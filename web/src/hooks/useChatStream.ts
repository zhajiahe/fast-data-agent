/**
 * 聊天 SSE 流处理 Hook
 * 封装 SSE 流的发送、解析和状态管理
 */
import { useCallback, useRef, useState } from 'react';
import type { LocalMessage, SSEEvent, ToolCallState } from '@/types';
import { storage } from '@/utils/storage';

interface UseChatStreamOptions {
  sessionId: number;
  onMessage: (message: LocalMessage) => void;
  onError: (error: string) => void;
  /** 流结束回调，支持异步。会等待此回调完成后才将 isGenerating 设为 false */
  onStreamEnd?: (finalContent: string) => void | Promise<void>;
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

      // 创建 AbortController
      abortControllerRef.current = new AbortController();

      let finalAiContent = '';
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
              // 流结束，将 streamingText 转为正式消息
              if (currentText) {
                finalAiContent = currentText;
                const aiMessage: LocalMessage = {
                  id: Date.now() + 1,
                  session_id: sessionId,
                  message_type: 'ai',
                  content: currentText,
                  create_time: new Date().toISOString(),
                };
                onMessage(aiMessage);
                setStreamingText('');
              }
              continue;
            }

            try {
              const event: SSEEvent = JSON.parse(dataStr);
              processSSEEvent(event, {
                currentText,
                sessionId,
                onMessage,
                onError,
                setStreamingText,
                setCurrentToolCall,
                updateCurrentText: (text) => {
                  currentText = text;
                },
                setFinalContent: (text) => {
                  finalAiContent = text;
                },
              });
            } catch {
              console.warn('Failed to parse SSE event:', dataStr);
            }
          }
        }

        // 调用流结束回调，等待其完成后再结束生成状态
        // 这确保 refetchMessages 完成后 isGenerating 才变为 false
        if (finalAiContent && onStreamEnd) {
          await onStreamEnd(finalAiContent);
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
 */
interface ProcessEventContext {
  currentText: string;
  sessionId: number;
  onMessage: (message: LocalMessage) => void;
  onError: (error: string) => void;
  setStreamingText: (text: string) => void;
  setCurrentToolCall: (call: ToolCallState | null) => void;
  updateCurrentText: (text: string) => void;
  setFinalContent: (text: string) => void;
}

function processSSEEvent(event: SSEEvent, ctx: ProcessEventContext) {
  switch (event.type) {
    case 'text-delta':
      if (event.delta) {
        const newText = ctx.currentText + event.delta;
        ctx.updateCurrentText(newText);
        ctx.setStreamingText(newText);
      }
      break;

    case 'text-end':
      // 文本块结束，将累积的文本保存为消息
      if (ctx.currentText) {
        const aiMessage: LocalMessage = {
          id: Date.now() + Math.random(),
          session_id: ctx.sessionId,
          message_type: 'ai',
          content: ctx.currentText,
          create_time: new Date().toISOString(),
        };
        ctx.onMessage(aiMessage);
        ctx.setFinalContent(ctx.currentText);
        ctx.updateCurrentText('');
        ctx.setStreamingText('');
      }
      break;

    case 'tool-input-start':
      ctx.setCurrentToolCall({
        id: event.toolCallId || '',
        name: event.toolName || '',
        status: 'calling',
      });
      break;

    case 'tool-input-available':
      ctx.setCurrentToolCall({
        id: event.toolCallId || '',
        name: event.toolName || '',
        status: 'executing',
      });
      break;

    case 'tool-output-available': {
      // 添加工具消息
      const toolMessage: LocalMessage = {
        id: Date.now() + Math.random(),
        session_id: ctx.sessionId,
        message_type: 'tool',
        content: JSON.stringify(event.output),
        tool_call_id: event.toolCallId,
        tool_name: event.toolName,
        artifact: event.artifact,
        create_time: new Date().toISOString(),
      };
      ctx.onMessage(toolMessage);
      // 设置工具调用为完成状态
      ctx.setCurrentToolCall({
        id: event.toolCallId || '',
        name: event.toolName || '',
        status: 'completed',
      });
      break;
    }

    case 'error':
      if (event.errorText) {
        ctx.onError(event.errorText);
      }
      break;
  }
}
