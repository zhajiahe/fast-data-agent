import { useQueries } from '@tanstack/react-query';
import type { AxiosResponse } from 'axios';
import { BarChart3, Download, ExternalLink, Maximize2, Search, Sparkles } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  type BaseResponsePageResponseChatMessageResponse,
  getMessagesApiV1SessionsSessionIdMessagesGet,
  useSessions,
} from '@/api';
import { EmptyState } from '@/components/common';
import { PlotlyChart } from '@/components/chat/PlotlyChart';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';

// 图表数据类型
interface ChartItem {
  id: string;
  title: string;
  chartJson: string;
  sessionId: string;
  sessionName: string;
  createTime: string;
}

// Artifact 类型（与 ChatMessage.tsx 保持一致）
interface MessageArtifact {
  type: string;
  chart_json?: string;
  title?: string;
}

/**
 * 图表工作台页面
 * 展示所有分析会话中生成的可视化图表
 */
export const Charts = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [previewChart, setPreviewChart] = useState<ChartItem | null>(null);

  // 获取所有会话
  const { data: sessionsResponse, isLoading: isLoadingSessions } = useSessions({ page_size: 100 });
  const sessions = sessionsResponse?.data.data?.items || [];

  // 并行获取所有会话的消息
  const messagesQueries = useQueries({
    queries: sessions.map((session) => ({
      queryKey: ['messages', session.id, { page_size: 200 }],
      queryFn: () =>
        getMessagesApiV1SessionsSessionIdMessagesGet(session.id, { page_size: 200 }) as Promise<
          AxiosResponse<BaseResponsePageResponseChatMessageResponse>
        >,
      enabled: !!session.id,
      staleTime: 5 * 60 * 1000, // 5 分钟缓存
    })),
  });

  const isLoadingMessages = messagesQueries.some((q) => q.isLoading);
  const isLoading = isLoadingSessions || isLoadingMessages;

  // 从所有消息中提取图表
  const charts: ChartItem[] = useMemo(() => {
    const result: ChartItem[] = [];

    messagesQueries.forEach((query, index) => {
      if (!query.data?.data.data?.items) return;

      const session = sessions[index];
      const messages = query.data.data.data.items;

      messages.forEach((msg) => {
        const artifact = msg.artifact as MessageArtifact | null;
        if (artifact?.type === 'plotly' && artifact.chart_json) {
          // 尝试从 chart_json 中提取标题
          let chartTitle = artifact.title || '';
          if (!chartTitle) {
            try {
              const chartData = JSON.parse(artifact.chart_json);
              chartTitle = chartData.layout?.title?.text || chartData.layout?.title || '';
            } catch {
              // ignore
            }
          }

          result.push({
            id: msg.id,
            title: chartTitle || t('charts.untitledChart'),
            chartJson: artifact.chart_json,
            sessionId: session.id,
            sessionName: session.name,
            createTime: msg.create_time || session.create_time || '',
          });
        }
      });
    });

    // 按创建时间降序排序
    return result.sort((a, b) => new Date(b.createTime).getTime() - new Date(a.createTime).getTime());
  }, [messagesQueries, sessions, t]);

  // 搜索过滤
  const filteredCharts = useMemo(() => {
    if (!searchQuery.trim()) return charts;
    const query = searchQuery.toLowerCase();
    return charts.filter(
      (chart) =>
        chart.title.toLowerCase().includes(query) ||
        chart.sessionName.toLowerCase().includes(query) ||
        chart.chartJson.toLowerCase().includes(query)
    );
  }, [charts, searchQuery]);

  // 统计数据
  const totalCharts = charts.length;
  const thisWeekCharts = charts.filter((chart) => {
    const chartDate = new Date(chart.createTime);
    const weekAgo = new Date();
    weekAgo.setDate(weekAgo.getDate() - 7);
    return chartDate >= weekAgo;
  }).length;

  const stats = [
    {
      title: t('charts.totalCharts'),
      value: totalCharts,
      icon: BarChart3,
      color: 'text-cyan-600 dark:text-cyan-400',
      bgColor: 'bg-cyan-500/10',
    },
    {
      title: t('charts.thisWeek'),
      value: thisWeekCharts,
      icon: Sparkles,
      color: 'text-teal-600 dark:text-teal-400',
      bgColor: 'bg-teal-500/10',
    },
  ];

  // 格式化日期
  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    return new Date(dateStr).toLocaleDateString('zh-CN', {
      month: 'short',
      day: 'numeric',
    });
  };

  // 下载图表
  const handleDownload = (chart: ChartItem, e: React.MouseEvent) => {
    e.stopPropagation();
    // 创建临时元素渲染图表并下载
    const tempDiv = document.createElement('div');
    tempDiv.style.position = 'absolute';
    tempDiv.style.left = '-9999px';
    document.body.appendChild(tempDiv);

    try {
      const chartData = JSON.parse(chart.chartJson);
      if (window.Plotly) {
        window.Plotly.newPlot(tempDiv, chartData.data, chartData.layout, { displayModeBar: false });
        window.Plotly.downloadImage(tempDiv, {
          format: 'png',
          width: 1200,
          height: 800,
          filename: chart.title || 'chart',
        });
      }
    } catch (err) {
      console.error('Download failed:', err);
    } finally {
      document.body.removeChild(tempDiv);
    }
  };

  // 跳转到会话
  const handleGoToSession = (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigate(`/chat/${sessionId}`);
  };

  return (
    <div className="container py-8 max-w-6xl">
      {/* 页面标题 */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold tracking-tight">{t('charts.title')}</h1>
        <p className="text-muted-foreground mt-1">{t('charts.subtitle')}</p>
      </div>

      {/* 统计卡片和搜索 */}
      <div className="flex flex-col md:flex-row gap-4 mb-8">
        <div className="flex gap-4">
          {stats.map((stat) => (
            <Card key={stat.title} className="min-w-[140px]">
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">{stat.title}</CardTitle>
                <div className={`p-2 rounded-lg ${stat.bgColor}`}>
                  <stat.icon className={`h-4 w-4 ${stat.color}`} />
                </div>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* 搜索框 */}
        <div className="flex-1 md:max-w-sm md:ml-auto">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder={t('charts.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>
      </div>

      {/* 图表列表 */}
      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
        </div>
      ) : filteredCharts.length === 0 ? (
        <Card>
          <CardContent className="py-16">
            <EmptyState
              icon={BarChart3}
              title={searchQuery ? t('charts.noSearchResults') : t('charts.empty')}
              description={searchQuery ? t('charts.tryDifferentSearch') : t('charts.emptyHint')}
              action={
                !searchQuery && (
                  <Button onClick={() => navigate('/sessions')}>{t('charts.goToSessions')}</Button>
                )
              }
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filteredCharts.map((chart) => (
            <Card
              key={chart.id}
              className="group cursor-pointer hover:shadow-md transition-shadow overflow-hidden"
              onClick={() => setPreviewChart(chart)}
            >
              {/* 图表预览区 */}
              <div className="relative h-[200px] bg-muted/30 overflow-hidden">
                <div className="absolute inset-0 pointer-events-none">
                  <PlotlyChart chartJson={chart.chartJson} compact />
                </div>
                {/* hover 操作按钮 */}
                <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <Button
                    variant="secondary"
                    size="icon"
                    className="h-8 w-8"
                    onClick={(e) => {
                      e.stopPropagation();
                      setPreviewChart(chart);
                    }}
                  >
                    <Maximize2 className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="secondary"
                    size="icon"
                    className="h-8 w-8"
                    onClick={(e) => handleDownload(chart, e)}
                  >
                    <Download className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              {/* 图表信息 */}
              <CardContent className="p-4">
                <h3 className="font-medium truncate">{chart.title}</h3>
                <div className="flex items-center justify-between mt-2 text-sm text-muted-foreground">
                  <button
                    type="button"
                    className="flex items-center gap-1 hover:text-foreground transition-colors"
                    onClick={(e) => handleGoToSession(chart.sessionId, e)}
                  >
                    <ExternalLink className="h-3 w-3" />
                    {chart.sessionName}
                  </button>
                  <span>{formatDate(chart.createTime)}</span>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* 图表预览弹窗 */}
      <Dialog open={!!previewChart} onOpenChange={(open) => !open && setPreviewChart(null)}>
        <DialogContent className="max-w-4xl max-h-[90vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>{previewChart?.title || t('charts.preview')}</span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => previewChart && navigate(`/chat/${previewChart.sessionId}`)}
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  {t('charts.viewSession')}
                </Button>
              </div>
            </DialogTitle>
          </DialogHeader>
          <div className="mt-4">
            {previewChart && <PlotlyChart chartJson={previewChart.chartJson} title={previewChart.title} />}
          </div>
          <div className="mt-4 text-sm text-muted-foreground">
            {t('charts.from')}: {previewChart?.sessionName} · {previewChart && formatDate(previewChart.createTime)}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};
