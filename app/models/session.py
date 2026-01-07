"""
分析会话模型

用户创建的数据分析会话，可关联多个数据对象进行分析
"""

import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseTableMixin


class SessionRawData(Base, BaseTableMixin):
    """
    会话与数据对象的关联表

    一个会话可以关联多个 RawData，用于多源分析
    """

    __tablename__ = "session_raw_data"
    __table_args__ = (
        UniqueConstraint("session_id", "raw_data_id", name="uq_session_raw_data"),
    )

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="会话ID",
    )
    raw_data_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("raw_data.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="数据对象ID",
    )

    # 用户自定义的表别名（在 SQL 中使用）
    alias: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="表别名（可选，默认用 RawData.name）",
    )

    # 是否启用
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True, comment="是否启用")

    # 关系
    session: Mapped["AnalysisSession"] = relationship("AnalysisSession", back_populates="raw_data_links")
    raw_data: Mapped["RawData"] = relationship("RawData")  # type: ignore  # noqa: F821

    def __repr__(self) -> str:
        return f"<SessionRawData(session={self.session_id}, raw={self.raw_data_id})>"


class AnalysisSession(Base, BaseTableMixin):
    """
    分析会话表

    用户创建的分析会话，可关联多个数据对象进行分析
    """

    __tablename__ = "analysis_sessions"

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="会话名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="会话描述")

    # 所属用户
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True, comment="所属用户ID"
    )

    # 会话配置
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="会话配置(JSON)")

    # 会话状态
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", comment="会话状态: active/archived"
    )

    # 统计信息
    message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="消息数量")

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="analysis_sessions")  # type: ignore  # noqa: F821
    messages: Mapped[list["ChatMessage"]] = relationship(  # type: ignore  # noqa: F821
        "ChatMessage", back_populates="session", cascade="all, delete-orphan"
    )
    recommendations: Mapped[list["TaskRecommendation"]] = relationship(  # type: ignore  # noqa: F821
        "TaskRecommendation", back_populates="session", cascade="all, delete-orphan"
    )

    # 关联的数据对象（替代 data_source_id）
    raw_data_links: Mapped[list["SessionRawData"]] = relationship(
        "SessionRawData",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<AnalysisSession(id={self.id}, name={self.name}, user_id={self.user_id})>"
