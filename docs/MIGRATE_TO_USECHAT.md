# 迁移到 Vercel AI SDK `useChat` 计划

## 概述

本文档描述将前端聊天功能从自定义 `useChatStream` hook 迁移到 Vercel AI SDK 的 `@ai-sdk/react` 的 `useChat` hook 的计划。

## 当前架构

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend (React)                                            │
├─────────────────────────────────────────────────────────────┤
│ Chat.tsx                                                    │
│   ├── useChatStream (自定义 hook)                           │
│   │   ├── 管理 SSE 连接                                     │
│   │   ├── 解析 Data Stream Protocol                         │
│   │   └── 返回 streamingText, isGenerating, currentToolCall │
│   ├── useMessages (React Query)                             │
│   │   └── 从 API 获取历史消息                               │
│   └── localMessages (本地状态)                              │
│       └── 同步 API 消息 + 流式消息                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ SSE (Data Stream Protocol)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend (FastAPI)                                           │
├─────────────────────────────────────────────────────────────┤
│ POST /api/v1/sessions/{session_id}/chat                     │
│   ├── 接收 { content: string }                              │
│   ├── 调用 LangGraph Agent                                  │
│   ├── 流式返回 SSE 事件:                                    │
│   │   ├── start, text-start, text-delta, text-end           │
│   │   ├── tool-input-start/available, tool-output-available │
│   │   ├── finish-step, finish, [DONE]                       │
│   └── 保存消息到数据库                                      │
├─────────────────────────────────────────────────────────────┤
│ GET /api/v1/sessions/{session_id}/messages                  │
│   └── 返回 ChatMessageResponse[] (自定义格式)               │
└─────────────────────────────────────────────────────────────┘
```

## 目标架构

```
┌─────────────────────────────────────────────────────────────┐
│ Frontend (React)                                            │
├─────────────────────────────────────────────────────────────┤
│ Chat.tsx                                                    │
│   └── useChat (@ai-sdk/react)                               │
│       ├── 内置 SSE 处理                                     │
│       ├── 内置消息状态管理                                  │
│       ├── 内置工具调用处理                                  │
│       ├── initialMessages 加载历史消息                      │
│       └── onFinish 处理后续操作                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ SSE (Data Stream Protocol - UIMessage 格式)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│ Backend (FastAPI)                                           │
├─────────────────────────────────────────────────────────────┤
│ POST /api/v1/sessions/{session_id}/chat                     │
│   ├── 接收 { messages: UIMessage[] }                        │
│   ├── 转换消息格式                                          │
│   ├── 调用 LangGraph Agent                                  │
│   ├── 流式返回 UIMessage 格式的 SSE 事件                    │
│   └── 保存消息到数据库                                      │
├─────────────────────────────────────────────────────────────┤
│ GET /api/v1/sessions/{session_id}/messages                  │
│   └── 返回 UIMessage[] 格式                                 │
└─────────────────────────────────────────────────────────────┘
```

## 迁移步骤

### Phase 1: 准备工作

#### 1.1 安装依赖
```bash
cd web
pnpm add @ai-sdk/react ai
```

#### 1.2 理解 UIMessage 格式
```typescript
// Vercel AI SDK UIMessage 格式
interface UIMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  parts: UIMessagePart[];
  createdAt?: Date;
  metadata?: Record<string, unknown>;
}

type UIMessagePart = 
  | { type: 'text'; text: string }
  | { type: 'tool-invocation'; toolInvocationId: string; toolName: string; args: unknown; state: string; result?: unknown }
  | { type: 'source-url'; url: string }
  | { type: 'file'; name: string; contentType: string; url: string }
  | { type: 'reasoning'; text: string }
  | { type: 'data-*'; [key: string]: unknown }; // 自定义数据类型
```

### Phase 2: 后端修改

#### 2.1 创建 UIMessage 转换器
```python
# app/utils/ui_message.py

from typing import Any
from app.models.message import ChatMessage

def chat_message_to_ui_message(msg: ChatMessage) -> dict[str, Any]:
    """将 ChatMessage 转换为 UIMessage 格式"""
    parts = []
    
    # 文本内容
    if msg.content:
        parts.append({"type": "text", "text": msg.content})
    
    # 工具调用
    if msg.message_type == "tool" and msg.tool_call_id:
        parts.append({
            "type": "tool-invocation",
            "toolInvocationId": msg.tool_call_id,
            "toolName": msg.name or "unknown",
            "args": {},
            "state": "result",
            "result": msg.content,
        })
        # 如果有 artifact（如图表），添加为自定义数据类型
        if msg.artifact:
            parts.append({
                "type": "data-artifact",
                **msg.artifact,
            })
    
    role_map = {
        "human": "user",
        "ai": "assistant",
        "tool": "tool",
        "system": "system",
    }
    
    return {
        "id": str(msg.id),
        "role": role_map.get(msg.message_type, "assistant"),
        "parts": parts,
        "createdAt": msg.create_time.isoformat() if msg.create_time else None,
    }
```

#### 2.2 修改消息 API 返回格式
```python
# app/api/chat.py

@router.get("/messages", response_model=BaseResponse[list[dict]])
async def get_messages_ui_format(
    session_id: int,
    current_user: CurrentUser,
    db: DBSession,
):
    """获取会话的历史消息（UIMessage 格式）"""
    # ... 验证会话权限
    messages, _ = await chat_service.get_history(session_id)
    ui_messages = [chat_message_to_ui_message(msg) for msg in messages]
    return BaseResponse(success=True, code=200, msg="成功", data=ui_messages)
```

#### 2.3 修改 SSE 流输出格式
```python
# app/api/chat.py

# 修改 VercelStreamBuilder 以输出标准 UIMessage 格式
# 主要变化：
# - text-delta 保持不变
# - tool-output-available 需要包含完整的 tool-invocation part
# - 自定义数据（artifact）使用 data-* 格式
```

### Phase 3: 前端修改

#### 3.1 创建新的 Chat 组件
```typescript
// web/src/pages/ChatV2.tsx

'use client';

import { useChat } from '@ai-sdk/react';
import { DefaultChatTransport } from 'ai';
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { storage } from '@/utils/storage';

export const ChatV2 = () => {
  const { id } = useParams<{ id: string }>();
  const sessionId = Number(id);

  // 获取初始消息
  const { data: initialMessages } = useQuery({
    queryKey: ['messages-ui', sessionId],
    queryFn: () => getMessagesUIFormat(sessionId),
  });

  const {
    messages,
    input,
    setInput,
    status,
    sendMessage,
    stop,
    reload,
  } = useChat({
    id: `session-${sessionId}`,
    initialMessages: initialMessages || [],
    
    transport: new DefaultChatTransport({
      api: `/api/v1/sessions/${sessionId}/chat`,
      headers: () => ({
        Authorization: `Bearer ${storage.getToken()}`,
      }),
    }),

    onFinish: ({ message }) => {
      // 流结束后的操作
      // 1. 生成追问推荐（后台执行）
      generateFollowupRecommendations(sessionId, {
        conversation_context: message.parts
          .filter(p => p.type === 'text')
          .map(p => p.text)
          .join('\n'),
      }).catch(console.warn);
      
      // 2. 刷新推荐列表
      queryClient.invalidateQueries({ queryKey: ['recommendations', sessionId] });
    },

    onError: (error) => {
      toast({
        title: '错误',
        description: error.message,
        variant: 'destructive',
      });
    },
  });

  // 渲染消息
  return (
    <div>
      {messages.map(message => (
        <div key={message.id}>
          {message.parts.map((part, i) => {
            switch (part.type) {
              case 'text':
                return <MarkdownRenderer key={i} content={part.text} />;
              case 'tool-invocation':
                return <ToolInvocationDisplay key={i} part={part} />;
              case 'data-artifact':
                return <ArtifactDisplay key={i} artifact={part} />;
              default:
                return null;
            }
          })}
        </div>
      ))}
      
      {/* 输入区域 */}
      <form onSubmit={e => { e.preventDefault(); sendMessage({ text: input }); setInput(''); }}>
        <input value={input} onChange={e => setInput(e.target.value)} />
        <button type="submit" disabled={status === 'in-progress'}>
          {status === 'in-progress' ? '生成中...' : '发送'}
        </button>
        {status === 'in-progress' && <button onClick={stop}>停止</button>}
      </form>
    </div>
  );
};
```

#### 3.2 创建新的消息渲染组件
```typescript
// web/src/components/chat/UIMessageRenderer.tsx

interface ToolInvocationDisplayProps {
  part: {
    type: 'tool-invocation';
    toolInvocationId: string;
    toolName: string;
    args: unknown;
    state: string;
    result?: unknown;
  };
}

export const ToolInvocationDisplay = ({ part }: ToolInvocationDisplayProps) => {
  if (part.state === 'call') {
    return <div className="tool-calling">调用 {part.toolName}...</div>;
  }
  
  if (part.state === 'result') {
    return (
      <div className="tool-result">
        <div className="tool-name">{part.toolName}</div>
        <pre>{JSON.stringify(part.result, null, 2)}</pre>
      </div>
    );
  }
  
  return null;
};

interface ArtifactDisplayProps {
  artifact: {
    type: string;
    chart_type?: string;
    plotly_json?: object;
    // ... 其他 artifact 属性
  };
}

export const ArtifactDisplay = ({ artifact }: ArtifactDisplayProps) => {
  if (artifact.chart_type) {
    return <PlotlyChart data={artifact.plotly_json} />;
  }
  // ... 其他 artifact 类型处理
  return null;
};
```

### Phase 4: 测试和迁移

#### 4.1 并行运行两个版本
```typescript
// 临时路由配置
<Route path="/sessions/:id/chat" element={<Chat />} />        {/* 旧版 */}
<Route path="/sessions/:id/chat-v2" element={<ChatV2 />} />   {/* 新版 */}
```

#### 4.2 功能测试清单
- [ ] 基本对话（发送消息、接收回复）
- [ ] 流式文本显示
- [ ] 工具调用显示（execute_sql, execute_python, generate_chart）
- [ ] 图表渲染
- [ ] 历史消息加载
- [ ] 停止生成
- [ ] 错误处理
- [ ] 推荐问题生成
- [ ] 多会话切换

#### 4.3 性能测试
- [ ] 首次加载时间
- [ ] 流式响应延迟
- [ ] 大量消息性能

### Phase 5: 清理

#### 5.1 删除旧代码
```bash
# 删除自定义 hook
rm web/src/hooks/useChatStream.ts

# 更新 Chat.tsx
mv web/src/pages/ChatV2.tsx web/src/pages/Chat.tsx

# 删除旧的消息类型定义
# 更新 LocalMessage 类型为 UIMessage
```

#### 5.2 更新文档
- 更新 README.md
- 更新 AGENTS.md
- 更新 API 文档

## 风险和注意事项

### 高风险
1. **消息格式不兼容**：需要迁移所有现有消息数据
2. **工具调用处理**：`useChat` 的工具调用处理方式与当前不同
3. **Artifact 显示**：需要适配自定义数据类型

### 中风险
1. **历史消息分页**：`useChat` 默认加载全部消息，大量消息时可能有性能问题
2. **消息持久化时机**：需要确保消息在流结束前保存

### 低风险
1. **依赖更新**：需要跟踪 `@ai-sdk/react` 的更新
2. **API 版本兼容**：Vercel AI SDK 可能有 breaking changes

## 时间估计

| 阶段 | 预计时间 |
|------|----------|
| Phase 1: 准备工作 | 0.5 天 |
| Phase 2: 后端修改 | 1-2 天 |
| Phase 3: 前端修改 | 2-3 天 |
| Phase 4: 测试和迁移 | 1-2 天 |
| Phase 5: 清理 | 0.5 天 |
| **总计** | **5-8 天** |

## 回滚计划

如果迁移过程中遇到严重问题：
1. 保留旧的 `useChatStream` 代码在 `_deprecated` 分支
2. 后端保持双格式支持（通过 Accept header 或查询参数区分）
3. 前端可以快速切换回旧版本

## 决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2024-XX-XX | 计划迁移到 useChat | 减少维护成本，使用官方维护的解决方案 |

---

*文档版本: 1.0*
*最后更新: 2024-XX-XX*

