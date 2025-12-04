"""
分析会话模型

用户创建的数据分析会话，可以关联多个数据源
"""

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseTableMixin


class AnalysisSession(Base, BaseTableMixin):
    """
    分析会话表

    用户创建的分析会话，可选择多个数据源进行分析
    """

    __tablename__ = "analysis_sessions"

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="会话名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="会话描述")

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="所属用户ID"
    )

    # 关联的数据源ID列表
    data_source_ids: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer), nullable=True, comment="关联的数据源ID列表"
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

    def __repr__(self) -> str:
        return f"<AnalysisSession(id={self.id}, name={self.name}, user_id={self.user_id})>"
