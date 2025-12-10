/**
 * 聊天 SSE 流处理 Hook
 * 简化设计：处理流式事件，管理显示状态
 */
import { useCallback, useRef, useState } from 'react';
import type { LocalMessage, SSEEvent, ToolCallState } from '@/types';
import { storage } from '@/utils/storage';

interface UseChatStreamOptions {
  sessionId: number;
  /** 消息回调，添加消息到列表 */
  onMessage: (message: LocalMessage) => void;
  onError: (error: string) => void;
  /** 流结束回调 */
  onStreamEnd?: () => void | Promise<void>;
}

interface UseChatStreamReturn {
  isGenerating: boolean;
  streamingText: string;
  currentToolCall: ToolCallState | null;
  send: (content: string) => Promise<void>;
  stop: () => void;
}

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
    abortControllerRef.current?.abort();
  }, []);

  const send = useCallback(
    async (content: string) => {
      if (!content.trim() || isGenerating) return;

      setIsGenerating(true);
      setStreamingText('');
      setCurrentToolCall(null);

      abortControllerRef.current = new AbortController();

      // 累积的文本内容
      let accumulatedText = '';
      // 已处理的工具调用 ID
      const processedToolCalls = new Set<string>();
      // 临时消息计数
      let tempMsgCount = 0;

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

              switch (event.type) {
                case 'text-delta':
                  // 累积文本并更新显示
                  if (event.delta) {
                    accumulatedText += event.delta;
                    setStreamingText(accumulatedText);
                  }
                  break;

                case 'text-end':
                  // 文本块结束，创建临时 AI 消息
                  if (accumulatedText.trim()) {
                    onMessage({
                      id: `temp_ai_${++tempMsgCount}`,
                      session_id: sessionId,
                      message_type: 'ai',
                      content: accumulatedText,
                      create_time: new Date().toISOString(),
                    });
                  }
                  accumulatedText = '';
                  setStreamingText('');
                  break;

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
                  // 去重
                  if (toolCallId && !processedToolCalls.has(toolCallId)) {
                    processedToolCalls.add(toolCallId);
                    onMessage({
                      id: `temp_tool_${toolCallId}`,
                      session_id: sessionId,
                      message_type: 'tool',
                      content: JSON.stringify(event.output),
                      tool_call_id: toolCallId,
                      tool_name: event.toolName,
                      artifact: event.artifact,
                      create_time: new Date().toISOString(),
                    });
                  }
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
            } catch {
              console.warn('Failed to parse SSE event:', dataStr);
            }
          }
        }

        // 流结束后回调
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
