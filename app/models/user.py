from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseTableMixin

if TYPE_CHECKING:
    from app.models.data_source import DataSource
    from app.models.database_connection import DatabaseConnection
    from app.models.raw_data import RawData
    from app.models.session import AnalysisSession
    from app.models.uploaded_file import UploadedFile


class User(Base, BaseTableMixin):
    """用户表模型"""

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True, comment="邮箱")
    nickname: Mapped[str] = mapped_column(String(50), nullable=False, comment="昵称")
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False, comment="加密密码")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, comment="是否激活")
    is_superuser: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否超级管理员")

    # 关系
    data_sources: Mapped[list["DataSource"]] = relationship(
        "DataSource", back_populates="user", cascade="all, delete-orphan"
    )
    uploaded_files: Mapped[list["UploadedFile"]] = relationship(
        "UploadedFile", back_populates="user", cascade="all, delete-orphan"
    )
    analysis_sessions: Mapped[list["AnalysisSession"]] = relationship(
        "AnalysisSession", back_populates="user", cascade="all, delete-orphan"
    )
    # 新增：数据库连接
    database_connections: Mapped[list["DatabaseConnection"]] = relationship(
        "DatabaseConnection", back_populates="user", cascade="all, delete-orphan"
    )
    # 新增：原始数据
    raw_data_list: Mapped[list["RawData"]] = relationship(
        "RawData", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, email={self.email})>"
