"""
上传文件相关的 Pydantic Schema
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.data_source import FileType


class UploadedFileResponse(BaseModel):
    """上传文件响应"""

    id: int = Field(..., description="文件ID")
    user_id: int = Field(..., description="上传用户ID")

    original_name: str = Field(..., description="原始文件名")
    object_key: str = Field(..., description="MinIO对象存储Key")
    file_type: FileType = Field(..., description="文件类型")
    file_size: int = Field(..., description="文件大小(字节)")
    mime_type: str | None = Field(default=None, description="MIME类型")

    # 元数据
    row_count: int | None = Field(default=None, description="数据行数")
    column_count: int | None = Field(default=None, description="数据列数")
    columns_info: list[dict[str, Any]] | None = Field(default=None, description="列信息")

    # 状态
    status: str = Field(..., description="处理状态")
    error_message: str | None = Field(default=None, description="错误信息")

    create_time: datetime | None = Field(default=None, description="创建时间")
    update_time: datetime | None = Field(default=None, description="更新时间")

    model_config = {"from_attributes": True}


class FilePreviewResponse(BaseModel):
    """文件预览响应"""

    columns: list[dict[str, Any]] = Field(..., description="列信息")
    data: list[dict[str, Any]] = Field(..., description="预览数据")
    total_rows: int = Field(..., description="总行数")


class FileListQuery(BaseModel):
    """文件列表查询参数"""

    keyword: str | None = Field(default=None, description="搜索关键词")
    file_type: FileType | None = Field(default=None, description="文件类型")
    status: str | None = Field(default=None, description="处理状态")
