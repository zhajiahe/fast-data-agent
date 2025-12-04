"""
任务推荐模型

存储系统为用户生成的分析任务推荐
"""

from enum import Enum

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseTableMixin


class RecommendationCategory(str, Enum):
    """推荐任务分类"""

    OVERVIEW = "overview"  # 数据概览
    TREND = "trend"  # 趋势分析
    COMPARISON = "comparison"  # 对比分析
    ANOMALY = "anomaly"  # 异常检测
    CORRELATION = "correlation"  # 关联分析
    DISTRIBUTION = "distribution"  # 分布分析
    OTHER = "other"  # 其他


class RecommendationStatus(str, Enum):
    """推荐状态"""

    PENDING = "pending"  # 待选择
    SELECTED = "selected"  # 已选择执行
    DISMISSED = "dismissed"  # 已忽略


class RecommendationSourceType(str, Enum):
    """推荐来源类型"""

    INITIAL = "initial"  # 初始推荐（创建会话时）
    FOLLOW_UP = "follow_up"  # 追问推荐（对话过程中）


class TaskRecommendation(Base, BaseTableMixin):
    """
    任务推荐表

    存储系统为用户生成的分析任务推荐
    """

    __tablename__ = "task_recommendations"

    # 所属会话
    session_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属会话ID",
    )

    # 推荐内容
    title: Mapped[str] = mapped_column(String(200), nullable=False, comment="推荐任务标题")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="任务描述")
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, default=RecommendationCategory.OVERVIEW.value, comment="任务分类"
    )

    # 推荐来源和优先级
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RecommendationSourceType.INITIAL.value, comment="推荐来源类型"
    )
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="优先级（0最高）")

    # 状态
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RecommendationStatus.PENDING.value, comment="状态"
    )

    # 触发该推荐的消息（用于追问推荐）
    trigger_message_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("chat_messages.id"), nullable=True, comment="触发推荐的消息ID"
    )

    # 关系
    session: Mapped["AnalysisSession"] = relationship("AnalysisSession", back_populates="recommendations")  # type: ignore  # noqa: F821
    trigger_message: Mapped["ChatMessage | None"] = relationship("ChatMessage")  # type: ignore  # noqa: F821

    def __repr__(self) -> str:
        return f"<TaskRecommendation(id={self.id}, title={self.title[:30]}...)>"
