"""
用户服务

处理用户管理相关的业务逻辑
"""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.core.security import get_password_hash
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserListQuery, UserUpdate


class UserService:
    """用户服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def get_user(self, user_id: uuid.UUID) -> User:
        """
        获取单个用户

        Args:
            user_id: 用户 ID

        Returns:
            User: 用户实例

        Raises:
            NotFoundException: 用户不存在
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(msg="用户不存在")
        return user

    async def get_users(
        self,
        query_params: UserListQuery,
        page_num: int = 1,
        page_size: int = 10,
    ) -> tuple[list[User], int]:
        """
        获取用户列表

        Args:
            query_params: 查询参数
            page_num: 页码
            page_size: 每页数量

        Returns:
            (用户列表, 总数) 元组
        """
        skip = (page_num - 1) * page_size
        return await self.user_repo.search(
            keyword=query_params.keyword,
            is_active=query_params.is_active,
            is_superuser=query_params.is_superuser,
            skip=skip,
            limit=page_size,
        )

    async def create_user(self, user_data: UserCreate) -> User:
        """
        创建用户

        Args:
            user_data: 用户创建数据

        Returns:
            User: 创建的用户实例

        Raises:
            BadRequestException: 用户名或邮箱已存在
        """
        # 检查用户名是否已存在
        if await self.user_repo.username_exists(user_data.username):
            raise BadRequestException(msg="用户名已存在")

        # 检查邮箱是否已存在
        if await self.user_repo.email_exists(user_data.email):
            raise BadRequestException(msg="邮箱已存在")

        # 创建用户
        user = await self.user_repo.create(
            {
                "username": user_data.username,
                "email": user_data.email,
                "nickname": user_data.nickname,
                "hashed_password": get_password_hash(user_data.password),
                "is_active": user_data.is_active,
                "is_superuser": user_data.is_superuser,
            }
        )

        return user

    async def update_user(
        self,
        user_id: uuid.UUID,
        user_data: UserUpdate,
    ) -> User:
        """
        更新用户

        Args:
            user_id: 用户 ID
            user_data: 更新数据

        Returns:
            User: 更新后的用户实例

        Raises:
            NotFoundException: 用户不存在
            BadRequestException: 邮箱已被使用
        """
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundException(msg="用户不存在")

        # 检查邮箱是否已被其他用户使用
        if user_data.email is not None:
            if await self.user_repo.email_exists(user_data.email, exclude_id=user_id):
                raise BadRequestException(msg="邮箱已被使用")

        # 更新用户
        update_data = user_data.model_dump(exclude_unset=True)
        user = await self.user_repo.update(user, update_data)

        return user

    async def update_current_user(
        self,
        user: User,
        user_data: UserUpdate,
    ) -> User:
        """
        更新当前用户信息

        Args:
            user: 当前用户
            user_data: 更新数据

        Returns:
            User: 更新后的用户实例

        Raises:
            BadRequestException: 邮箱已被使用
        """
        # 检查邮箱是否已被其他用户使用
        if user_data.email is not None:
            if await self.user_repo.email_exists(user_data.email, exclude_id=user.id):
                raise BadRequestException(msg="邮箱已被使用")

        # 只允许更新部分字段
        update_data = {}
        if user_data.email is not None:
            update_data["email"] = user_data.email
        if user_data.nickname is not None:
            update_data["nickname"] = user_data.nickname

        if update_data:
            user = await self.user_repo.update(user, update_data)

        return user

    async def delete_user(self, user_id: uuid.UUID) -> None:
        """
        删除用户（逻辑删除）

        Args:
            user_id: 用户 ID

        Raises:
            NotFoundException: 用户不存在
        """
        success = await self.user_repo.delete(user_id, soft_delete=True)
        if not success:
            raise NotFoundException(msg="用户不存在")
