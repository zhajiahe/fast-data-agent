"""
原始数据 Repository

封装原始数据相关的数据库操作
"""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.raw_data import RawData, RawDataType
from app.repositories.base import BaseRepository


class RawDataRepository(BaseRepository[RawData]):
    """原始数据数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(RawData, db)

    async def get_by_user(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[RawData]:
        """获取用户的原始数据列表"""
        return await self.get_all(skip=skip, limit=limit, filters={"user_id": user_id})

    async def search(
        self,
        user_id: int,
        *,
        keyword: str | None = None,
        raw_type: RawDataType | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[RawData], int]:
        """
        搜索原始数据

        Args:
            user_id: 用户 ID
            keyword: 搜索关键词
            raw_type: 原始数据类型
            status: 状态
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            (原始数据列表, 总数) 元组
        """
        # 基础查询
        base_filter = [RawData.user_id == user_id, RawData.deleted == 0]

        # 关键词搜索
        if keyword:
            base_filter.append(
                or_(
                    RawData.name.like(f"%{keyword}%"),
                    RawData.description.like(f"%{keyword}%"),
                )
            )

        # 类型过滤
        if raw_type:
            base_filter.append(RawData.raw_type == raw_type.value)

        # 状态过滤
        if status:
            base_filter.append(RawData.status == status)

        # 获取总数
        count_query = select(func.count()).select_from(RawData).where(*base_filter)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # 分页查询
        query = select(RawData).where(*base_filter).order_by(RawData.create_time.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_ids(self, ids: list[int], user_id: int) -> list[RawData]:
        """
        根据 ID 列表获取原始数据

        Args:
            ids: ID 列表
            user_id: 用户 ID

        Returns:
            原始数据列表
        """
        query = select(RawData).where(
            RawData.id.in_(ids),
            RawData.user_id == user_id,
            RawData.deleted == 0,
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_with_relations(self, id: int) -> RawData | None:
        """
        获取原始数据（包含关联的 connection 和 uploaded_file）

        Args:
            id: 原始数据 ID

        Returns:
            原始数据实例或 None
        """
        query = (
            select(RawData)
            .options(
                selectinload(RawData.connection),
                selectinload(RawData.uploaded_file),
            )
            .where(RawData.id == id, RawData.deleted == 0)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def name_exists(self, name: str, user_id: int, exclude_id: int | None = None) -> bool:
        """检查原始数据名称是否已存在"""
        query = select(RawData).where(
            RawData.name == name,
            RawData.user_id == user_id,
            RawData.deleted == 0,
        )
        if exclude_id:
            query = query.where(RawData.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
