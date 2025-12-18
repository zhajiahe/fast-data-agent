"""
认证服务

处理用户认证相关的业务逻辑
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, UnauthorizedException
from app.core.security import create_tokens, get_password_hash, verify_password, verify_refresh_token
from app.models.base import Token
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import LoginRequest, UserCreate


class AuthService:
    """认证服务类"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def login(self, login_data: LoginRequest) -> Token:
        """
        用户登录

        Args:
            login_data: 登录请求数据

        Returns:
            Token: 访问令牌和刷新令牌

        Raises:
            UnauthorizedException: 用户名或密码错误
            ForbiddenException: 用户已被禁用
        """
        # 查找用户
        user = await self.user_repo.get_by_username(login_data.username)

        # 验证用户和密码
        if not user or not verify_password(login_data.password, user.hashed_password):
            raise UnauthorizedException(msg="用户名或密码错误")

        # 检查用户状态
        if not user.is_active:
            raise ForbiddenException(msg="用户已被禁用")

        # 创建 token
        access_token, refresh_token = create_tokens({"user_id": user.id})

        return Token(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def register(self, user_data: UserCreate) -> User:
        """
        用户注册

        Args:
            user_data: 用户注册数据

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
                "is_active": True,
                "is_superuser": False,
            }
        )

        return user

    async def refresh_token(self, refresh_token_str: str) -> Token:
        """
        刷新访问令牌

        Args:
            refresh_token_str: 刷新令牌

        Returns:
            Token: 新的访问令牌和刷新令牌

        Raises:
            UnauthorizedException: 刷新令牌无效或已过期
            ForbiddenException: 用户已被禁用
        """
        credentials_exception = UnauthorizedException(msg="刷新令牌无效或已过期")

        # 验证刷新令牌
        try:
            user_id = verify_refresh_token(refresh_token_str, credentials_exception)
        except Exception as e:
            raise credentials_exception from e

        # 获取用户信息
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise credentials_exception

        if not user.is_active:
            raise ForbiddenException(msg="用户已被禁用")

        # 创建新的 token
        access_token, refresh_token = create_tokens({"user_id": user.id})

        return Token(
            id=user.id,
            username=user.username,
            nickname=user.nickname,
            email=user.email,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            access_token=access_token,
            refresh_token=refresh_token,
        )

    async def change_password(
        self,
        user: User,
        old_password: str,
        new_password: str,
    ) -> None:
        """
        修改密码

        Args:
            user: 当前用户
            old_password: 旧密码
            new_password: 新密码

        Raises:
            BadRequestException: 旧密码错误或新旧密码相同
        """
        # 验证旧密码
        if not verify_password(old_password, user.hashed_password):
            raise BadRequestException(msg="旧密码错误")

        # 检查新旧密码是否相同
        if old_password == new_password:
            raise BadRequestException(msg="新密码不能与旧密码相同")

        # 更新密码
        user.hashed_password = get_password_hash(new_password)
        await self.db.flush()
