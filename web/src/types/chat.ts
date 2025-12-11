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
  chart_json?: string;
  columns?: string[];
  rows?: unknown[][];
  title?: string;
  error_message?: string;
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
 * id 支持 number（后端消息）或 string（临时工具消息，使用 tool_call_id）
 */
export interface LocalMessage {
  id: number | string;
  session_id: number;
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
