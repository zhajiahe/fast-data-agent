/**
 * 聊天 SSE 流处理 Hook
 * 封装 SSE 流的发送、解析和状态管理
 *
 * 设计原则：
 * - AI 文本：流式显示（streamingText），结束后通过 refetch 获取持久化消息
 * - 工具消息：实时添加到消息列表（通过 onToolMessage），让用户看到 agent 执行过程
 * - 使用 tool_call_id 去重，避免工具消息重复
 */
import { useCallback, useRef, useState } from 'react';
import type { LocalMessage, SSEEvent, ToolCallState } from '@/types';
import { storage } from '@/utils/storage';

interface UseChatStreamOptions {
  sessionId: number;
  /** 工具消息回调，实时显示工具执行结果 */
  onToolMessage: (message: LocalMessage) => void;
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
  onToolMessage,
  onError,
  onStreamEnd,
}: UseChatStreamOptions): UseChatStreamReturn {
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [currentToolCall, setCurrentToolCall] = useState<ToolCallState | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  // 跟踪已添加的工具消息，避免重复
  const addedToolCallsRef = useRef<Set<string>>(new Set());

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
                onToolMessage,
                onError,
                setStreamingText,
                setCurrentToolCall,
              });
            } catch {
              console.warn('Failed to parse SSE event:', dataStr);
            }
          }
        }

        // 流结束后 refetch 获取持久化消息（包括 AI 文本消息）
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
    [sessionId, isGenerating, onToolMessage, onError, onStreamEnd]
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
 * - AI 文本：更新 streamingText 状态
 * - 工具消息：实时添加到消息列表（让用户看到 agent 执行过程）
 */
interface ProcessEventHandlers {
  sessionId: number;
  addedToolCalls: Set<string>;
  onToolMessage: (message: LocalMessage) => void;
  onError: (error: string) => void;
  setStreamingText: (text: string) => void;
  setCurrentToolCall: (call: ToolCallState | null) => void;
}

function processSSEEvent(
  event: SSEEvent,
  currentText: string,
  handlers: ProcessEventHandlers
): string {
  const { sessionId, addedToolCalls, onToolMessage, onError, setStreamingText, setCurrentToolCall } = handlers;

  switch (event.type) {
    case 'text-delta':
      if (event.delta) {
        const newText = currentText + event.delta;
        setStreamingText(newText);
        return newText;
      }
      break;

    case 'text-end':
      // 文本块结束，清空流式文本（AI 消息由后端持久化，前端 refetch 获取）
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
        
        // 实时添加工具消息，让用户看到 agent 执行过程
        const toolMessage: LocalMessage = {
          id: `tool_${toolCallId}`,  // 使用 tool_call_id 作为临时 ID
          session_id: sessionId,
          message_type: 'tool',
          content: JSON.stringify(event.output),
          tool_call_id: toolCallId,
          tool_name: event.toolName,
          artifact: event.artifact,
          create_time: new Date().toISOString(),
        };
        onToolMessage(toolMessage);
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
