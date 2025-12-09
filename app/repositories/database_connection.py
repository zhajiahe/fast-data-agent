"""
数据库连接 Repository

封装数据库连接相关的数据库操作
"""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database_connection import DatabaseConnection
from app.repositories.base import BaseRepository


class DatabaseConnectionRepository(BaseRepository[DatabaseConnection]):
    """数据库连接数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(DatabaseConnection, db)

    async def get_by_user(
        self,
        user_id: int,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> list[DatabaseConnection]:
        """获取用户的连接列表"""
        return await self.get_all(skip=skip, limit=limit, filters={"user_id": user_id})

    async def search(
        self,
        user_id: int,
        *,
        keyword: str | None = None,
        db_type: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[DatabaseConnection], int]:
        """
        搜索数据库连接

        Args:
            user_id: 用户 ID
            keyword: 搜索关键词
            db_type: 数据库类型
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            (连接列表, 总数) 元组
        """
        # 基础查询
        base_filter = [DatabaseConnection.user_id == user_id, DatabaseConnection.deleted == 0]

        # 关键词搜索
        if keyword:
            base_filter.append(
                or_(
                    DatabaseConnection.name.like(f"%{keyword}%"),
                    DatabaseConnection.description.like(f"%{keyword}%"),
                )
            )

        # 类型过滤
        if db_type:
            base_filter.append(DatabaseConnection.db_type == db_type)

        # 获取总数
        count_query = select(func.count()).select_from(DatabaseConnection).where(*base_filter)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # 分页查询
        query = (
            select(DatabaseConnection)
            .where(*base_filter)
            .order_by(DatabaseConnection.create_time.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def name_exists(self, name: str, user_id: int, exclude_id: int | None = None) -> bool:
        """检查连接名称是否已存在"""
        query = select(DatabaseConnection).where(
            DatabaseConnection.name == name,
            DatabaseConnection.user_id == user_id,
            DatabaseConnection.deleted == 0,
        )
        if exclude_id:
            query = query.where(DatabaseConnection.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
