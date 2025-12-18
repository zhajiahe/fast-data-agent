"""
依赖注入模块

提供常用的依赖注入函数，用于路由中获取数据库会话、当前用户等
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import verify_access_token
from app.models.user import User

# HTTP Bearer 认证方案
security = HTTPBearer()

# 类型别名
DBSession = Annotated[AsyncSession, Depends(get_db)]
TokenCredentials = Annotated[HTTPAuthorizationCredentials, Depends(security)]


async def get_current_user(
    db: DBSession,
    credentials: TokenCredentials,
) -> User:
    """
    获取当前登录用户

    Args:
        db: 数据库会话
        credentials: Token 凭证

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 认证失败时抛出 401 错误
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败，请重新登录",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 验证 token 并获取用户ID
    token = credentials.credentials
    user_id = verify_access_token(token, credentials_exception)

    # 从数据库获取用户
    result = await db.execute(select(User).where(User.id == user_id, User.deleted == 0))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    # 检查用户是否激活
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="用户已被禁用",
        )

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    获取当前激活的用户（已被 get_current_user 包含）

    保留此函数是为了向后兼容。新代码应直接使用 CurrentUser。

    Args:
        current_user: 当前用户

    Returns:
        User: 当前用户对象
    """
    # is_active 检查已在 get_current_user 中完成
    return current_user


async def get_current_superuser(
    current_user: Annotated[User, Depends(get_current_active_user)],
) -> User:
    """
    获取当前超级管理员用户

    Args:
        current_user: 当前用户

    Returns:
        User: 当前用户对象

    Raises:
        HTTPException: 用户不是超级管理员时抛出 403 错误
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="权限不足",
        )
    return current_user


# 类型别名（用于路由中）
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentActiveUser = Annotated[User, Depends(get_current_active_user)]
CurrentSuperUser = Annotated[User, Depends(get_current_superuser)]
