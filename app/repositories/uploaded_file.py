"""
上传文件 Repository

封装上传文件相关的数据库操作
"""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.data_source import FileType
from app.models.uploaded_file import UploadedFile
from app.repositories.base import BaseRepository


class UploadedFileRepository(BaseRepository[UploadedFile]):
    """上传文件数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(UploadedFile, db)

    async def search(
        self,
        user_id: uuid.UUID,
        *,
        keyword: str | None = None,
        file_type: FileType | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[UploadedFile], int]:
        """
        搜索上传文件

        Args:
            user_id: 用户 ID
            keyword: 搜索关键词
            file_type: 文件类型
            status: 处理状态
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            (文件列表, 总数) 元组
        """
        from sqlalchemy import func

        # 基础查询
        query = select(UploadedFile).where(UploadedFile.user_id == user_id, UploadedFile.deleted == 0)
        count_query = select(UploadedFile).where(UploadedFile.user_id == user_id, UploadedFile.deleted == 0)

        # 关键词搜索
        if keyword:
            keyword_filter = or_(
                UploadedFile.original_name.like(f"%{keyword}%"),
            )
            query = query.where(keyword_filter)
            count_query = count_query.where(keyword_filter)

        # 类型过滤
        if file_type:
            query = query.where(UploadedFile.file_type == file_type.value)
            count_query = count_query.where(UploadedFile.file_type == file_type.value)

        # 状态过滤
        if status:
            query = query.where(UploadedFile.status == status)
            count_query = count_query.where(UploadedFile.status == status)

        # 获取总数
        count_result = await self.db.execute(select(func.count()).select_from(count_query.subquery()))
        total = count_result.scalar() or 0

        # 分页查询
        query = query.order_by(UploadedFile.create_time.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_stored_name(self, stored_name: str) -> UploadedFile | None:
        """根据存储名称获取文件"""
        result = await self.db.execute(
            select(UploadedFile).where(UploadedFile.stored_name == stored_name, UploadedFile.deleted == 0)
        )
        return result.scalar_one_or_none()
