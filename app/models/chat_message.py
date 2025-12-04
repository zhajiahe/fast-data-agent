"""
对话消息模型

存储用户与AI的对话历史，与 LangChain 消息格式对齐
"""

from enum import Enum

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseTableMixin


class MessageType(str, Enum):
    """消息类型 - 对应 LangChain 消息类型"""

    HUMAN = "human"  # 用户消息 (HumanMessage)
    AI = "ai"  # AI助手消息 (AIMessage)
    SYSTEM = "system"  # 系统消息 (SystemMessage)
    TOOL = "tool"  # 工具消息 (ToolMessage)


class ChatMessage(Base, BaseTableMixin):
    """
    对话消息表

    存储分析会话中的对话历史，与 LangChain 消息格式对齐
    """

    __tablename__ = "chat_messages"

    # 所属会话
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属会话ID",
    )

    # 消息基本信息 (对应 LangChain BaseMessage)
    message_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="消息类型: human/ai/system/tool")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")
    message_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="LangChain 消息ID")
    name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="消息名称(可选)")

    # AIMessage 特有字段
    tool_calls: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="工具调用列表(JSON)")
    invalid_tool_calls: Mapped[list | None] = mapped_column(JSONB, nullable=True, comment="无效工具调用列表(JSON)")
    usage_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="Token使用统计(JSON)")

    # ToolMessage 特有字段
    tool_call_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="工具调用ID")
    artifact: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="工具产出物(JSON)")
    status: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="工具执行状态: success/error")

    # 额外元数据
    additional_kwargs: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="额外参数(JSON)")
    response_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="响应元数据(JSON)")

    # 关系
    session: Mapped["AnalysisSession"] = relationship(  # type: ignore  # noqa: F821
        "AnalysisSession", back_populates="messages"
    )

    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ChatMessage(id={self.id}, type={self.message_type}, content={content_preview})>"
