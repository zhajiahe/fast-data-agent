"""
文件上传模型

存储用户上传的数据文件信息
"""

import uuid

from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, BaseTableMixin


class UploadedFile(Base, BaseTableMixin):
    """
    上传文件表

    存储用户上传的文件元信息，实际文件存储在文件系统或对象存储中
    """

    __tablename__ = "uploaded_files"

    # 基本信息
    original_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    stored_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, comment="存储文件名(UUID)")
    object_key: Mapped[str] = mapped_column(String(500), nullable=False, comment="MinIO对象存储Key")
    bucket_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="MinIO桶名称")
    file_type: Mapped[str] = mapped_column(String(20), nullable=False, comment="文件类型: csv/excel/json/parquet")
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False, comment="文件大小(字节)")
    mime_type: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="MIME类型")

    # 所属用户
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True, comment="上传用户ID"
    )

    # 文件元数据
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="数据行数")
    column_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="数据列数")
    columns_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="列信息(JSON)")
    preview_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True, comment="预览数据(前几行)")

    # 处理状态
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", comment="处理状态: pending/processing/ready/error"
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误信息")

    # 关系
    user: Mapped["User"] = relationship("User", back_populates="uploaded_files")  # type: ignore  # noqa: F821
    # 关联原始数据（一个文件对应一个 RawData）
    raw_data: Mapped["RawData | None"] = relationship(  # type: ignore  # noqa: F821
        "RawData", back_populates="uploaded_file", uselist=False
    )

    def __repr__(self) -> str:
        return f"<UploadedFile(id={self.id}, name={self.original_name}, type={self.file_type})>"
