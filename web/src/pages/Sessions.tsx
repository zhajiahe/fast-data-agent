import { Archive, Calendar, Database, MessageSquare, MoreHorizontal, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { type AnalysisSessionResponse, useArchiveSession, useDeleteSession, useSessions } from '@/api';
import { EmptyState, LoadingState } from '@/components/common';
import { CreateSessionDialog } from '@/components/session/CreateSessionDialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useConfirmDialog, useToast } from '@/hooks';

/**
 * 会话列表页面
 */
export const Sessions = () => {
  const { t } = useTranslation();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const { confirm, ConfirmDialog } = useConfirmDialog();

  const { data: response, isLoading } = useSessions();
  const deleteSessionMutation = useDeleteSession();
  const archiveSessionMutation = useArchiveSession();

  const sessions = response?.data.data?.items || [];

  const handleDelete = async (id: number, name: string) => {
    const confirmed = await confirm({
      title: t('sessions.confirmDeleteTitle'),
      description: t('sessions.confirmDelete', { name }),
      confirmText: t('common.delete'),
      cancelText: t('common.cancel'),
      variant: 'destructive',
    });

    if (!confirmed) return;

    deleteSessionMutation.mutate(id, {
      onSuccess: () => {
        toast({ title: t('common.success'), description: t('sessions.deleteSuccess') });
      },
    });
  };

  const handleArchive = async (id: number) => {
    archiveSessionMutation.mutate(id, {
      onSuccess: () => {
        toast({ title: t('common.success'), description: '会话已归档' });
      },
    });
  };

  const handleOpenSession = (id: number) => {
    navigate(`/chat/${id}`);
  };

  // 按日期分组会话
  const groupSessionsByDate = (sessionList: AnalysisSessionResponse[]) => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const weekAgo = new Date(today);
    weekAgo.setDate(weekAgo.getDate() - 7);

    const groups: { title: string; sessions: AnalysisSessionResponse[] }[] = [
      { title: t('sessions.today'), sessions: [] },
      { title: t('sessions.yesterday'), sessions: [] },
      { title: t('sessions.thisWeek'), sessions: [] },
      { title: t('sessions.earlier'), sessions: [] },
    ];

    for (const session of sessionList) {
      const date = new Date(session.create_time || '');
      date.setHours(0, 0, 0, 0);

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

  const groupedSessions = groupSessionsByDate(sessions);

  return (
    <div className="container py-8 max-w-4xl">
      {/* 页面标题 */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{t('sessions.title')}</h1>
          <p className="text-muted-foreground mt-1">{t('sessions.subtitle')}</p>
        </div>
        <Button size="sm" onClick={() => setShowCreateDialog(true)}>
          <Plus className="h-4 w-4 mr-2" />
          {t('sessions.create')}
        </Button>
      </div>

      {/* 会话列表 */}
      {isLoading ? (
        <LoadingState />
      ) : sessions.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="py-0">
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
      ) : (
        <div className="space-y-8">
          {groupedSessions.map((group) => (
            <div key={group.title}>
              <h2 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
                <Calendar className="h-4 w-4" />
                {group.title}
              </h2>
              <div className="space-y-2">
                {group.sessions.map((session) => (
                  <Card
                    key={session.id}
                    className="group hover:shadow-md transition-shadow cursor-pointer"
                    onClick={() => handleOpenSession(session.id)}
                  >
                    <CardHeader className="py-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <CardTitle className="text-base truncate">{session.name}</CardTitle>
                          {session.description && (
                            <CardDescription className="text-sm mt-1 line-clamp-1">
                              {session.description}
                            </CardDescription>
                          )}
                        </div>
                        <div className="flex items-center gap-2 ml-4">
                          <Badge variant="secondary" className="shrink-0">
                            <Database className="h-3 w-3 mr-1" />
                            {session.data_source_ids?.length || 0}
                          </Badge>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity"
                              >
                                <MoreHorizontal className="h-4 w-4" />
                              </Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent align="end">
                              <DropdownMenuItem
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleArchive(session.id);
                                }}
                              >
                                <Archive className="h-4 w-4 mr-2" />
                                {t('sessions.archive')}
                              </DropdownMenuItem>
                              <DropdownMenuSeparator />
                              <DropdownMenuItem
                                className="text-destructive"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleDelete(session.id, session.name);
                                }}
                              >
                                <Trash2 className="h-4 w-4 mr-2" />
                                {t('common.delete')}
                              </DropdownMenuItem>
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </div>
                    </CardHeader>
                  </Card>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <CreateSessionDialog open={showCreateDialog} onOpenChange={setShowCreateDialog} />
      <ConfirmDialog />
    </div>
  );
};
