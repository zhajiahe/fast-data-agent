import { Archive, Calendar, Database, MessageSquare, MoreHorizontal, Plus, Search, Trash2 } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useArchiveSession, useDataSources, useDeleteSession, useSessions } from '@/api';
import { EmptyState } from '@/components/common';
import { CreateSessionDialog } from '@/components/session/CreateSessionDialog';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Input } from '@/components/ui/input';
import { useToast } from '@/hooks/use-toast';

// 将后端时间字符串（无时区信息）按 UTC 解析，再转换为本地相对时间
const parseServerDate = (dateStr: string | null | undefined): Date | null => {
  if (!dateStr) return null;
  const hasTimezone = /[zZ]|[+-]\d{2}:?\d{2}$/.test(dateStr);
  const normalized = hasTimezone ? dateStr : `${dateStr}Z`; // 视作 UTC
  const date = new Date(normalized);
  return Number.isNaN(date.getTime()) ? null : date;
};

// 辅助函数：格式化相对时间
const formatRelativeTime = (dateStr: string | null | undefined): string => {
  const date = parseServerDate(dateStr);
  if (!date) return '-';
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return '刚刚';
  if (diffMins < 60) return `${diffMins} 分钟前`;
  if (diffHours < 24) return `${diffHours} 小时前`;
  if (diffDays < 7) return `${diffDays} 天前`;
  return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' });
};

// 辅助函数：会话分组
interface SessionGroup {
  label: string;
  sessions: Array<{
    id: string;
    name: string;
    description?: string | null;
    status?: string | null;
    message_count?: number | null;
    data_source_id?: string | null;
    create_time?: string | null;
    update_time?: string | null;
  }>;
}

const groupSessionsByDate = (
  sessions: Array<{
    id: string;
    name: string;
    description?: string | null;
    status?: string | null;
    message_count?: number | null;
    data_source_id?: string | null;
    create_time?: string | null;
    update_time?: string | null;
  }>,
  t: (key: string) => string
): SessionGroup[] => {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const weekAgo = new Date(today.getTime() - 7 * 86400000);

  const groups: SessionGroup[] = [
    { label: t('sessions.today'), sessions: [] },
    { label: t('sessions.yesterday'), sessions: [] },
    { label: t('sessions.thisWeek'), sessions: [] },
    { label: t('sessions.earlier'), sessions: [] },
  ];

  for (const session of sessions) {
    const date = parseServerDate(session.update_time || session.create_time) || new Date(0);
    if (date >= today) {
      groups[0].sessions.push(session);
    } else if (date >= yesterday) {
      groups[1].sessions.push(session);
    } else if (date >= weekAgo) {
      groups[2].sessions.push(session);
    } else {
      groups[3].sessions.push(session);
    }
  }

  return groups.filter((g) => g.sessions.length > 0);
};

/**
 * 分析会话页面
 */
export const Sessions = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [searchQuery, setSearchQuery] = useState('');
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

  // API Hooks
  const { data: sessionsRes, isLoading } = useSessions({ page_size: 100 });
  const { data: dataSourcesRes } = useDataSources({ page_size: 200 });
  const deleteSessionMutation = useDeleteSession();
  const archiveSessionMutation = useArchiveSession();

  const sessions = sessionsRes?.data.data?.items || [];
  const dataSources = dataSourcesRes?.data.data?.items || [];
  const dataSourceNameMap = useMemo(() => {
    const map = new Map<string, string>();
    dataSources.forEach((ds) => map.set(ds.id, ds.name));
    return map;
  }, [dataSources]);

  // 过滤和分组
  const filteredSessions = useMemo(() => {
    if (!searchQuery.trim()) return sessions;
    const query = searchQuery.toLowerCase();
    return sessions.filter((s) => s.name.toLowerCase().includes(query) || s.description?.toLowerCase().includes(query));
  }, [sessions, searchQuery]);

  const groupedSessions = useMemo(() => groupSessionsByDate(filteredSessions, t), [filteredSessions, t]);

  // 统计
  const activeCount = sessions.filter((s) => s.status === 'active').length;
  const archivedCount = sessions.filter((s) => s.status === 'archived').length;

  // 删除会话
  const handleDelete = async () => {
    if (!deleteTarget) return;
    try {
      await deleteSessionMutation.mutateAsync(deleteTarget.id);
      toast({ title: t('common.success'), description: t('sessions.deleteSuccess') });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : '删除失败';
      toast({ title: t('common.error'), description: msg, variant: 'destructive' });
    } finally {
      setDeleteTarget(null);
    }
  };

  // 归档会话
  const handleArchive = async (id: string) => {
    try {
      await archiveSessionMutation.mutateAsync(id);
      toast({ title: t('common.success'), description: '会话已归档' });
    } catch {
      toast({ title: t('common.error'), description: '归档失败', variant: 'destructive' });
    }
  };

  return (
    <div className="container py-8 max-w-4xl">
      {/* 页面标题 */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('sessions.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('sessions.subtitle')}</p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          {t('sessions.create')}
        </Button>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-teal-500/10">
              <MessageSquare className="h-5 w-5 text-teal-600 dark:text-teal-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{sessions.length}</p>
              <p className="text-xs text-muted-foreground">全部会话</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-emerald-500/10">
              <Calendar className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{activeCount}</p>
              <p className="text-xs text-muted-foreground">进行中</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-slate-500/10">
              <Archive className="h-5 w-5 text-slate-600 dark:text-slate-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{archivedCount}</p>
              <p className="text-xs text-muted-foreground">已归档</p>
            </div>
          </div>
        </Card>
      </div>

      {/* 搜索框 */}
      <div className="relative mb-6">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="搜索会话..."
          className="pl-10"
        />
      </div>

      {/* 会话列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : sessions.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <EmptyState
              icon={MessageSquare}
              title={t('sessions.empty')}
              description={t('sessions.emptyHint')}
              action={
                <Button onClick={() => setShowCreateDialog(true)}>
                  <Plus className="h-4 w-4 mr-2" />
                  {t('sessions.create')}
                </Button>
              }
            />
          </CardContent>
        </Card>
      ) : filteredSessions.length === 0 ? (
        <Card>
          <CardContent className="py-12">
            <EmptyState icon={Search} title="未找到匹配的会话" description="尝试使用其他关键词搜索" />
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-6">
          {groupedSessions.map((group) => (
            <div key={group.label}>
              <h3 className="text-sm font-medium text-muted-foreground mb-3">{group.label}</h3>
              <Card>
                <CardContent className="p-0 divide-y">
                  {group.sessions.map((session) => (
                    <button
                      type="button"
                      key={session.id}
                      className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors text-left"
                      onClick={() => navigate(`/chat/${session.id}`)}
                    >
                      <div className="flex items-center gap-4 min-w-0">
                        <div className="p-2 rounded-lg bg-gradient-to-br from-teal-500/20 to-cyan-500/20">
                          <MessageSquare className="h-5 w-5 text-teal-600 dark:text-teal-400" />
                        </div>
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="font-medium truncate">{session.name}</p>
                            {session.status === 'archived' && (
                              <Badge variant="secondary" className="text-xs">
                                已归档
                              </Badge>
                            )}
                          </div>
                          <div className="flex items-center gap-3 text-sm text-muted-foreground">
                            {session.data_source_id && (
                              <span className="flex items-center gap-1">
                                <Database className="h-3 w-3" />
                                {dataSourceNameMap.get(session.data_source_id) || '数据源'}
                              </span>
                            )}
                            <span>{session.message_count ?? 0} 条消息</span>
                            <span>{formatRelativeTime(session.update_time || session.create_time)}</span>
                          </div>
                        </div>
                      </div>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                          <Button variant="ghost" size="icon">
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
                          {session.status !== 'archived' && (
                            <DropdownMenuItem onClick={() => handleArchive(session.id)}>
                              <Archive className="h-4 w-4 mr-2" />
                              {t('sessions.archive')}
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => setDeleteTarget({ id: session.id, name: session.name })}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            {t('common.delete')}
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </button>
                  ))}
                </CardContent>
              </Card>
            </div>
          ))}
        </div>
      )}

      {/* 对话框 */}
      <CreateSessionDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} />

      {/* 删除确认对话框 */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('dataSources.confirmDeleteTitle')}</AlertDialogTitle>
            <AlertDialogDescription>{t('sessions.confirmDelete', { name: deleteTarget?.name })}</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete} className="bg-destructive text-destructive-foreground">
              {t('common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};
