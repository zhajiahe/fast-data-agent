import { AlertCircle, Bot, User, Wrench } from 'lucide-react';
import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import { DataTable } from './DataTable';
import { PlotlyChart } from './PlotlyChart';

// 扩展的消息类型（包含更多 artifact 属性用于展示）
interface MessageArtifact {
  type: string;
  // plotly
  chart_json?: string;
  // table / sql
  columns?: string[];
  rows?: unknown[][];
  title?: string;
  // sql
  sql?: string;
  total_rows?: number;
  truncated?: boolean;
  result_file?: string;
  // code
  code?: string;
  output?: string;
  files_created?: string[];
  // error
  tool?: string;
  error_message?: string;
  // file
  filename?: string;
}

interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
}

interface LocalMessage {
  id: number | string; // 支持数字（持久化消息）和字符串（临时工具消息）
  session_id: number;
  message_type: string;
  content: string;
  tool_call_id?: string;
  tool_name?: string;
  tool_calls?: ToolCall[];
  artifact?: MessageArtifact;
  create_time: string;
}

interface ChatMessageProps {
  message: LocalMessage;
  isStreaming?: boolean;
}

/**
 * 聊天消息组件
 */
export const ChatMessage = ({ message, isStreaming }: ChatMessageProps) => {
  const isUser = message.message_type === 'human';
  const isTool = message.message_type === 'tool';

  const avatar = useMemo(() => {
    if (isUser) {
      return (
        <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center shrink-0">
          <User className="w-4 h-4 text-primary-foreground" />
        </div>
      );
    }
    if (isTool) {
      return (
        <div className="w-8 h-8 rounded-full bg-amber-500 flex items-center justify-center shrink-0">
          <Wrench className="w-4 h-4 text-white" />
        </div>
      );
    }
    return (
      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-violet-500 to-purple-600 flex items-center justify-center shrink-0">
        <Bot className="w-4 h-4 text-white" />
      </div>
    );
  }, [isUser, isTool]);

  // 可折叠容器
  const CollapsibleArtifact = ({ title, children }: { title: string; children: React.ReactNode }) => (
    <details className="mt-3 group">
      <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground flex items-center gap-1">
        <span className="group-open:rotate-90 transition-transform">▶</span>
        {title}
      </summary>
      <div className="mt-2">{children}</div>
    </details>
  );

  // 渲染 Artifact
  const renderArtifact = () => {
    if (!message.artifact) return null;

    switch (message.artifact.type) {
      case 'plotly':
        // 图表不折叠，直接显示
        if (message.artifact.chart_json) {
          return (
            <div className="mt-3">
              <PlotlyChart chartJson={message.artifact.chart_json} />
            </div>
          );
        }
        break;

      case 'table':
        if (message.artifact.columns && message.artifact.rows) {
          return (
            <CollapsibleArtifact title={`📊 数据表 (${message.artifact.rows.length} 行)`}>
              <DataTable
                columns={message.artifact.columns}
                rows={message.artifact.rows as unknown[][]}
                title={message.artifact.title}
              />
            </CollapsibleArtifact>
          );
        }
        break;

      case 'sql':
        return (
          <CollapsibleArtifact title={`🗃️ SQL 查询结果 (${message.artifact.rows?.length || 0} 行)`}>
            <div className="space-y-2">
              {message.artifact.sql && (
                <pre className="p-2 bg-muted rounded-md overflow-x-auto">
                  <code className="text-xs font-mono text-blue-600 dark:text-blue-400">{message.artifact.sql}</code>
                </pre>
              )}
              {message.artifact.columns && message.artifact.rows && (
                <DataTable
                  columns={message.artifact.columns}
                  rows={message.artifact.rows as unknown[][]}
                  title={
                    message.artifact.truncated
                      ? `结果 (前 ${message.artifact.rows.length} 行 / 共 ${message.artifact.total_rows} 行)`
                      : undefined
                  }
                />
              )}
            </div>
          </CollapsibleArtifact>
        );

      case 'code':
        return (
          <CollapsibleArtifact title="💻 代码执行结果">
            <div className="space-y-2">
              {message.artifact.code && (
                <pre className="p-2 bg-muted rounded-md overflow-x-auto">
                  <code className="text-xs font-mono">{message.artifact.code}</code>
                </pre>
              )}
              {message.artifact.output && (
                <pre className="p-2 bg-black/90 text-green-400 rounded-md overflow-x-auto text-xs font-mono whitespace-pre-wrap">
                  {message.artifact.output}
                </pre>
              )}
              {message.artifact.files_created && message.artifact.files_created.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  📁 生成文件: {message.artifact.files_created.join(', ')}
                </p>
              )}
            </div>
          </CollapsibleArtifact>
        );

      case 'error':
        return (
          <CollapsibleArtifact title={`❌ 错误${message.artifact.tool ? ` (${message.artifact.tool})` : ''}`}>
            <div className="p-3 bg-destructive/10 border border-destructive/20 rounded-md space-y-2">
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle className="w-4 h-4" />
                <span className="font-medium text-sm">{message.artifact.tool || '执行'}失败</span>
              </div>
              {/* 显示相关代码/SQL */}
              {(message.artifact.sql || message.artifact.code) && (
                <details className="group">
                  <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
                    查看代码
                  </summary>
                  <pre className="mt-1 p-2 bg-muted rounded text-xs font-mono overflow-x-auto max-h-[150px] overflow-y-auto">
                    {message.artifact.sql || message.artifact.code}
                  </pre>
                </details>
              )}
              {/* 显示标准输出 */}
              {message.artifact.output && (
                <details className="group">
                  <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground">
                    标准输出
                  </summary>
                  <pre className="mt-1 p-2 bg-black/90 text-green-400 rounded text-xs font-mono overflow-x-auto max-h-[100px] overflow-y-auto whitespace-pre-wrap">
                    {message.artifact.output}
                  </pre>
                </details>
              )}
              {/* 完整错误信息 */}
              <pre className="p-2 bg-destructive/5 text-destructive/90 rounded text-xs font-mono overflow-x-auto max-h-[300px] overflow-y-auto whitespace-pre-wrap">
                {message.artifact.error_message}
              </pre>
            </div>
          </CollapsibleArtifact>
        );

      case 'file':
        return (
          <CollapsibleArtifact title={`📎 ${message.artifact.filename}`}>
            <div className="p-2 bg-muted rounded-md">
              <a
                href={`/api/v1/sessions/${message.session_id}/files/${message.artifact.filename}`}
                className="text-xs text-primary hover:underline"
                target="_blank"
                rel="noreferrer"
              >
                点击下载: {message.artifact.filename}
              </a>
            </div>
          </CollapsibleArtifact>
        );
    }

    return null;
  };

  // 用户消息
  if (isUser) {
    return (
      <div className="flex justify-end gap-3">
        <div className="max-w-[80%] bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-4 py-3">
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {avatar}
      </div>
    );
  }

  // 工具消息 - 折叠显示
  if (isTool) {
    return (
      <div className="flex gap-3">
        {avatar}
        <div className="flex-1 min-w-0">
          <div className="text-xs text-muted-foreground mb-1">工具: {message.tool_name || message.tool_call_id}</div>
          {renderArtifact()}
          {!message.artifact && (
            <details className="group">
              <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">查看输出</summary>
              <pre className="mt-2 p-3 bg-muted rounded-lg text-xs overflow-x-auto">{message.content}</pre>
            </details>
          )}
        </div>
      </div>
    );
  }

  // AI 消息
  const hasContent = message.content?.trim();
  const hasToolCalls = message.tool_calls && message.tool_calls.length > 0;

  return (
    <div className="flex gap-3">
      {avatar}
      <div className="flex-1 min-w-0">
        {/* 文本内容 */}
        {hasContent && (
          <div
            className={cn(
              'prose prose-sm dark:prose-invert max-w-none',
              'prose-pre:bg-muted prose-pre:border prose-pre:rounded-lg',
              'prose-code:before:content-none prose-code:after:content-none',
              isStreaming && 'animate-pulse'
            )}
          >
            <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}
        {/* 工具调用提示（当没有文本但有工具调用时） */}
        {!hasContent && hasToolCalls && (
          <div className="text-sm text-muted-foreground italic">
            正在调用工具: {message.tool_calls?.map((tc) => tc.name).join(', ')}
          </div>
        )}
        {/* 流式占位符 */}
        {!hasContent && !hasToolCalls && isStreaming && <div className="text-muted-foreground animate-pulse">...</div>}
        {renderArtifact()}
      </div>
    </div>
  );
};
