"""
数据库连接配置模型

独立管理数据库连接，供 RawData 引用
"""

from enum import Enum

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseTableMixin


class DatabaseType(str, Enum):
    """数据库类型"""

    MYSQL = "mysql"
    POSTGRESQL = "postgresql"
    SQLITE = "sqlite"


class DatabaseConnection(Base, BaseTableMixin):
    """
    数据库连接配置表

    独立存储数据库连接信息，可被多个 RawData 复用
    """

    __tablename__ = "database_connections"

    # 基本信息
    name: Mapped[str] = mapped_column(String(100), nullable=False, comment="连接名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="连接描述")

    # 所属用户
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False, index=True, comment="所属用户ID"
    )

    # 连接配置
    db_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="数据库类型: mysql/postgresql/sqlite")
    host: Mapped[str] = mapped_column(String(255), nullable=False, comment="数据库主机")
    port: Mapped[int] = mapped_column(Integer, nullable=False, comment="数据库端口")
    database: Mapped[str] = mapped_column(String(100), nullable=False, comment="数据库名")
    username: Mapped[str] = mapped_column(String(100), nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="加密密码")
    extra_params: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="额外连接参数(JSON)")

    # 连接状态
    last_tested_at: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="最后测试时间")
    is_active: Mapped[bool] = mapped_column(default=True, comment="是否可用")

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="database_connections")  # type: ignore  # noqa: F821
    raw_data_list: Mapped[list["RawData"]] = relationship(  # type: ignore  # noqa: F821
        "RawData", back_populates="connection"
    )

    def __repr__(self) -> str:
        return f"<DatabaseConnection(id={self.id}, name={self.name}, type={self.db_type})>"
