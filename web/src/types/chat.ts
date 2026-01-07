/**
 * Chat 相关类型定义
 */

/**
 * SSE 事件类型枚举
 */
export type SSEEventType =
  | 'start'
  | 'text-start'
  | 'text-delta'
  | 'text-end'
  | 'tool-input-start'
  | 'tool-input-available'
  | 'tool-output-available'
  | 'start-step'
  | 'finish-step'
  | 'finish'
  | 'error';

/**
 * 工具产出物类型
 */
export interface ToolArtifact {
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

/**
 * SSE 事件数据
 */
export interface SSEEvent {
  type: SSEEventType;
  messageId?: string;
  id?: string;
  delta?: string;
  toolCallId?: string;
  toolName?: string;
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  artifact?: ToolArtifact;
  errorText?: string;
}

/**
 * 工具调用结构
 */
export interface ToolCall {
  id: string;
  name: string;
  args: Record<string, unknown>;
}

/**
 * 本地消息类型（用于 UI 状态管理）
 * id 支持 string（UUID）或临时 ID（前缀 temp- 或 streaming）
 */
export interface LocalMessage {
  id: string;
  session_id: string;
  seq?: number; // 消息序号（会话内递增，用于排序）
  message_type: 'human' | 'ai' | 'tool' | 'system';
  content: string;
  tool_call_id?: string;
  tool_name?: string;
  tool_calls?: ToolCall[]; // AIMessage 的工具调用
  artifact?: ToolArtifact;
  create_time: string;
}

/**
 * 工具调用状态
 */
export interface ToolCallState {
  id: string;
  name: string;
  status: 'calling' | 'executing' | 'completed' | 'error';
}

/**
 * 聊天流状态
 */
export interface ChatStreamState {
  isGenerating: boolean;
  streamingText: string;
  currentToolCall: ToolCallState | null;
}
