import { ChevronLeft, Database, PanelRight, PanelRightClose, Send, Sparkles, StopCircle } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import { useSession, useMessages, type ChatMessageResponse, type AnalysisSessionDetail } from '@/api';
import { ChatMessage } from '@/components/chat/ChatMessage';
import { RecommendationPanel } from '@/components/chat/RecommendationPanel';
import { ToolCallDisplay } from '@/components/chat/ToolCallDisplay';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { useToast } from '@/hooks/use-toast';
import { storage } from '@/utils/storage';

// SSE 事件类型
interface SSEEvent {
  type: string;
  messageId?: string;
  id?: string;
  delta?: string;
  toolCallId?: string;
  toolName?: string;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  artifact?: {
    type: string;
    chart_json?: string;
    columns?: string[];
    rows?: unknown[][];
    title?: string;
    error_message?: string;
    filename?: string;
  };
  errorText?: string;
}

// 本地消息类型（用于 store）
interface LocalMessage {
  id: number;
  session_id: number;
  message_type: string;
  content: string;
  tool_call_id?: string;
  tool_name?: string;
  artifact?: SSEEvent['artifact'];
  create_time: string;
}

/**
 * 聊天页面 - 核心交互界面
 */
export const Chat = () => {
  const { id } = useParams<{ id: string }>();
  const sessionId = Number(id);
  const { t } = useTranslation();
  const { toast } = useToast();
  const navigate = useNavigate();
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const [input, setInput] = useState('');
  const [showPanel, setShowPanel] = useState(true);
  const [localMessages, setLocalMessages] = useState<LocalMessage[]>([]);
  const [isGenerating, setIsGenerating] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [currentToolCall, setCurrentToolCall] = useState<{
    id: string;
    name: string;
    status: 'calling' | 'executing' | 'completed' | 'error';
  } | null>(null);

  // 使用生成的 API hooks
  const { data: sessionResponse } = useSession(sessionId);
  const { data: messagesResponse } = useMessages(sessionId, { page_size: 100 });

  const currentSession: AnalysisSessionDetail | null = sessionResponse?.data.data || null;
  const apiMessages: ChatMessageResponse[] = messagesResponse?.data.data?.items || [];

  // 同步 API 消息到本地
  useEffect(() => {
    if (apiMessages.length > 0) {
      setLocalMessages(
        apiMessages.map((m) => ({
          id: m.id,
          session_id: m.session_id,
          message_type: m.message_type,
          content: m.content,
          tool_call_id: m.tool_call_id || undefined,
          create_time: m.create_time || new Date().toISOString(),
        }))
      );
    }
  }, [apiMessages]);

  // 自动滚动到底部
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [localMessages, streamingText]);

  // 添加消息到本地
  const addMessage = useCallback((message: LocalMessage) => {
    setLocalMessages((prev) => [...prev, message]);
  }, []);

  // 发送消息
  const handleSend = useCallback(async () => {
    const content = input.trim();
    if (!content || isGenerating) return;

    setInput('');
    setIsGenerating(true);
    setStreamingText('');

    // 添加用户消息到本地
    const userMessage: LocalMessage = {
      id: Date.now(),
      session_id: sessionId,
      message_type: 'human',
      content,
      create_time: new Date().toISOString(),
    };
    addMessage(userMessage);

    // 创建 AbortController
    abortControllerRef.current = new AbortController();

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
      let currentStreamingText = '';

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
            if (currentStreamingText) {
              const aiMessage: LocalMessage = {
                id: Date.now() + 1,
                session_id: sessionId,
                message_type: 'ai',
                content: currentStreamingText,
                create_time: new Date().toISOString(),
              };
              addMessage(aiMessage);
              setStreamingText('');
            }
            continue;
          }

          try {
            const event: SSEEvent = JSON.parse(dataStr);

            switch (event.type) {
              case 'text-delta':
                if (event.delta) {
                  currentStreamingText += event.delta;
                  setStreamingText(currentStreamingText);
                }
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
                // 添加工具消息
                const toolMessage: LocalMessage = {
                  id: Date.now(),
                  session_id: sessionId,
                  message_type: 'tool',
                  content: JSON.stringify(event.output),
                  tool_call_id: event.toolCallId,
                  artifact: event.artifact,
                  create_time: new Date().toISOString(),
                };
                addMessage(toolMessage);
                setCurrentToolCall((prev) =>
                  prev
                    ? {
                        ...prev,
                        status: 'completed',
                      }
                    : null
                );
                break;
              }

              case 'error':
                toast({
                  title: t('common.error'),
                  description: event.errorText,
                  variant: 'destructive',
                });
                break;
            }
          } catch {
            console.warn('Failed to parse SSE event:', dataStr);
          }
        }
      }
    } catch (err: unknown) {
      const error = err as Error;
      if (error.name === 'AbortError') {
        toast({
          title: t('chat.stopped'),
          description: t('chat.stoppedDesc'),
        });
      } else {
        toast({
          title: t('common.error'),
          description: error.message,
          variant: 'destructive',
        });
      }
    } finally {
      setIsGenerating(false);
      setCurrentToolCall(null);
      abortControllerRef.current = null;
    }
  }, [input, isGenerating, sessionId, addMessage, toast, t]);

  // 停止生成
  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 处理推荐任务点击
  const handleRecommendationClick = (query: string) => {
    setInput(query);
    textareaRef.current?.focus();
  };

  if (!sessionId) {
    return (
      <div className="flex items-center justify-center h-screen">
        <p className="text-muted-foreground">{t('chat.invalidSession')}</p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* 主聊天区域 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部栏 */}
        <div className="h-14 border-b flex items-center justify-between px-4 shrink-0">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate('/sessions')}>
              <ChevronLeft className="h-5 w-5" />
            </Button>
            <div>
              <h1 className="font-semibold truncate max-w-[300px]">{currentSession?.name || t('chat.loading')}</h1>
              {currentSession?.data_sources && currentSession.data_sources.length > 0 && (
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <Database className="h-3 w-3" />
                  {currentSession.data_sources.map((ds) => ds.name).join(', ')}
                </div>
              )}
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={() => setShowPanel(!showPanel)}>
            {showPanel ? <PanelRightClose className="h-5 w-5" /> : <PanelRight className="h-5 w-5" />}
          </Button>
        </div>

        {/* 消息列表 */}
        <ScrollArea className="flex-1 p-4" ref={scrollRef}>
          <div className="max-w-3xl mx-auto space-y-6">
            {localMessages.length === 0 && !isGenerating ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Sparkles className="h-12 w-12 text-primary/50 mb-4" />
                <h2 className="text-xl font-semibold mb-2">{t('chat.welcome')}</h2>
                <p className="text-muted-foreground max-w-md">{t('chat.welcomeHint')}</p>
              </div>
            ) : (
              <>
                {localMessages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}
                {/* 流式文本 */}
                {streamingText && (
                  <ChatMessage
                    message={{
                      id: -1,
                      session_id: sessionId,
                      message_type: 'ai',
                      content: streamingText,
                      create_time: new Date().toISOString(),
                    }}
                    isStreaming
                  />
                )}
                {/* 工具调用状态 */}
                {currentToolCall && <ToolCallDisplay toolCall={currentToolCall} />}
              </>
            )}
          </div>
        </ScrollArea>

        {/* 输入区域 */}
        <div className="border-t p-4 shrink-0">
          <div className="max-w-3xl mx-auto">
            <div className="relative">
              <Textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={t('chat.inputPlaceholder')}
                className="min-h-[60px] max-h-[200px] pr-24 resize-none"
                disabled={isGenerating}
              />
              <div className="absolute right-2 bottom-2 flex gap-2">
                {isGenerating ? (
                  <Button size="sm" variant="destructive" onClick={handleStop}>
                    <StopCircle className="h-4 w-4 mr-1" />
                    {t('chat.stop')}
                  </Button>
                ) : (
                  <Button size="sm" onClick={handleSend} disabled={!input.trim()}>
                    <Send className="h-4 w-4 mr-1" />
                    {t('chat.send')}
                  </Button>
                )}
              </div>
            </div>
            <p className="text-xs text-muted-foreground mt-2 text-center">{t('chat.enterToSend')}</p>
          </div>
        </div>
      </div>

      {/* 右侧面板 */}
      {showPanel && (
        <div className="w-80 border-l shrink-0 hidden lg:block">
          <RecommendationPanel sessionId={sessionId} onSelect={handleRecommendationClick} />
        </div>
      )}
    </div>
  );
};
