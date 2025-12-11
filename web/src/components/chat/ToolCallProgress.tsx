import { CheckCircle2, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { cn } from '@/lib/utils';
import type { LocalMessage, ToolCallState } from '@/types';
import { DataTable } from './DataTable';
import { PlotlyChart } from './PlotlyChart';

const toolNameMap: Record<string, string> = {
  execute_sql: 'SQL',
  execute_python: 'Python',
  generate_chart: '图表',
  quick_analysis: '分析',
  list_local_files: '文件',
};

// 工具图标组件
const ToolIcon = ({ name, isExecuting }: { name: string; isExecuting?: boolean }) => {
  const iconMap: Record<string, string> = {
    execute_sql: '🗃️',
    execute_python: '🐍',
    generate_chart: '📊',
    quick_analysis: '🔍',
    list_local_files: '📁',
  };

  return (
    <span className={cn('text-base', isExecuting && 'animate-bounce')}>
      {iconMap[name] || '⚡'}
    </span>
  );
};

interface ToolCallProgressProps {
  toolMessages: LocalMessage[];
  currentToolCall?: ToolCallState | null;
}

/**
 * 工具调用进度组件
 * 使用动画效果展示执行状态，减少文字干扰
 */
export const ToolCallProgress = ({ toolMessages, currentToolCall }: ToolCallProgressProps) => {
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());

  const isExecuting = !!currentToolCall && currentToolCall.status !== 'completed';

  const toggleExpand = (toolId: string) => {
    setExpandedTools((prev) => {
      const next = new Set(prev);
      if (next.has(toolId)) {
        next.delete(toolId);
      } else {
        next.add(toolId);
      }
      return next;
    });
  };

  const renderToolResult = (message: LocalMessage, isExpanded: boolean) => {
    const artifact = message.artifact;
    if (!artifact || !isExpanded) return null;

    switch (artifact.type) {
      case 'plotly':
        if (artifact.chart_json) {
          return (
            <div className="mt-2">
              <PlotlyChart chartJson={artifact.chart_json} title={artifact.title} />
            </div>
          );
        }
        break;

      case 'table':
      case 'sql':
        if (artifact.columns && artifact.rows) {
          return (
            <div className="mt-2">
              <DataTable
                columns={artifact.columns}
                rows={artifact.rows as unknown[][]}
                title={artifact.title || `${artifact.rows.length} 行`}
              />
            </div>
          );
        }
        break;

      case 'code':
        return (
          <div className="mt-2 space-y-2">
            {artifact.code && (
              <pre className="p-2 bg-muted rounded-md overflow-x-auto">
                <code className="text-xs font-mono">{artifact.code}</code>
              </pre>
            )}
            {artifact.output && (
              <pre className="p-2 bg-black/90 text-green-400 rounded-md overflow-x-auto text-xs font-mono whitespace-pre-wrap max-h-[200px]">
                {artifact.output}
              </pre>
            )}
          </div>
        );

      case 'error':
        return (
          <div className="mt-2 p-2 bg-destructive/10 border border-destructive/20 rounded-md">
            <pre className="text-xs text-destructive/90 font-mono whitespace-pre-wrap max-h-[150px] overflow-y-auto">
              {artifact.error_message}
            </pre>
          </div>
        );
    }

    return null;
  };

  const getToolSummary = (message: LocalMessage): string => {
    const artifact = message.artifact;
    if (!artifact) return '';

    switch (artifact.type) {
      case 'plotly':
        return artifact.title || '';
      case 'table':
      case 'sql':
        return `${artifact.rows?.length || 0} 行`;
      case 'code':
        return artifact.files_created?.length ? `${artifact.files_created.length} 文件` : '';
      case 'error':
        return '失败';
      default:
        return '';
    }
  };

  // 不渲染空状态
  if (toolMessages.length === 0 && !currentToolCall) return null;
  if (toolMessages.length === 0 && !isExecuting) return null;

  return (
    <div className="flex gap-3 my-2">
      {/* 左侧动画指示器 */}
      <div className="relative w-8 flex flex-col items-center pt-1">
        {/* 主圆圈 */}
        <div
          className={cn(
            'w-8 h-8 rounded-full flex items-center justify-center transition-all duration-300',
            isExecuting
              ? 'bg-gradient-to-br from-amber-400 to-orange-500 shadow-lg shadow-amber-500/30'
              : 'bg-gradient-to-br from-emerald-400 to-teal-500 shadow-lg shadow-emerald-500/20'
          )}
        >
          {isExecuting ? (
            // 执行中：脉冲动画
            <>
              <div className="absolute inset-0 rounded-full bg-amber-400 animate-ping opacity-30" />
              <ToolIcon name={currentToolCall?.name ?? ''} isExecuting />
            </>
          ) : (
            // 完成：对勾图标
            <CheckCircle2 className="w-4 h-4 text-white" />
          )}
        </div>

        {/* 连接线（如果有多个工具） */}
        {(toolMessages.length > 0 || isExecuting) && (
          <div
            className={cn(
              'w-0.5 flex-1 mt-1 rounded-full transition-colors duration-300',
              isExecuting ? 'bg-gradient-to-b from-amber-400 to-transparent' : 'bg-gradient-to-b from-emerald-400 to-transparent'
            )}
          />
        )}
      </div>

      {/* 工具列表 */}
      <div className="flex-1 min-w-0 space-y-1.5">
        {/* 已完成的工具 */}
        {toolMessages.map((msg) => {
          const toolId = String(msg.id);
          const isExpanded = expandedTools.has(toolId);
          const displayName = toolNameMap[msg.tool_name || ''] || msg.tool_name || '工具';
          const summary = getToolSummary(msg);
          const hasError = msg.artifact?.type === 'error';
          const hasChart = msg.artifact?.type === 'plotly';

          return (
            <div
              key={toolId}
              className={cn(
                'border rounded-xl overflow-hidden transition-all duration-200',
                hasError ? 'border-red-200 dark:border-red-800' : 'border-border/50',
                isExpanded && 'shadow-sm'
              )}
            >
              <button
                type="button"
                className={cn(
                  'w-full flex items-center gap-2 px-3 py-2 text-sm transition-all duration-200',
                  'hover:bg-muted/50',
                  hasError && 'bg-red-50/50 dark:bg-red-950/20'
                )}
                onClick={() => toggleExpand(toolId)}
              >
                {/* 展开/收起图标 */}
                <div
                  className={cn(
                    'transition-transform duration-200',
                    isExpanded && 'rotate-90'
                  )}
                >
                  <ChevronRight className="w-4 h-4 text-muted-foreground" />
                </div>

                {/* 工具图标 */}
                <ToolIcon name={msg.tool_name || ''} />

                {/* 工具名称 */}
                <span className="font-medium">{displayName}</span>

                {/* 结果摘要 */}
                {summary && (
                  <span
                    className={cn(
                      'text-xs px-1.5 py-0.5 rounded-full',
                      hasError
                        ? 'bg-red-100 text-red-600 dark:bg-red-900/50 dark:text-red-400'
                        : 'bg-muted text-muted-foreground'
                    )}
                  >
                    {summary}
                  </span>
                )}

                {/* 图表提示 */}
                {hasChart && !isExpanded && (
                  <span className="ml-auto text-xs text-primary/70 flex items-center gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                  </span>
                )}
              </button>

              {/* 展开内容 */}
              <div
                className={cn(
                  'overflow-hidden transition-all duration-300',
                  isExpanded ? 'max-h-[600px] opacity-100' : 'max-h-0 opacity-0'
                )}
              >
                <div className="px-3 pb-3 border-t bg-muted/10">
                  {renderToolResult(msg, isExpanded)}
                </div>
              </div>
            </div>
          );
        })}

        {/* 正在执行的工具 */}
        {isExecuting && (
          <div className="border border-amber-200 dark:border-amber-800 rounded-xl overflow-hidden bg-gradient-to-r from-amber-50/80 to-orange-50/80 dark:from-amber-950/30 dark:to-orange-950/30">
            <div className="px-3 py-2.5">
              <div className="flex items-center gap-2">
                {/* 动画图标 */}
                <div className="relative">
                  <ToolIcon name={currentToolCall?.name ?? ''} isExecuting />
                  {/* 环形进度动画 */}
                  <div className="absolute -inset-1">
                    <svg className="w-7 h-7 animate-spin" viewBox="0 0 24 24" aria-hidden="true">
                      <circle
                        className="opacity-20"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="2"
                        fill="none"
                      />
                      <circle
                        className="text-amber-500"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="2"
                        fill="none"
                        strokeLinecap="round"
                        strokeDasharray="60"
                        strokeDashoffset="45"
                      />
                    </svg>
                  </div>
                </div>

                {/* 工具名称 */}
                <span className="font-medium text-amber-700 dark:text-amber-300">
                  {(currentToolCall?.name && toolNameMap[currentToolCall.name]) || currentToolCall?.name || '工具'}
                </span>

                {/* 跳动的点 */}
                <div className="flex gap-1 ml-auto">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-500 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>

              {/* 流动进度条 */}
              <div className="mt-2 h-1 bg-amber-200/50 dark:bg-amber-800/30 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-amber-400 via-orange-400 to-amber-400 rounded-full"
                  style={{
                    width: '40%',
                    animation: 'flowProgress 1.5s ease-in-out infinite',
                  }}
                />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 全局动画样式 */}
      <style>{`
        @keyframes flowProgress {
          0% { transform: translateX(-100%); }
          100% { transform: translateX(350%); }
        }
      `}</style>
    </div>
  );
};
