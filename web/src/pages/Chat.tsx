// @ts-nocheck
import { useQueryClient } from '@tanstack/react-query';
import { ArrowDown, ChevronLeft, Database, PanelRight, PanelRightClose, Send, Sparkles, StopCircle, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
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
import { ToolCallProgress } from '@/components/chat/ToolCallProgress';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { useChatStream, useToast } from '@/hooks';
import { cn } from '@/lib/utils';
import type { LocalMessage } from '@/types';

/**
 * 消息分组类型
 * - single: 单条消息（人类消息、独立 AI 消息）
 * - tool-group: 工具调用组（一个 AI 消息后跟多个工具消息）
 */
interface MessageGroup {
  type: 'single' | 'tool-group';
  /** AI 消息（仅 tool-group 时有） */
  aiMessage?: LocalMessage;
  /** 工具消息列表（仅 tool-group 时有） */
  toolMessages?: LocalMessage[];
  /** 单条消息（仅 single 时有） */
  message?: LocalMessage;
  /** 用于 React key */
  key: string;
}

/**
 * 聊天页面 - 核心交互界面
 */
export const Chat = () => {
  const { id } = useParams<{ id: string }>();
  // sessionId 可以是 UUID 字符串，这里直接使用原始值
  // 注意：API 定义为 number 但实际后端使用 UUID
  const sessionId = id as unknown as number; // 临时类型转换
  const { t } = useTranslation();
  const { toast } = useToast();
  const navigate = useNavigate();
  const scrollRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const lastScrollTopRef = useRef(0);
  const isUserScrollingRef = useRef(false);

  const [input, setInput] = useState('');
  const [showPanel, setShowPanel] = useState(true);
  const [localMessages, setLocalMessages] = useState<LocalMessage[]>([]);
  const [isAutoScrollEnabled, setIsAutoScrollEnabled] = useState(true);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);

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
  // - AI 文本：流式显示，text-end 时添加临时消息
  // - 工具消息：实时添加到消息列表，让用户看到 agent 执行过程
  // - 流结束后 refetch 获取持久化消息，替换所有临时消息
  const { isGenerating, streamingText, currentToolCall, send, stop } = useChatStream({
    sessionId,
    onMessage: addMessage, // 实时添加 AI 和工具消息
    onError: (error) => {
      toast({
        title: t('common.error'),
        description: error,
        variant: 'destructive',
      });
    },
    onStreamEnd: async () => {
      // 1. 刷新消息列表，用持久化消息替换所有临时消息
      const result = await refetchMessages();
      const newItems = result.data?.data.data?.items;
      if (newItems) {
        setLocalMessages(convertApiMessages(newItems));
      }

      // 2. 后台生成后续问题推荐（非关键路径，不等待）
      generateFollowupRecommendationsApiV1SessionsSessionIdRecommendationsFollowupPost(sessionId, {
        conversation_context: `用户最新问题: ${input}`,
        max_count: 3,
      })
        .then(() => {
          queryClient.invalidateQueries({ queryKey: ['recommendations', sessionId] });
        })
        .catch((e) => {
          console.warn('Failed to generate followup recommendations:', e);
        });
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

  // 将 API 消息转换为本地格式的工具函数
  const convertApiMessages = useCallback((items: typeof apiMessagesItems): LocalMessage[] => {
    if (!items) return [];
    const converted = items.map((m) => ({
      id: m.id,
      session_id: m.session_id,
      seq: m.seq,
      message_type: m.message_type as LocalMessage['message_type'],
      content: m.content,
      tool_call_id: m.tool_call_id || undefined,
      tool_name: m.name || undefined,
      tool_calls: m.tool_calls as LocalMessage['tool_calls'],
      artifact: m.artifact as LocalMessage['artifact'],
      create_time: m.create_time || new Date().toISOString(),
    }));
    // 按 seq 排序（后端已保证顺序，但前端也做一次排序确保正确）
    converted.sort((a, b) => (a.seq ?? 0) - (b.seq ?? 0));
    return converted;
  }, []);

  // 同步 API 消息到本地（仅在非生成状态时）
  useEffect(() => {
    if (isGenerating || isMessagesFetching || !apiMessagesItems) return;
    setLocalMessages(convertApiMessages(apiMessagesItems));
  }, [apiMessagesItems, isGenerating, isMessagesFetching, convertApiMessages]);

  /**
   * 将消息列表分组，优化连续消息的显示：
   * - 人类消息单独一组
   * - 连续的工具相关消息（AI+tool/tool）合并为一组
   * - AI 消息如果有实际内容则单独显示
   *
   * 合并规则：如果相邻的两个组都是 tool-group，则合并它们
   */
  const messageGroups = useMemo((): MessageGroup[] => {
    const rawGroups: MessageGroup[] = [];
    let i = 0;

    // 第一遍：基本分组
    while (i < localMessages.length) {
      const msg = localMessages[i];

      if (msg.message_type === 'human') {
        // 人类消息单独一组
        rawGroups.push({
          type: 'single',
          message: msg,
          key: `single-${msg.id}`,
        });
        i++;
      } else if (msg.message_type === 'ai') {
        const hasContent = msg.content?.trim();
        const hasToolCalls = msg.tool_calls && msg.tool_calls.length > 0;

        // 检查后续是否有工具消息
        const toolMessages: LocalMessage[] = [];
        let j = i + 1;
        while (j < localMessages.length && localMessages[j].message_type === 'tool') {
          toolMessages.push(localMessages[j]);
          j++;
        }

        if (toolMessages.length > 0) {
          // 有工具消息
          if (hasContent) {
            // AI 消息有内容，先显示 AI 消息
            rawGroups.push({
              type: 'single',
              message: msg,
              key: `single-${msg.id}`,
            });
          }
          // 再显示工具组
          rawGroups.push({
            type: 'tool-group',
            toolMessages,
            key: `tool-group-${msg.id}`,
          });
          i = j;
        } else if (hasContent) {
          // 没有工具消息但有内容，单独显示 AI 消息
          rawGroups.push({
            type: 'single',
            message: msg,
            key: `single-${msg.id}`,
          });
          i++;
        } else if (hasToolCalls) {
          // 没有内容但有 tool_calls（工具调用中），跳过这条消息
          i++;
        } else {
          // 空消息，跳过
          i++;
        }
      } else if (msg.message_type === 'tool') {
        // 收集连续的工具消息
        const toolMessages: LocalMessage[] = [msg];
        let j = i + 1;
        while (j < localMessages.length && localMessages[j].message_type === 'tool') {
          toolMessages.push(localMessages[j]);
          j++;
        }

        rawGroups.push({
          type: 'tool-group',
          toolMessages,
          key: `tool-group-${msg.id}`,
        });
        i = j;
      } else {
        // 其他类型消息
        rawGroups.push({
          type: 'single',
          message: msg,
          key: `single-${msg.id}`,
        });
        i++;
      }
    }

    // 第二遍：合并相邻的 tool-group
    const mergedGroups: MessageGroup[] = [];
    for (const group of rawGroups) {
      const lastGroup = mergedGroups[mergedGroups.length - 1];

      if (
        group.type === 'tool-group' &&
        lastGroup?.type === 'tool-group' &&
        group.toolMessages &&
        lastGroup.toolMessages
      ) {
        // 合并到上一个工具组
        lastGroup.toolMessages.push(...group.toolMessages);
      } else {
        mergedGroups.push(group);
      }
    }

    return mergedGroups;
  }, [localMessages]);

  /**
   * 智能滚动处理
   * - 向上滚动：暂停自动跟踪，显示"滚动到底部"按钮
   * - 滚动到底部：恢复自动跟踪
   */
  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const isAtBottom = scrollHeight - scrollTop - clientHeight < 100;
    const isScrollingUp = scrollTop < lastScrollTopRef.current;

    lastScrollTopRef.current = scrollTop;

    // 如果用户主动向上滚动，暂停自动滚动
    if (isScrollingUp && isUserScrollingRef.current) {
      setIsAutoScrollEnabled(false);
      setShowScrollToBottom(true);
    }

    // 如果滚动到底部，恢复自动滚动
    if (isAtBottom) {
      setIsAutoScrollEnabled(true);
      setShowScrollToBottom(false);
    } else if (!isScrollingUp && !isAtBottom) {
      // 向下滚动但还没到底部，显示按钮
      setShowScrollToBottom(true);
    }
  }, []);

  // 监听用户滚动交互
  const handleWheel = useCallback(() => {
    isUserScrollingRef.current = true;
    // 短暂延迟后重置
    setTimeout(() => {
      isUserScrollingRef.current = false;
    }, 150);
  }, []);

  // 滚动到底部
  const scrollToBottom = useCallback(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    setIsAutoScrollEnabled(true);
    setShowScrollToBottom(false);
  }, []);

  // 自动滚动到底部
  // biome-ignore lint/correctness/useExhaustiveDependencies: 需要在消息/流式文本变化时滚动
  useEffect(() => {
    if (isAutoScrollEnabled && scrollRef.current) {
      // 使用 requestAnimationFrame 确保在渲染后滚动
      requestAnimationFrame(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
      });
    }
  }, [localMessages, streamingText, currentToolCall, isAutoScrollEnabled]);

  // 发送消息或开始生成时启用自动滚动
  useEffect(() => {
    if (isGenerating) {
      setIsAutoScrollEnabled(true);
      setShowScrollToBottom(false);
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

  if (!id) {
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
        <div className="flex-1 relative min-h-0">
          <div
            ref={scrollRef}
            className="h-full overflow-auto p-4"
            onScroll={handleScroll}
            onWheel={handleWheel}
          >
          <div className="max-w-3xl mx-auto space-y-4">
            {localMessages.length === 0 && !isGenerating ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Sparkles className="h-12 w-12 text-primary/50 mb-4" />
                <h2 className="text-xl font-semibold mb-2">{t('chat.welcome')}</h2>
                <p className="text-muted-foreground max-w-md mb-6">{t('chat.welcomeHint')}</p>

                {/* 示例问题卡片 */}
                <div className="w-full max-w-lg">
                  <p className="text-sm text-muted-foreground mb-3">{t('chat.exampleQuestionsTitle')}</p>
                  <div className="grid gap-2">
                    {[
                      { icon: '📊', text: t('chat.exampleQuestions.overview') },
                      { icon: '📈', text: t('chat.exampleQuestions.trend') },
                      { icon: '🔍', text: t('chat.exampleQuestions.detail') },
                      { icon: '📉', text: t('chat.exampleQuestions.comparison') },
                    ].map((item) => (
                      <button
                        key={item.text}
                        type="button"
                        className="flex items-center gap-3 p-3 rounded-lg border border-border/50 hover:border-primary/50 hover:bg-muted/50 transition-all text-left group"
                        onClick={() => handleSend(item.text)}
                      >
                        <span className="text-lg">{item.icon}</span>
                        <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors">
                          {item.text}
                        </span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <>
                {messageGroups.map((group) => {
                  if (group.type === 'single' && group.message) {
                    return <ChatMessage key={group.key} message={group.message} />;
                  }

                  if (group.type === 'tool-group') {
                    return (
                      <div key={group.key} className="space-y-2">
                        {/* AI 消息（如果有内容） */}
                        {group.aiMessage?.content?.trim() && (
                          <ChatMessage message={group.aiMessage} />
                        )}
                        {/* 工具调用进度组件 */}
                        <ToolCallProgress toolMessages={group.toolMessages || []} />
                      </div>
                    );
                  }

                  return null;
                })}

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

                {/* 当前工具调用状态（流式进行中） */}
                {currentToolCall && (
                  <ToolCallProgress
                    toolMessages={[]}
                    currentToolCall={currentToolCall}
                  />
                )}

                {/* AI 正在思考 - 当正在生成但还没有任何输出时 */}
                {isGenerating && !streamingText && !currentToolCall && (
                  <div className="flex gap-3">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shrink-0">
                      <Sparkles className="w-4 h-4 text-white animate-pulse" />
                    </div>
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <div className="flex gap-1">
                        <span className="w-2 h-2 rounded-full bg-violet-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-2 h-2 rounded-full bg-violet-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                        <span className="w-2 h-2 rounded-full bg-violet-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                      </div>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
          </div>

          {/* 滚动到底部按钮 */}
          {showScrollToBottom && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10">
              <Button
                size="sm"
                variant="secondary"
                className={cn(
                  'shadow-lg transition-all duration-200',
                  'hover:shadow-xl hover:scale-105'
                )}
                onClick={scrollToBottom}
              >
                <ArrowDown className="h-4 w-4 mr-1" />
                {isGenerating ? '跟踪对话' : '滚动到底部'}
              </Button>
            </div>
          )}

          {/* 自动滚动暂停提示 */}
          {isGenerating && !isAutoScrollEnabled && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-10">
              <div className="bg-amber-100 dark:bg-amber-900/50 text-amber-700 dark:text-amber-300 text-xs px-3 py-1.5 rounded-full shadow-sm">
                已暂停自动跟踪
              </div>
            </div>
          )}
        </div>

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
