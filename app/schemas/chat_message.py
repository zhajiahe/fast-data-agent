"""
对话消息相关的 Pydantic Schema
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.chat_message import MessageRole, MessageType


class ChatMessageBase(BaseModel):
    """对话消息基础字段"""

    role: MessageRole = Field(..., description="消息角色")
    message_type: MessageType = Field(default=MessageType.TEXT, description="消息类型")
    content: str = Field(..., description="消息内容")


class ChatMessageCreate(BaseModel):
    """创建对话消息请求（用户发送）"""

    content: str = Field(..., min_length=1, description="消息内容")


class ChatMessageResponse(ChatMessageBase):
    """对话消息响应"""

    id: int = Field(..., description="消息ID")
    session_id: int = Field(..., description="所属会话ID")

    # 额外数据
    extra_data: dict[str, Any] | None = Field(default=None, description="额外数据")

    # SQL 相关
    sql_query: str | None = Field(default=None, description="执行的SQL查询")
    sql_result: dict[str, Any] | None = Field(default=None, description="SQL执行结果")
    execution_time_ms: int | None = Field(default=None, description="执行时间(毫秒)")

    # 工具调用相关
    tool_call_id: str | None = Field(default=None, description="工具调用ID")
    tool_name: str | None = Field(default=None, description="工具名称")
    tool_args: dict[str, Any] | None = Field(default=None, description="工具调用参数")
    tool_result: dict[str, Any] | None = Field(default=None, description="工具调用结果")

    # Token 统计
    prompt_tokens: int | None = Field(default=None, description="Prompt Token数")
    completion_tokens: int | None = Field(default=None, description="Completion Token数")

    create_time: datetime | None = Field(default=None, description="创建时间")

    model_config = {"from_attributes": True}


class ChatStreamEvent(BaseModel):
    """聊天流式事件"""

    event: str = Field(..., description="事件类型: start/content/tool_call/tool_result/end/error")
    data: dict[str, Any] = Field(default_factory=dict, description="事件数据")


class TaskRecommendationResponse(BaseModel):
    """任务推荐响应"""

    id: int = Field(..., description="推荐ID")
    session_id: int = Field(..., description="所属会话ID")
    title: str = Field(..., description="推荐任务标题")
    description: str | None = Field(default=None, description="任务描述")
    category: str = Field(..., description="任务分类")
    status: str = Field(..., description="状态")
    create_time: datetime | None = Field(default=None, description="创建时间")

    model_config = {"from_attributes": True}
