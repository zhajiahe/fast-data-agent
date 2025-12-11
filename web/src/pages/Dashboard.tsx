import { ArrowRight, BarChart3, CheckCircle2, Circle, Clock, Database, MessageSquare, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useDataSources, useSessions } from '@/api';
import { EmptyState } from '@/components/common';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuthStore } from '@/stores/authStore';

/**
 * 仪表盘页面
 * 色彩方案：slate（数据库）、teal（会话/主品牌）、cyan（图表）
 */
export const Dashboard = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user } = useAuthStore();

  const { data: dataSourcesResponse } = useDataSources({ page_size: 100 });
  const { data: sessionsResponse } = useSessions({ page_size: 5 });

  const dataSources = dataSourcesResponse?.data.data?.items || [];
  const sessions = sessionsResponse?.data.data?.items || [];
  const totalSessions = sessionsResponse?.data.data?.total || 0;

  const stats = [
    {
      title: t('dashboard.totalDataSources'),
      value: dataSources.length,
      subValue: `${dataSources.length} ${t('dashboard.active')}`,
      icon: Database,
      color: 'text-slate-600 dark:text-slate-400',
      bgColor: 'bg-slate-500/10',
    },
    {
      title: t('dashboard.totalSessions'),
      value: totalSessions,
      subValue: t('dashboard.thisWeek'),
      icon: MessageSquare,
      color: 'text-teal-600 dark:text-teal-400',
      bgColor: 'bg-teal-500/10',
    },
    {
      title: t('dashboard.chartsGenerated'),
      value: '-',
      subValue: t('dashboard.comingSoon'),
      icon: BarChart3,
      color: 'text-cyan-600 dark:text-cyan-400',
      bgColor: 'bg-cyan-500/10',
    },
  ];

  return (
    <div className="container py-8 max-w-6xl">
      {/* 欢迎信息 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">
          {t('dashboard.welcome', { name: user?.nickname || user?.username })}
        </h1>
        <p className="text-muted-foreground mt-1">{t('dashboard.subtitle')}</p>
      </div>

      {/* 统计卡片 */}
      <div className="grid gap-4 md:grid-cols-3 mb-8">
        {stats.map((stat) => (
          <Card key={stat.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">{stat.title}</CardTitle>
              <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`h-4 w-4 ${stat.color}`} />
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-muted-foreground">{stat.subValue}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* 快速指引 - 仅在新用户或没有会话时显示 */}
      {sessions.length === 0 && (
        <Card className="mb-8 border-dashed border-primary/30 bg-gradient-to-br from-primary/5 to-transparent">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <span className="text-xl">🚀</span>
              {t('dashboard.quickStart.title')}
            </CardTitle>
            <CardDescription>{t('dashboard.quickStart.subtitle')}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[
                {
                  step: 1,
                  title: t('dashboard.quickStart.step1Title'),
                  desc: t('dashboard.quickStart.step1Desc'),
                  done: dataSources.length > 0,
                  action: () => navigate('/data-sources'),
                },
                {
                  step: 2,
                  title: t('dashboard.quickStart.step2Title'),
                  desc: t('dashboard.quickStart.step2Desc'),
                  done: false,
                  action: () => navigate('/sessions'),
                },
                {
                  step: 3,
                  title: t('dashboard.quickStart.step3Title'),
                  desc: t('dashboard.quickStart.step3Desc'),
                  done: false,
                  action: null,
                },
              ].map((item) => (
                <div
                  key={item.step}
                  className={`flex items-start gap-4 p-3 rounded-lg transition-colors ${
                    item.done ? 'bg-emerald-500/10' : 'hover:bg-muted/50'
                  } ${item.action && !item.done ? 'cursor-pointer' : ''}`}
                  onClick={() => !item.done && item.action?.()}
                  onKeyDown={(e) => e.key === 'Enter' && !item.done && item.action?.()}
                  tabIndex={item.action && !item.done ? 0 : -1}
                  role={item.action && !item.done ? 'button' : undefined}
                >
                  <div className="shrink-0 mt-0.5">
                    {item.done ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-500" />
                    ) : (
                      <Circle className="h-5 w-5 text-muted-foreground" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className={`font-medium text-sm ${item.done ? 'text-emerald-600 dark:text-emerald-400' : ''}`}>
                      {t('dashboard.quickStart.stepLabel', { n: item.step })} {item.title}
                    </p>
                    <p className="text-xs text-muted-foreground mt-0.5">{item.desc}</p>
                  </div>
                  {item.action && !item.done && (
                    <ArrowRight className="h-4 w-4 text-muted-foreground shrink-0" />
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 快速操作 - 使用 teal/cyan 色系 */}
      <div className="grid gap-4 md:grid-cols-2 mb-8">
        <Card className="group hover:shadow-md transition-shadow cursor-pointer" onClick={() => navigate('/sessions')}>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-xl bg-gradient-to-br from-teal-500 to-cyan-600">
                <Plus className="h-6 w-6 text-white" />
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:translate-x-1 transition-transform" />
            </div>
            <CardTitle className="mt-4">{t('dashboard.newSession')}</CardTitle>
            <CardDescription>{t('dashboard.newSessionDesc')}</CardDescription>
          </CardHeader>
        </Card>

        <Card
          className="group hover:shadow-md transition-shadow cursor-pointer"
          onClick={() => navigate('/data-sources')}
        >
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="p-3 rounded-xl bg-gradient-to-br from-slate-600 to-slate-700">
                <Database className="h-6 w-6 text-white" />
              </div>
              <ArrowRight className="h-5 w-5 text-muted-foreground group-hover:translate-x-1 transition-transform" />
            </div>
            <CardTitle className="mt-4">{t('dashboard.addDataSource')}</CardTitle>
            <CardDescription>{t('dashboard.addDataSourceDesc')}</CardDescription>
          </CardHeader>
        </Card>
      </div>

      {/* 最近会话 */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-5 w-5" />
              {t('dashboard.recentSessions')}
            </CardTitle>
            <CardDescription>{t('dashboard.recentSessionsDesc')}</CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={() => navigate('/sessions')}>
            {t('common.viewAll')}
          </Button>
        </CardHeader>
        <CardContent>
          {sessions.length === 0 ? (
            <EmptyState
              icon={MessageSquare}
              title={t('dashboard.noRecentSessions')}
              action={
                <Button variant="link" onClick={() => navigate('/sessions')}>
                  {t('dashboard.createFirstSession')}
                </Button>
              }
            />
          ) : (
            <div className="space-y-3">
              {sessions.map((session) => (
                <button
                  type="button"
                  key={session.id}
                  className="w-full flex items-center justify-between p-3 rounded-lg hover:bg-muted cursor-pointer transition-colors text-left"
                  onClick={() => navigate(`/chat/${session.id}`)}
                >
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-muted">
                      <MessageSquare className="h-4 w-4 text-muted-foreground" />
                    </div>
                    <div>
                      <p className="font-medium text-sm">{session.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(session.update_time || session.create_time || '').toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground">
                      {(session.data_source_id ? 1 : 0)} {t('dashboard.dataSources')}
                    </span>
                    <ArrowRight className="h-4 w-4 text-muted-foreground" />
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
