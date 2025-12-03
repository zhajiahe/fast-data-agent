"""
上传文件服务

处理文件上传相关的业务逻辑
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import BadRequestException, NotFoundException
from app.core.minio import minio_client
from app.models.data_source import FileType
from app.models.uploaded_file import UploadedFile
from app.repositories.uploaded_file import UploadedFileRepository
from app.schemas.uploaded_file import FileListQuery, FilePreviewResponse
from app.services.file_processor import FileProcessorService


class UploadedFileService:
    """上传文件服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = UploadedFileRepository(db)

    async def get_file(self, file_id: int, user_id: int) -> UploadedFile:
        """
        获取单个文件

        Args:
            file_id: 文件 ID
            user_id: 用户 ID

        Returns:
            文件实例

        Raises:
            NotFoundException: 文件不存在
        """
        file = await self.repo.get_by_id(file_id)
        if not file or file.user_id != user_id:
            raise NotFoundException(msg="文件不存在")
        return file

    async def get_files(
        self,
        user_id: int,
        query_params: FileListQuery,
        page_num: int = 1,
        page_size: int = 10,
    ) -> tuple[list[UploadedFile], int]:
        """
        获取文件列表

        Args:
            user_id: 用户 ID
            query_params: 查询参数
            page_num: 页码
            page_size: 每页数量

        Returns:
            (文件列表, 总数) 元组
        """
        skip = (page_num - 1) * page_size
        return await self.repo.search(
            user_id,
            keyword=query_params.keyword,
            file_type=query_params.file_type,
            status=query_params.status,
            skip=skip,
            limit=page_size,
        )

    async def upload_file(
        self,
        user_id: int,
        filename: str,
        content: bytes,
        content_type: str | None = None,
    ) -> UploadedFile:
        """
        上传文件

        Args:
            user_id: 用户 ID
            filename: 原始文件名
            content: 文件内容
            content_type: MIME 类型

        Returns:
            创建的文件实例
        """
        # 检查文件大小
        if len(content) > settings.MAX_UPLOAD_SIZE:
            raise BadRequestException(msg=f"文件大小超过限制 ({settings.MAX_UPLOAD_SIZE // 1024 // 1024}MB)")

        # 检测文件类型
        file_type = FileProcessorService.detect_file_type(filename, content_type)

        # 生成存储名称
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        object_key = f"files/{user_id}/{stored_name}"

        # 上传到 MinIO
        await minio_client.upload_file(
            object_name=object_key,
            data=content,
            length=len(content),
            content_type=content_type or "application/octet-stream",
        )

        # 创建数据库记录
        create_data: dict[str, Any] = {
            "user_id": user_id,
            "original_name": filename,
            "stored_name": stored_name,
            "object_key": object_key,
            "bucket_name": settings.MINIO_BUCKET,
            "file_type": file_type.value,
            "file_size": len(content),
            "mime_type": content_type,
            "status": "processing",
        }

        file = await self.repo.create(create_data)

        # 异步处理文件（提取元数据）
        try:
            metadata = await FileProcessorService.parse_file(content, file_type)
            await self.repo.update(
                file,
                {
                    "row_count": metadata["row_count"],
                    "column_count": metadata["column_count"],
                    "columns_info": metadata["columns_info"],
                    "preview_data": metadata["preview_data"],
                    "status": "ready",
                },
            )
        except Exception as e:
            await self.repo.update(file, {"status": "error", "error_message": str(e)})

        return file

    async def delete_file(self, file_id: int, user_id: int) -> None:
        """
        删除文件

        Args:
            file_id: 文件 ID
            user_id: 用户 ID

        Raises:
            NotFoundException: 文件不存在
        """
        file = await self.get_file(file_id, user_id)

        # 从 MinIO 删除
        try:
            await minio_client.delete_file(file.object_key)
        except Exception:
            pass  # 忽略删除错误

        # 软删除数据库记录
        await self.repo.delete(file_id, soft_delete=True)

    async def get_preview(self, file_id: int, user_id: int, rows: int = 100) -> FilePreviewResponse:
        """
        获取文件预览

        Args:
            file_id: 文件 ID
            user_id: 用户 ID
            rows: 预览行数

        Returns:
            预览数据
        """
        file = await self.get_file(file_id, user_id)

        if file.status != "ready":
            raise BadRequestException(msg="文件尚未处理完成")

        # 优先使用缓存的预览数据
        if file.preview_data and file.columns_info:
            return FilePreviewResponse(
                columns=file.columns_info,  # type: ignore[arg-type]
                data=file.preview_data[:rows],
                total_rows=file.row_count or 0,
            )

        # 从 MinIO 下载并解析
        content = await minio_client.download_file(file.object_key)
        columns, data, total = await FileProcessorService.get_preview(content, FileType(file.file_type), rows)

        return FilePreviewResponse(columns=columns, data=data, total_rows=total)

    async def get_download_url(self, file_id: int, user_id: int, expires: int = 3600) -> str:
        """
        获取文件下载 URL

        Args:
            file_id: 文件 ID
            user_id: 用户 ID
            expires: 过期时间（秒）

        Returns:
            预签名下载 URL
        """
        file = await self.get_file(file_id, user_id)
        return await minio_client.get_presigned_url(file.object_key, expires=expires)
