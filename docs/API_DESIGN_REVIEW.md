# API 设计评估报告

## 概述

本文档评估 Fast Data Agent 后端 API 设计是否满足前端构建需求。

## 当前 API 结构

```
/api/v1/
├── auth/                    # 认证
│   ├── POST /register      # 用户注册
│   ├── POST /login         # 用户登录
│   ├── GET /me             # 当前用户信息
│   └── POST /refresh       # 刷新令牌
│
├── users/                   # 用户管理（管理员）
│   ├── GET /               # 用户列表
│   ├── POST /              # 创建用户
│   ├── GET /{id}           # 用户详情
│   ├── PUT /{id}           # 更新用户
│   └── DELETE /{id}        # 删除用户
│
├── files/                   # 文件管理
│   ├── POST /upload        # 上传文件
│   ├── GET /               # 文件列表
│   ├── GET /{id}           # 文件详情
│   └── DELETE /{id}        # 删除文件
│
├── data-sources/            # 数据源管理
│   ├── GET /               # 数据源列表
│   ├── POST /              # 创建数据源
│   ├── GET /{id}           # 数据源详情
│   ├── PUT /{id}           # 更新数据源
│   └── DELETE /{id}        # 删除数据源
│
├── sessions/                # 分析会话
│   ├── GET /               # 会话列表
│   ├── POST /              # 创建会话
│   ├── GET /{id}           # 会话详情（含数据源）
│   ├── PUT /{id}           # 更新会话
│   ├── DELETE /{id}        # 删除会话
│   └── POST /{id}/archive  # 归档会话
│
└── sessions/{id}/           # 会话内操作
    ├── POST /chat          # 发送消息（SSE 流式）
    ├── GET /messages       # 历史消息（分页）
    └── recommendations/    # 任务推荐
        ├── GET /           # 推荐列表
        ├── POST /generate  # 生成推荐
        └── PUT /{id}       # 更新状态
```

## ✅ 设计合理的部分

### 1. 统一响应格式

```typescript
interface BaseResponse<T> {
  success: boolean;
  code: number;
  msg: string;
  data: T | null;
}
```

**优点**：前端可以统一处理错误和成功响应

### 2. 分页支持

```typescript
interface PageResponse<T> {
  page_num: number;
  page_size: number;
  total: number;
  items: T[];
}
```

**优点**：分页信息完整，支持无限滚动和传统分页

### 3. SSE 流式传输

聊天接口使用 Server-Sent Events 实现流式响应：

```typescript
// SSE 事件格式
data: {"mode": "messages", "content": "...", "type": "ai"}
data: {"mode": "updates", "node": "tools", "messages": [...]}
data: [DONE]
```

**优点**：
- 实时显示 AI 回复
- 支持工具调用过程展示
- 支持 artifact（图表数据）传递

### 4. LangChain 消息格式对齐

```typescript
interface ChatMessage {
  message_type: 'human' | 'ai' | 'tool' | 'system';
  content: string;
  tool_calls?: ToolCall[];      // AI 调用的工具
  tool_call_id?: string;        // 工具执行结果关联
  artifact?: object;            // 附加数据（如图表）
}
```

**优点**：消息类型清晰，工具调用链完整

### 5. RESTful 规范

- 资源命名规范（复数形式）
- HTTP 方法语义正确
- 状态码使用恰当

## ⚠️ 前端构建可能遇到的问题

### 1. 图表渲染

**问题**：
- `artifact.chart_json` 包含 Plotly JSON 数据
- 前端需要识别 tool 消息中的图表类型并渲染

**前端处理示例**：
```typescript
if (message.artifact?.type === 'plotly') {
  const chartData = JSON.parse(message.artifact.chart_json);
  Plotly.newPlot('chart-container', chartData.data, chartData.layout);
}
```

### 2. 会话文件访问缺失

**问题**：
- 生成的图表文件（chart_xxx.html）和结果文件（sql_result_xxx.parquet）无法下载
- 沙盒服务有文件接口，但主服务未暴露

**建议新增**：
```
GET /sessions/{id}/files              # 列出会话文件
GET /sessions/{id}/files/{filename}   # 下载会话文件
```

### 3. 交互功能缺失

**问题**：缺少常见的聊天交互功能

**建议新增**：
```
POST /sessions/{id}/abort            # 中断当前生成
POST /sessions/{id}/messages/{id}/regenerate  # 重新生成
POST /sessions/{id}/messages/{id}/feedback    # 消息反馈（👍/👎）
```

### 4. SSE 事件类型不明确

**问题**：当前只使用 `data:` 前缀，前端需要解析 JSON 判断类型

**建议改进**：
```
event: token
data: {"content": "..."}

event: tool_call
data: {"name": "execute_sql", "args": {...}}

event: tool_result
data: {"name": "execute_sql", "result": {...}, "artifact": {...}}

event: done
data: {}
```

## 建议新增接口

### 1. 会话文件管理

```python
# GET /sessions/{session_id}/files
# 列出会话中生成的文件
@router.get("/{session_id}/files")
async def list_session_files(session_id: int, ...):
    # 调用沙盒服务获取文件列表
    pass

# GET /sessions/{session_id}/files/{filename}
# 下载会话文件
@router.get("/{session_id}/files/{filename}")
async def download_session_file(session_id: int, filename: str, ...):
    # 代理沙盒服务的文件下载
    pass
```

### 2. 生成控制

```python
# POST /sessions/{session_id}/abort
# 中断当前生成（需要实现取消机制）
@router.post("/{session_id}/abort")
async def abort_generation(session_id: int, ...):
    pass
```

### 3. 消息操作

```python
# POST /sessions/{session_id}/messages/{message_id}/regenerate
# 重新生成某条消息
@router.post("/{session_id}/messages/{message_id}/regenerate")
async def regenerate_message(session_id: int, message_id: int, ...):
    pass

# POST /sessions/{session_id}/messages/{message_id}/feedback
# 消息反馈
@router.post("/{session_id}/messages/{message_id}/feedback")
async def message_feedback(session_id: int, message_id: int, feedback: FeedbackType, ...):
    pass
```

## 前端技术建议

### 推荐技术栈
- **框架**: React/Vue 3 + TypeScript
- **状态管理**: Zustand/Pinia
- **SSE 处理**: EventSource API 或 fetch + ReadableStream
- **图表**: Plotly.js（与后端一致）
- **UI 组件**: Ant Design/shadcn/ui

### SSE 处理示例

```typescript
async function streamChat(sessionId: number, content: string) {
  const response = await fetch(`/api/v1/sessions/${sessionId}/chat`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ content })
  });

  const reader = response.body.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = decoder.decode(value);
    const lines = text.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data === '[DONE]') return;
        
        const event = JSON.parse(data);
        handleEvent(event);
      }
    }
  }
}

function handleEvent(event: SSEEvent) {
  if (event.mode === 'messages') {
    // 处理 AI 回复 token
    appendToken(event.content);
  } else if (event.mode === 'updates') {
    // 处理工具调用
    handleToolUpdate(event);
  }
}
```

## 总结

当前 API 设计总体合理，满足基本的前端构建需求。主要需要补充：

1. **会话文件访问接口** - 下载图表和结果文件
2. **交互控制接口** - 中断、重新生成、反馈
3. **SSE 事件标准化** - 可选优化

优先级建议：
1. ⭐⭐⭐ 会话文件下载接口
2. ⭐⭐ 消息反馈接口
3. ⭐ 中断/重新生成接口

