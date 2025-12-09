"""
数据源模型

数据源层：基于多个原始数据(RawData)构建的统一数据入口，
支持字段映射和聚合，为 AI 分析提供清晰的逻辑视图。
"""

from enum import Enum

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseTableMixin


class DataSourceCategory(str, Enum):
    """数据源分类"""

    FACT = "fact"  # 事实类
    DIMENSION = "dimension"  # 维度类
    EVENT = "event"  # 事件类
    OTHER = "other"  # 其他


class FileType(str, Enum):
    """文件类型"""

    CSV = "csv"
    EXCEL = "excel"
    JSON = "json"
    PARQUET = "parquet"
    SQLITE = "sqlite"  # SQLite 数据库文件


class DataSource(Base, BaseTableMixin):
    """
    数据源配置表

    基于多个 RawData 构建，支持字段映射和聚合
    """

    __tablename__ = "data_sources"

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="数据源名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="数据源描述")
    category: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="数据源分类: fact/dimension/event/other"
    )

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="所属用户ID"
    )

    # 目标字段定义（统一后的逻辑字段）
    # 格式: [{name: string, data_type: string, description?: string}]
    target_fields: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="目标字段定义(JSON): [{name, data_type, description}]"
    )

    # 元数据缓存（合并后的表结构、统计信息等）
    schema_cache: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="表结构缓存(JSON)")

    # 记忆（关于数据源的记忆，供 AI 使用）
    insights: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="数据源记忆(JSON)")

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="data_sources")  # type: ignore  # noqa: F821

    # 关联多个 RawData（通过中间表）
    raw_mappings: Mapped[list["DataSourceRawMapping"]] = relationship(
        "DataSourceRawMapping", back_populates="data_source", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<DataSource(id={self.id}, name={self.name})>"


class DataSourceRawMapping(Base, BaseTableMixin):
    """
    数据源与原始数据的映射表

    存储每个 RawData 到 DataSource 目标字段的映射关系
    """

    __tablename__ = "data_source_raw_mappings"

    # 关联
    data_source_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("data_sources.id"), nullable=False, index=True, comment="数据源ID"
    )
    raw_data_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("raw_data.id"), nullable=False, index=True, comment="原始数据ID"
    )

    # 字段映射配置
    # 格式: {"target_field": "source_field_or_expression", ...}
    # 例如: {"order_id": "id", "customer_id": "customer_id", "discount": null}
    field_mappings: Mapped[dict] = mapped_column(
        JSONB, nullable=False, default=dict, comment="字段映射(JSON): {target_field: source_field/expression}"
    )

    # 映射顺序（用于合并时的优先级）
    priority: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="映射优先级（数值越大优先级越高）"
    )

    # 是否启用
    is_enabled: Mapped[bool] = mapped_column(default=True, comment="是否启用该映射")

    # 关系
    data_source: Mapped["DataSource"] = relationship("DataSource", back_populates="raw_mappings")
    raw_data: Mapped["RawData"] = relationship("RawData", back_populates="data_source_mappings")  # type: ignore  # noqa: F821

    def __repr__(self) -> str:
        return f"<DataSourceRawMapping(ds_id={self.data_source_id}, raw_id={self.raw_data_id})>"
