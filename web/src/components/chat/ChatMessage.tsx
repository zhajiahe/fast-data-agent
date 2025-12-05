import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import { User, Bot, Wrench, AlertCircle } from 'lucide-react';
import { cn } from '@/lib/utils';
import { PlotlyChart } from './PlotlyChart';
import { DataTable } from './DataTable';

// 本地消息类型
interface LocalMessage {
  id: number;
  session_id: number;
  message_type: string;
  content: string;
  tool_call_id?: string;
  tool_name?: string;
  artifact?: {
    type: string;
    chart_json?: string;
    columns?: string[];
    rows?: unknown[][];
    title?: string;
    error_message?: string;
    filename?: string;
  };
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

  // 渲染 Artifact
  const renderArtifact = () => {
    if (!message.artifact) return null;

    switch (message.artifact.type) {
      case 'plotly':
        if (message.artifact.chart_json) {
          return (
            <div className="mt-4">
              <PlotlyChart chartJson={message.artifact.chart_json} />
            </div>
          );
        }
        break;

      case 'table':
        if (message.artifact.columns && message.artifact.rows) {
          return (
            <div className="mt-4">
              <DataTable
                columns={message.artifact.columns}
                rows={message.artifact.rows as unknown[][]}
                title={message.artifact.title}
              />
            </div>
          );
        }
        break;

      case 'error':
        return (
          <div className="mt-4 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="w-4 h-4" />
              <span className="font-medium">错误</span>
            </div>
            <p className="mt-2 text-sm text-destructive/80">{message.artifact.error_message}</p>
          </div>
        );

      case 'file':
        return (
          <div className="mt-4 p-3 bg-muted rounded-lg">
            <a
              href={`/api/v1/sessions/${message.session_id}/files/${message.artifact.filename}`}
              className="text-sm text-primary hover:underline"
              target="_blank"
              rel="noreferrer"
            >
              📎 {message.artifact.filename}
            </a>
          </div>
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
          <div className="text-xs text-muted-foreground mb-1">
            工具: {message.tool_name || message.tool_call_id}
          </div>
          {renderArtifact()}
          {!message.artifact && (
            <details className="group">
              <summary className="cursor-pointer text-sm text-muted-foreground hover:text-foreground">
                查看输出
              </summary>
              <pre className="mt-2 p-3 bg-muted rounded-lg text-xs overflow-x-auto">
                {message.content}
              </pre>
            </details>
          )}
        </div>
      </div>
    );
  }

  // AI 消息
  return (
    <div className="flex gap-3">
      {avatar}
      <div className="flex-1 min-w-0">
        <div
          className={cn(
            'prose prose-sm dark:prose-invert max-w-none',
            'prose-pre:bg-muted prose-pre:border prose-pre:rounded-lg',
            'prose-code:before:content-none prose-code:after:content-none',
            isStreaming && 'animate-pulse'
          )}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            rehypePlugins={[rehypeHighlight]}
          >
            {message.content || '...'}
          </ReactMarkdown>
        </div>
        {renderArtifact()}
      </div>
    </div>
  );
};
