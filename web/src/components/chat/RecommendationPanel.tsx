import { useTranslation } from 'react-i18next';
import {
  BarChart3,
  TrendingUp,
  GitCompare,
  AlertTriangle,
  Share2,
  PieChart,
  Sparkles,
  RefreshCw,
} from 'lucide-react';
import { useRecommendations, useGenerateRecommendations } from '@/api';
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
};

const categoryColors: Record<string, string> = {
  overview: 'bg-blue-500/10 text-blue-500',
  trend: 'bg-green-500/10 text-green-500',
  comparison: 'bg-purple-500/10 text-purple-500',
  anomaly: 'bg-red-500/10 text-red-500',
  correlation: 'bg-amber-500/10 text-amber-500',
  distribution: 'bg-cyan-500/10 text-cyan-500',
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

  const handleGenerate = async () => {
    await generateMutation.mutateAsync({});
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
          <RefreshCw className={`h-4 w-4 ${generateMutation.isPending ? 'animate-spin' : ''}`} />
        </Button>
      </div>

      {/* 推荐列表 */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-3">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <RefreshCw className="h-5 w-5 animate-spin text-muted-foreground" />
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
            recommendations.map((rec) => (
              <button
                type="button"
                key={rec.id}
                className="w-full text-left p-3 rounded-lg border hover:bg-muted/50 transition-colors group"
                onClick={() => onSelect(rec.title)}
              >
                <div className="flex items-start gap-3">
                  <div className={`p-1.5 rounded ${categoryColors[rec.category] || 'bg-muted'}`}>
                    {categoryIcons[rec.category] || <Sparkles className="h-4 w-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="font-medium text-sm group-hover:text-primary transition-colors">
                      {rec.title}
                    </h4>
                    {rec.description && (
                      <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                        {rec.description}
                      </p>
                    )}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
};
