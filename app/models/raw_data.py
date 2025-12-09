"""
原始数据模型

原始数据层：登记库表或文件的原始数据对象
"""

from enum import Enum

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseTableMixin


class RawDataType(str, Enum):
    """原始数据类型"""

    DATABASE_TABLE = "database_table"  # 数据库表
    FILE = "file"  # 文件


class RawData(Base, BaseTableMixin):
    """
    原始数据表

    存储用户登记的原始数据对象（库表或文件），
    用于后续构建数据源时的字段映射
    """

    __tablename__ = "raw_data"

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="原始数据名称，如 pg_orders_raw")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原始数据描述")
    raw_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="原始数据类型: database_table/file")

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="所属用户ID"
    )

    # 数据库表类型配置 (raw_type=database_table 时使用)
    connection_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("database_connections.id"), nullable=True, comment="数据库连接ID"
    )
    schema_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="Schema名称")
    table_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="表名")
    custom_sql: Mapped[str | None] = mapped_column(Text, nullable=True, comment="自定义SQL查询（可选）")

    # 文件类型配置 (raw_type=file 时使用)
    file_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("uploaded_files.id"), nullable=True, comment="关联的上传文件ID"
    )

    # 元数据
    columns_schema: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="列结构信息(JSON): [{name, data_type, nullable, user_type_override}]"
    )
    sample_data: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, comment="预览抽样数据(JSON): {columns, rows}"
    )
    row_count_estimate: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="估算行数")
    synced_at: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="最后同步时间")

    # 状态
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", comment="状态: pending/syncing/ready/error"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="raw_data_list")  # type: ignore  # noqa: F821
    connection: Mapped["DatabaseConnection | None"] = relationship(  # type: ignore  # noqa: F821
        "DatabaseConnection", back_populates="raw_data_list"
    )
    uploaded_file: Mapped["UploadedFile | None"] = relationship(  # type: ignore  # noqa: F821
        "UploadedFile", back_populates="raw_data"
    )
    # 多对多：RawData <-> DataSource 通过 DataSourceRawMapping 关联
    data_source_mappings: Mapped[list["DataSourceRawMapping"]] = relationship(  # type: ignore  # noqa: F821
        "DataSourceRawMapping", back_populates="raw_data", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RawData(id={self.id}, name={self.name}, type={self.raw_type})>"
