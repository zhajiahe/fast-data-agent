import { CheckCircle2, Loader2, Wrench, XCircle } from 'lucide-react';
import { cn } from '@/lib/utils';

interface ToolCallDisplayProps {
  toolCall: {
    id: string;
    name: string;
    status: 'calling' | 'executing' | 'completed' | 'error';
  };
}

const toolNameMap: Record<string, string> = {
  execute_sql: 'SQL 查询',
  execute_python: 'Python 执行',
  generate_chart: '生成图表',
  quick_analysis: '快速分析',
  list_local_files: '列出文件',
};

/**
 * 工具调用状态展示组件
 */
export const ToolCallDisplay = ({ toolCall }: ToolCallDisplayProps) => {
  const displayName = toolNameMap[toolCall.name] || toolCall.name;

  const statusConfig = {
    calling: {
      icon: <Loader2 className="w-4 h-4 animate-spin" />,
      text: '准备调用...',
      className: 'text-muted-foreground',
    },
    executing: {
      icon: <Loader2 className="w-4 h-4 animate-spin text-amber-500" />,
      text: '执行中...',
      className: 'text-amber-500',
    },
    completed: {
      icon: <CheckCircle2 className="w-4 h-4 text-green-500" />,
      text: '完成',
      className: 'text-green-500',
    },
    error: {
      icon: <XCircle className="w-4 h-4 text-destructive" />,
      text: '失败',
      className: 'text-destructive',
    },
  };

  const config = statusConfig[toolCall.status];

  return (
    <div className="flex items-center gap-3 py-3">
      <div className="w-8 h-8 rounded-full bg-amber-500/10 flex items-center justify-center shrink-0">
        <Wrench className="w-4 h-4 text-amber-500" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-medium text-sm">{displayName}</span>
          <div className={cn('flex items-center gap-1 text-xs', config.className)}>
            {config.icon}
            <span>{config.text}</span>
          </div>
        </div>
        {toolCall.status === 'executing' && (
          <div className="mt-2 h-1 bg-muted rounded-full overflow-hidden">
            <div className="h-full bg-amber-500 rounded-full animate-pulse w-2/3" />
          </div>
        )}
      </div>
    </div>
  );
};
