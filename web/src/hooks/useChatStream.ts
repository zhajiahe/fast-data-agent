/**
 * 聊天 SSE 流处理 Hook
 * 封装 SSE 流的发送、解析和状态管理
 *
 * 设计原则：
 * - 流式过程只更新显示状态（streamingText, currentToolCall）
 * - 不在流式过程中创建临时消息，避免与 refetch 重复
 * - 流结束后通过 onStreamEnd 回调统一 refetch 获取持久化消息
 */
import { useCallback, useRef, useState } from 'react';
import type { SSEEvent, ToolCallState } from '@/types';
import { storage } from '@/utils/storage';

interface UseChatStreamOptions {
  sessionId: number;
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
                onError,
                setStreamingText,
                setCurrentToolCall,
              });
            } catch {
              console.warn('Failed to parse SSE event:', dataStr);
            }
          }
        }

        // 流结束后统一 refetch 获取持久化消息
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
    [sessionId, isGenerating, onError, onStreamEnd]
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
 * 只更新显示状态，不创建消息（消息通过流结束后 refetch 获取）
 */
interface ProcessEventHandlers {
  onError: (error: string) => void;
  setStreamingText: (text: string) => void;
  setCurrentToolCall: (call: ToolCallState | null) => void;
}

function processSSEEvent(
  event: SSEEvent,
  currentText: string,
  handlers: ProcessEventHandlers
): string {
  const { onError, setStreamingText, setCurrentToolCall } = handlers;

  switch (event.type) {
    case 'text-delta':
      if (event.delta) {
        const newText = currentText + event.delta;
        setStreamingText(newText);
        return newText;
      }
      break;

    case 'text-end':
      // 文本块结束，清空流式文本（消息由后端持久化，前端 refetch 获取）
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

    case 'tool-output-available':
      // 工具执行完成，更新状态（消息由后端持久化，前端 refetch 获取）
      setCurrentToolCall({
        id: event.toolCallId || '',
        name: event.toolName || '',
        status: 'completed',
      });
      break;

    case 'error':
      if (event.errorText) {
        onError(event.errorText);
      }
      break;
  }

  return currentText;
}
