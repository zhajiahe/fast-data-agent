"""
MinIO 客户端封装

提供文件上传、下载、删除等操作
"""

from io import BytesIO
from typing import BinaryIO

from loguru import logger
from miniopy_async import Minio  # type: ignore[attr-defined]

from app.core.config import settings


class MinioClient:
    """MinIO 客户端封装"""

    _instance: "MinioClient | None" = None
    _client: Minio | None = None

    def __new__(cls) -> "MinioClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def client(self) -> Minio:
        """获取 MinIO 客户端实例"""
        if self._client is None:
            self._client = Minio(
                settings.MINIO_ENDPOINT,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
        return self._client

    async def ensure_bucket(self, bucket_name: str | None = None) -> None:
        """
        确保 bucket 存在，不存在则创建

        Args:
            bucket_name: bucket 名称，默认使用配置中的 bucket
        """
        bucket = bucket_name or settings.MINIO_BUCKET
        if not await self.client.bucket_exists(bucket):
            await self.client.make_bucket(bucket)
            logger.info(f"Created MinIO bucket: {bucket}")

    async def upload_file(
        self,
        object_name: str,
        data: BinaryIO | bytes,
        length: int,
        content_type: str = "application/octet-stream",
        bucket_name: str | None = None,
    ) -> str:
        """
        上传文件到 MinIO

        Args:
            object_name: 对象名称（存储路径）
            data: 文件数据
            length: 文件大小
            content_type: 文件 MIME 类型
            bucket_name: bucket 名称

        Returns:
            对象名称
        """
        bucket = bucket_name or settings.MINIO_BUCKET
        await self.ensure_bucket(bucket)

        if isinstance(data, bytes):
            data = BytesIO(data)

        await self.client.put_object(
            bucket,
            object_name,
            data,
            length,
            content_type=content_type,
        )
        logger.debug(f"Uploaded file to MinIO: {bucket}/{object_name}")
        return object_name

    async def download_file(
        self,
        object_name: str,
        bucket_name: str | None = None,
    ) -> bytes:
        """
        从 MinIO 下载文件

        Args:
            object_name: 对象名称
            bucket_name: bucket 名称

        Returns:
            文件内容
        """
        bucket = bucket_name or settings.MINIO_BUCKET
        response = await self.client.get_object(bucket, object_name)
        data: bytes = await response.read()
        response.close()
        await response.release()
        return data

    async def delete_file(
        self,
        object_name: str,
        bucket_name: str | None = None,
    ) -> None:
        """
        从 MinIO 删除文件

        Args:
            object_name: 对象名称
            bucket_name: bucket 名称
        """
        bucket = bucket_name or settings.MINIO_BUCKET
        await self.client.remove_object(bucket, object_name)
        logger.debug(f"Deleted file from MinIO: {bucket}/{object_name}")

    async def get_presigned_url(
        self,
        object_name: str,
        bucket_name: str | None = None,
        expires: int = 3600,
    ) -> str:
        """
        获取预签名 URL

        Args:
            object_name: 对象名称
            bucket_name: bucket 名称
            expires: 过期时间（秒）

        Returns:
            预签名 URL
        """
        from datetime import timedelta

        bucket = bucket_name or settings.MINIO_BUCKET
        url: str = await self.client.presigned_get_object(
            bucket,
            object_name,
            expires=timedelta(seconds=expires),
        )
        return url

    async def file_exists(
        self,
        object_name: str,
        bucket_name: str | None = None,
    ) -> bool:
        """
        检查文件是否存在

        Args:
            object_name: 对象名称
            bucket_name: bucket 名称

        Returns:
            是否存在
        """
        bucket = bucket_name or settings.MINIO_BUCKET
        try:
            await self.client.stat_object(bucket, object_name)
            return True
        except Exception:
            return False


# 全局实例
minio_client = MinioClient()
