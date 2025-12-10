"""
用户 Repository

封装用户相关的数据库操作
"""

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """用户数据访问层"""

    def __init__(self, db: AsyncSession):
        super().__init__(User, db)

    async def get_by_username(self, username: str) -> User | None:
        """
        根据用户名获取用户

        Args:
            username: 用户名

        Returns:
            用户实例或 None
        """
        result = await self.db.execute(select(User).where(User.username == username, User.deleted == 0))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """
        根据邮箱获取用户

        Args:
            email: 邮箱

        Returns:
            用户实例或 None
        """
        result = await self.db.execute(select(User).where(User.email == email, User.deleted == 0))
        return result.scalar_one_or_none()

    async def search(
        self,
        *,
        keyword: str | None = None,
        is_active: bool | None = None,
        is_superuser: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[User], int]:
        """
        搜索用户（支持关键词、状态过滤和分页）

        Args:
            keyword: 搜索关键词（匹配用户名、邮箱、昵称）
            is_active: 激活状态过滤
            is_superuser: 超级管理员过滤
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            (用户列表, 总数) 元组
        """
        # 基础查询
        query = select(User).where(User.deleted == 0)
        count_query = select(User).where(User.deleted == 0)

        # 关键词搜索
        if keyword:
            keyword_filter = or_(
                User.username.like(f"%{keyword}%"),
                User.email.like(f"%{keyword}%"),
                User.nickname.like(f"%{keyword}%"),
            )
            query = query.where(keyword_filter)
            count_query = count_query.where(keyword_filter)

        # 激活状态过滤
        if is_active is not None:
            query = query.where(User.is_active == is_active)
            count_query = count_query.where(User.is_active == is_active)

        # 超级管理员过滤
        if is_superuser is not None:
            query = query.where(User.is_superuser == is_superuser)
            count_query = count_query.where(User.is_superuser == is_superuser)

        # 获取总数
        from sqlalchemy import func

        count_result = await self.db.execute(select(func.count()).select_from(count_query.subquery()))
        total = count_result.scalar() or 0

        # 分页查询
        query = query.order_by(User.create_time.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def username_exists(self, username: str, exclude_id: uuid.UUID | None = None) -> bool:
        """
        检查用户名是否已存在

        Args:
            username: 用户名
            exclude_id: 排除的用户 ID（用于更新时检查）

        Returns:
            是否存在
        """
        query = select(User).where(User.username == username, User.deleted == 0)
        if exclude_id:
            query = query.where(User.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None

    async def email_exists(self, email: str, exclude_id: uuid.UUID | None = None) -> bool:
        """
        检查邮箱是否已存在

        Args:
            email: 邮箱
            exclude_id: 排除的用户 ID（用于更新时检查）

        Returns:
            是否存在
        """
        query = select(User).where(User.email == email, User.deleted == 0)
        if exclude_id:
            query = query.where(User.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
