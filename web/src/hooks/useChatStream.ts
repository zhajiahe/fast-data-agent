/**
 * 聊天 SSE 流处理 Hook
 * 封装 SSE 流的发送、解析和状态管理
 *
 * 设计原则：
 * - AI 文本：流式显示（streamingText），text-end 时添加临时消息，让用户看到中间输出
 * - 工具消息：实时添加到消息列表（通过 onMessage），让用户看到 agent 执行过程
 * - 流结束后 refetch 获取持久化消息，完全替换临时消息
 */
import { useCallback, useRef, useState } from 'react';
import type { LocalMessage, SSEEvent, ToolCallState } from '@/types';
import { storage } from '@/utils/storage';

interface UseChatStreamOptions {
  sessionId: number;
  /** 消息回调，添加 AI 和工具消息到列表 */
  onMessage: (message: LocalMessage) => void;
  onError: (error: string) => void;
  /** 流结束回调，支持异步。会等待此回调完成后才将 isGenerating 设为 false */
  onStreamEnd?: () => void | Promise<void>;
}

interface UseChatStreamReturn {
  /** 是否正在生成 */
  isGenerating: boolean;
  /** 当前流式文本 */
  streamingText: string;
  /** 当前工具调用状态 */
  currentToolCall: ToolCallState | null;
  /** 发送消息 */
  send: (content: string) => Promise<void>;
  /** 停止生成 */
  stop: () => void;
}

/**
 * 聊天 SSE 流处理 Hook
 */
export function useChatStream({
  sessionId,
  onMessage,
  onError,
  onStreamEnd,
}: UseChatStreamOptions): UseChatStreamReturn {
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [currentToolCall, setCurrentToolCall] = useState<ToolCallState | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  // 跟踪已添加的工具消息，避免重复
  const addedToolCallsRef = useRef<Set<string>>(new Set());
  // 临时消息计数器，用于生成唯一 ID
  const tempMessageIdRef = useRef(0);

  const stop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  }, []);

  const send = useCallback(
    async (content: string) => {
      if (!content.trim() || isGenerating) return;

      setIsGenerating(true);
      setStreamingText('');
      setCurrentToolCall(null);
      addedToolCallsRef.current.clear();
      tempMessageIdRef.current = 0;

      abortControllerRef.current = new AbortController();
      let currentText = '';

      try {
        const token = storage.getToken();
        const response = await fetch(`/api/v1/sessions/${sessionId}/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ content }),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) throw new Error('No response body');

        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (!line.startsWith('data: ')) continue;
            const dataStr = line.slice(6);

            if (dataStr === '[DONE]') {
              setStreamingText('');
              continue;
            }

            try {
              const event: SSEEvent = JSON.parse(dataStr);
              currentText = processSSEEvent(event, currentText, {
                sessionId,
                addedToolCalls: addedToolCallsRef.current,
                getTempId: () => `temp_${++tempMessageIdRef.current}`,
                onMessage,
                onError,
                setStreamingText,
                setCurrentToolCall,
              });
            } catch {
              console.warn('Failed to parse SSE event:', dataStr);
            }
          }
        }

        // 流结束后 refetch 获取持久化消息，替换所有临时消息
        if (onStreamEnd) {
          await onStreamEnd();
        }
      } catch (err: unknown) {
        const error = err as Error;
        if (error.name !== 'AbortError') {
          onError(error.message);
        }
      } finally {
        setIsGenerating(false);
        setCurrentToolCall(null);
        abortControllerRef.current = null;
      }
    },
    [sessionId, isGenerating, onMessage, onError, onStreamEnd]
  );

  return {
    isGenerating,
    streamingText,
    currentToolCall,
    send,
    stop,
  };
}

/**
 * 处理单个 SSE 事件
 * - AI 文本：流式显示，text-end 时添加临时消息
 * - 工具消息：实时添加到消息列表
 */
interface ProcessEventHandlers {
  sessionId: number;
  addedToolCalls: Set<string>;
  getTempId: () => string;
  onMessage: (message: LocalMessage) => void;
  onError: (error: string) => void;
  setStreamingText: (text: string) => void;
  setCurrentToolCall: (call: ToolCallState | null) => void;
}

function processSSEEvent(
  event: SSEEvent,
  currentText: string,
  handlers: ProcessEventHandlers
): string {
  const { sessionId, addedToolCalls, getTempId, onMessage, onError, setStreamingText, setCurrentToolCall } = handlers;

  switch (event.type) {
    case 'text-delta':
      if (event.delta) {
        const newText = currentText + event.delta;
        setStreamingText(newText);
        return newText;
      }
      break;

    case 'text-end':
      // 文本块结束，将累积的文本添加为临时 AI 消息
      if (currentText.trim()) {
        const aiMessage: LocalMessage = {
          id: getTempId(), // 临时 ID，refetch 后会被替换
          session_id: sessionId,
          message_type: 'ai',
          content: currentText,
          create_time: new Date().toISOString(),
        };
        onMessage(aiMessage);
      }
      setStreamingText('');
      return '';

    case 'tool-input-start':
      setCurrentToolCall({
        id: event.toolCallId || '',
        name: event.toolName || '',
        status: 'calling',
      });
      break;

    case 'tool-input-available':
      setCurrentToolCall({
        id: event.toolCallId || '',
        name: event.toolName || '',
        status: 'executing',
      });
      break;

    case 'tool-output-available': {
      const toolCallId = event.toolCallId || '';
      
      // 使用 tool_call_id 去重，避免重复添加
      if (toolCallId && !addedToolCalls.has(toolCallId)) {
        addedToolCalls.add(toolCallId);
        
        // 实时添加工具消息
        const toolMessage: LocalMessage = {
          id: `tool_${toolCallId}`, // 临时 ID，refetch 后会被替换
          session_id: sessionId,
          message_type: 'tool',
          content: JSON.stringify(event.output),
          tool_call_id: toolCallId,
          tool_name: event.toolName,
          artifact: event.artifact,
          create_time: new Date().toISOString(),
        };
        onMessage(toolMessage);
      }

      // 更新工具调用状态
      setCurrentToolCall({
        id: toolCallId,
        name: event.toolName || '',
        status: 'completed',
      });
      break;
    }

    case 'error':
      if (event.errorText) {
        onError(event.errorText);
      }
      break;
  }

  return currentText;
}
