"""
对话消息模型

存储用户与AI的对话历史
"""

from enum import Enum

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseTableMixin


class MessageRole(str, Enum):
    """消息角色"""

    USER = "user"  # 用户消息
    ASSISTANT = "assistant"  # AI助手消息
    SYSTEM = "system"  # 系统消息
    TOOL = "tool"  # 工具消息（工具调用结果）


class MessageType(str, Enum):
    """消息类型"""

    TEXT = "text"  # 纯文本
    SQL = "sql"  # SQL查询
    CODE = "code"  # 代码
    CHART = "chart"  # 图表
    TABLE = "table"  # 数据表格
    ERROR = "error"  # 错误信息
    TOOL_CALL = "tool_call"  # 工具调用请求
    TOOL_RESULT = "tool_result"  # 工具调用结果


class ChatMessage(Base, BaseTableMixin):
    """
    对话消息表

    存储分析会话中的对话历史
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

    # 消息基本信息
    role: Mapped[str] = mapped_column(String(20), nullable=False, comment="消息角色: user/assistant/system")
    message_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=MessageType.TEXT.value, comment="消息类型"
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="消息内容")

    # 额外数据（SQL执行结果、图表配置等）
    extra_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="消息额外数据(JSON)")

    # SQL相关（如果是SQL查询）
    sql_query: Mapped[str | None] = mapped_column(Text, nullable=True, comment="执行的SQL查询")
    sql_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="SQL执行结果(JSON)")
    execution_time_ms: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="执行时间(毫秒)")

    # 工具调用相关（如果是工具消息）
    tool_call_id: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="工具调用ID")
    tool_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="工具名称")
    tool_args: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="工具调用参数(JSON)")
    tool_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="工具调用结果(JSON)")

    # Token使用统计
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Prompt Token数")
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="Completion Token数")

    # 父消息（用于追踪对话关系）
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_messages.id"), nullable=True, comment="父消息ID"
    )

    # 关系
    session: Mapped["AnalysisSession"] = relationship("AnalysisSession", back_populates="messages")  # type: ignore  # noqa: F821
    parent: Mapped["ChatMessage | None"] = relationship(
        "ChatMessage", remote_side="ChatMessage.id", back_populates="replies"
    )
    replies: Mapped[list["ChatMessage"]] = relationship("ChatMessage", back_populates="parent")

    def __repr__(self) -> str:
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<ChatMessage(id={self.id}, role={self.role}, content={content_preview})>"
