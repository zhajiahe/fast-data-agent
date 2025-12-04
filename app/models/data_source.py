"""
数据源模型

支持两种类型的数据源：
1. 数据库连接 (database) - MySQL, PostgreSQL, SQLite 等
2. 上传文件 (file) - CSV, Excel, JSON 等
"""

from enum import Enum

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseTableMixin


class DataSourceType(str, Enum):
    """数据源类型"""

    DATABASE = "database"  # 数据库连接
    FILE = "file"  # 上传文件


class DatabaseType(str, Enum):
    """数据库类型"""

    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"


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

    存储用户配置的数据库连接或上传文件的元信息
    """

    __tablename__ = "data_sources"

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="数据源名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="数据源描述")
    source_type: Mapped[str] = mapped_column(
        String(20), nullable=False, default=DataSourceType.DATABASE.value, comment="数据源类型: database/file"
    )

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="所属用户ID"
    )

    # 数据库连接配置 (source_type=database 时使用)
    db_type: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="数据库类型")
    host: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="数据库主机")
    port: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="数据库端口")
    database: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="数据库名")
    username: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="用户名")
    password: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="加密密码")
    extra_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="额外连接参数(JSON)")

    # 文件配置 (source_type=file 时使用，关联到 UploadedFile)
    file_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("uploaded_files.id"), nullable=True, comment="关联的上传文件ID"
    )

    # 元数据缓存（表结构、字段信息等）
    schema_cache: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="表结构缓存(JSON)")

    # 记忆（关于数据源的记忆）
    insights: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="数据源记忆(JSON)")

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="data_sources")  # type: ignore  # noqa: F821
    uploaded_file: Mapped["UploadedFile | None"] = relationship(  # type: ignore  # noqa: F821
        "UploadedFile", back_populates="data_source"
    )

    def __repr__(self) -> str:
        return f"<DataSource(id={self.id}, name={self.name}, type={self.source_type})>"
