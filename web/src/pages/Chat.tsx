import { useQueryClient } from '@tanstack/react-query';
import { ChevronLeft, Database, PanelRight, PanelRightClose, Send, Sparkles, StopCircle, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate, useParams } from 'react-router-dom';
import {
  type AnalysisSessionDetail,
  generateFollowupRecommendationsApiV1SessionsSessionIdRecommendationsFollowupPost,
  useClearMessages,
  useMessages,
  useSession,
} from '@/api';
import { ChatMessage } from '@/components/chat/ChatMessage';
import { RecommendationPanel } from '@/components/chat/RecommendationPanel';
import { SessionFilesPanel } from '@/components/chat/SessionFilesPanel';
import { ToolCallDisplay } from '@/components/chat/ToolCallDisplay';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Textarea } from '@/components/ui/textarea';
import { useChatStream, useToast } from '@/hooks';
import type { LocalMessage } from '@/types';

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
  const shouldAutoScrollRef = useRef(true);

  const [input, setInput] = useState('');
  const [showPanel, setShowPanel] = useState(true);
  const [localMessages, setLocalMessages] = useState<LocalMessage[]>([]);

  const queryClient = useQueryClient();

  // 使用生成的 API hooks
  const { data: sessionResponse } = useSession(sessionId);
  const {
    data: messagesResponse,
    refetch: refetchMessages,
    isFetching: isMessagesFetching,
  } = useMessages(sessionId, { page_size: 100 });
  const clearMessagesMutation = useClearMessages();

  const currentSession: AnalysisSessionDetail | null = sessionResponse?.data.data || null;

  // 添加消息到本地（防止重复）
  const addMessage = useCallback((message: LocalMessage) => {
    setLocalMessages((prev) => {
      // 检查是否已存在相同 ID 的消息
      if (prev.some((m) => m.id === message.id)) {
        return prev;
      }
      return [...prev, message];
    });
  }, []);

  // 使用聊天流 hook
  const { isGenerating, streamingText, currentToolCall, send, stop } = useChatStream({
    sessionId,
    onMessage: addMessage,
    onError: (error) => {
      toast({
        title: t('common.error'),
        description: error,
        variant: 'destructive',
      });
    },
    onStreamEnd: async (finalContent) => {
      // 生成后续问题推荐
      if (finalContent) {
        try {
          await generateFollowupRecommendationsApiV1SessionsSessionIdRecommendationsFollowupPost(sessionId, {
            conversation_context: `用户问: ${input}\n\nAI回答: ${finalContent}`,
            max_count: 3,
          });
          queryClient.invalidateQueries({ queryKey: ['recommendations', sessionId] });
        } catch (e) {
          console.warn('Failed to generate followup recommendations:', e);
        }
      }
      // 刷新消息列表
      await refetchMessages();
    },
  });

  // 使用稳定引用，避免每次渲染创建新数组
  const apiMessagesItems = messagesResponse?.data.data?.items;

  // 追踪上一次同步的 sessionId，避免重复同步
  const lastSyncedSessionRef = useRef<number | null>(null);

  // 会话切换时重置状态
  useEffect(() => {
    if (lastSyncedSessionRef.current !== sessionId) {
      lastSyncedSessionRef.current = sessionId;
      setLocalMessages([]);
    }
  }, [sessionId]);

  // 同步 API 消息到本地
  // 只在：不生成中 且 不在刷新中 且 有数据时才同步
  // 这样避免流结束后立即用旧数据替换，而是等 refetch 完成后一次性更新
  useEffect(() => {
    if (isGenerating || isMessagesFetching || !apiMessagesItems) return;

    const convertedMessages: LocalMessage[] = apiMessagesItems.map((m) => ({
      id: m.id,
      session_id: m.session_id,
      message_type: m.message_type as LocalMessage['message_type'],
      content: m.content,
      tool_call_id: m.tool_call_id || undefined,
      tool_name: m.name || undefined,
      artifact: m.artifact as LocalMessage['artifact'],
      create_time: m.create_time || new Date().toISOString(),
    }));

    convertedMessages.sort((a, b) => new Date(a.create_time).getTime() - new Date(b.create_time).getTime());
    setLocalMessages(convertedMessages);
  }, [apiMessagesItems, isGenerating, isMessagesFetching]);

  // 检测用户是否在底部附近
  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    shouldAutoScrollRef.current = scrollHeight - scrollTop - clientHeight < 100;
  }, []);

  // 自动滚动到底部
  // biome-ignore lint/correctness/useExhaustiveDependencies: 需要在消息/流式文本变化时滚动
  useEffect(() => {
    if (scrollRef.current && shouldAutoScrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [localMessages, streamingText]);

  // 发送消息时重置自动滚动
  useEffect(() => {
    if (isGenerating) {
      shouldAutoScrollRef.current = true;
    }
  }, [isGenerating]);

  // 发送消息
  const handleSend = useCallback(
    async (messageContent?: string) => {
      const content = (messageContent || input).trim();
      if (!content || isGenerating) return;

      setInput('');

      // 添加用户消息到本地
      const userMessage: LocalMessage = {
        id: Date.now(),
        session_id: sessionId,
        message_type: 'human',
        content,
        create_time: new Date().toISOString(),
      };
      addMessage(userMessage);

      await send(content);
    },
    [input, isGenerating, sessionId, addMessage, send]
  );

  // 处理键盘事件
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 处理推荐任务点击
  const handleRecommendationClick = useCallback(
    (query: string) => {
      handleSend(query);
    },
    [handleSend]
  );

  // 清空对话
  const handleClearMessages = useCallback(async () => {
    if (!sessionId || isGenerating) return;
    try {
      await clearMessagesMutation.mutateAsync(sessionId);
      setLocalMessages([]);
      toast({ title: t('chat.messagesCleared') });
    } catch {
      toast({ title: t('chat.clearFailed'), variant: 'destructive' });
    }
  }, [sessionId, isGenerating, clearMessagesMutation, toast, t]);

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
        <ScrollArea className="flex-1 p-4" ref={scrollRef} onScrollCapture={handleScroll}>
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
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={handleClearMessages}
                  disabled={isGenerating || localMessages.length === 0}
                  title={t('chat.clearMessages')}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
                {isGenerating ? (
                  <Button size="sm" variant="destructive" onClick={stop}>
                    <StopCircle className="h-4 w-4 mr-1" />
                    {t('chat.stop')}
                  </Button>
                ) : (
                  <Button size="sm" onClick={() => handleSend()} disabled={!input.trim()}>
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
        <div className="w-80 border-l shrink-0 hidden lg:flex lg:flex-col">
          <div className="flex-1 min-h-0 border-b">
            <RecommendationPanel sessionId={sessionId} onSelect={handleRecommendationClick} />
          </div>
          <div className="h-[280px] shrink-0">
            <SessionFilesPanel sessionId={sessionId} />
          </div>
        </div>
      )}
    </div>
  );
};
