import {
  AlertTriangle,
  BarChart3,
  GitCompare,
  MessageCircle,
  PieChart,
  RefreshCw,
  Share2,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import { useEffect, useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { type TaskRecommendationResponse, useGenerateRecommendations, useRecommendations } from '@/api';
import { LoadingSpinner } from '@/components/common';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

interface RecommendationPanelProps {
  sessionId: number;
  onSelect: (query: string) => void;
}

const categoryIcons: Record<string, React.ReactNode> = {
  overview: <BarChart3 className="h-4 w-4" />,
  trend: <TrendingUp className="h-4 w-4" />,
  comparison: <GitCompare className="h-4 w-4" />,
  anomaly: <AlertTriangle className="h-4 w-4" />,
  correlation: <Share2 className="h-4 w-4" />,
  distribution: <PieChart className="h-4 w-4" />,
  followup: <MessageCircle className="h-4 w-4" />,
};

// 色彩方案：使用 slate/teal/cyan 主色系 + 语义色（amber/red）
const categoryColors: Record<string, string> = {
  overview: 'bg-slate-500/10 text-slate-600 dark:text-slate-400',
  trend: 'bg-teal-500/10 text-teal-600 dark:text-teal-400',
  comparison: 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400',
  anomaly: 'bg-red-500/10 text-red-600 dark:text-red-400',
  correlation: 'bg-amber-500/10 text-amber-600 dark:text-amber-400',
  distribution: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400',
  followup: 'bg-teal-500/10 text-teal-600 dark:text-teal-400',
};

// 推荐卡片组件
const RecommendationCard = ({
  rec,
  onSelect,
  isFollowup = false,
}: {
  rec: TaskRecommendationResponse;
  onSelect: (query: string) => void;
  isFollowup?: boolean;
}) => {
  const icon = isFollowup ? categoryIcons.followup : categoryIcons[rec.category] || <Sparkles className="h-4 w-4" />;
  const color = isFollowup ? categoryColors.followup : categoryColors[rec.category] || 'bg-muted';

  return (
    <button
      type="button"
      className="w-full text-left p-3 rounded-lg border hover:bg-muted/50 transition-colors group"
      onClick={() => onSelect(rec.description || rec.title)}
    >
      <div className="flex items-start gap-3">
        <div className={`p-1.5 rounded ${color}`}>{icon}</div>
        <div className="flex-1 min-w-0">
          <h4 className="font-medium text-sm group-hover:text-primary transition-colors">{rec.title}</h4>
          {rec.description && <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{rec.description}</p>}
        </div>
      </div>
    </button>
  );
};

/**
 * 任务推荐面板
 */
export const RecommendationPanel = ({ sessionId, onSelect }: RecommendationPanelProps) => {
  const { t } = useTranslation();

  // 使用生成的 API hooks
  const { data: response, isLoading, refetch } = useRecommendations(sessionId, { status_filter: 'pending' });
  const generateMutation = useGenerateRecommendations(sessionId);

  const recommendations = response?.data.data?.items || [];
  const hasLoadedRef = useRef(false);
  const hasDataLoaded = !!response?.data.data;
  const isPending = generateMutation.isPending;

  // 首次加载时，如果没有推荐，自动生成
  useEffect(() => {
    // 只在首次加载完成且没有推荐时自动生成
    if (!isLoading && !hasLoadedRef.current && hasDataLoaded) {
      hasLoadedRef.current = true;
      if (recommendations.length === 0 && !isPending) {
        generateMutation.mutate({});
      }
    }
  }, [isLoading, recommendations.length, hasDataLoaded, isPending, generateMutation.mutate]);

  // 分离初始推荐和后续问题推荐
  const { initialRecs, followupRecs } = useMemo(() => {
    const initial: TaskRecommendationResponse[] = [];
    const followup: TaskRecommendationResponse[] = [];

    for (const rec of recommendations) {
      if (rec.source_type === 'follow_up') {
        followup.push(rec);
      } else {
        initial.push(rec);
      }
    }

    return { initialRecs: initial, followupRecs: followup };
  }, [recommendations]);

  const handleGenerate = async () => {
    // 使用 force_regenerate: true 来清除旧推荐并重新生成
    await generateMutation.mutateAsync({ force_regenerate: true });
    refetch();
  };

  return (
    <div className="h-full flex flex-col">
      {/* 标题 */}
      <div className="px-4 py-3 border-b flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sparkles className="h-4 w-4 text-primary" />
          <span className="font-medium text-sm">{t('chat.recommendations')}</span>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={handleGenerate}
          disabled={generateMutation.isPending}
        >
          {generateMutation.isPending ? <LoadingSpinner size="sm" /> : <RefreshCw className="h-4 w-4" />}
        </Button>
      </div>

      {/* 推荐列表 */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <LoadingSpinner size="md" />
            </div>
          ) : recommendations.length === 0 ? (
            <div className="text-center py-8">
              <Sparkles className="h-8 w-8 mx-auto text-muted-foreground mb-2" />
              <p className="text-sm text-muted-foreground">{t('chat.noRecommendations')}</p>
              <Button
                variant="outline"
                size="sm"
                className="mt-3"
                onClick={handleGenerate}
                disabled={generateMutation.isPending}
              >
                {t('chat.generateRecommendations')}
              </Button>
            </div>
          ) : (
            <div className="space-y-2">
              {(followupRecs.length > 0 ? followupRecs : initialRecs).map((rec) => (
                <RecommendationCard key={rec.id} rec={rec} onSelect={onSelect} isFollowup={followupRecs.length > 0} />
              ))}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
};
