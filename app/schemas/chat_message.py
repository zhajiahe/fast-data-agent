"""
对话消息相关的 Pydantic Schema

与 LangChain 消息格式对齐
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ChatMessageCreate(BaseModel):
    """创建对话消息请求（用户发送）"""

    content: str = Field(..., min_length=1, description="消息内容")


class ChatMessageResponse(BaseModel):
    """对话消息响应 - 与 LangChain 消息格式对齐"""

    id: int = Field(..., description="消息ID")
    session_id: int = Field(..., description="所属会话ID")

    # 消息基本信息
    message_type: str = Field(..., description="消息类型: human/ai/system/tool")
    content: str = Field(..., description="消息内容")
    message_id: str | None = Field(default=None, description="LangChain 消息ID")
    name: str | None = Field(default=None, description="消息名称")

    # AIMessage 特有字段
    tool_calls: list[dict[str, Any]] | None = Field(default=None, description="工具调用列表")
    usage_metadata: dict[str, Any] | None = Field(default=None, description="Token使用统计")

    # ToolMessage 特有字段
    tool_call_id: str | None = Field(default=None, description="工具调用ID")

    create_time: datetime | None = Field(default=None, description="创建时间")

    model_config = {"from_attributes": True}


class ChatStreamEvent(BaseModel):
    """聊天流式事件"""

    event: str = Field(..., description="事件类型")
    data: dict[str, Any] = Field(default_factory=dict, description="事件数据")
