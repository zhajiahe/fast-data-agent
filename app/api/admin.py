"""
超级管理员 API 路由

提供系统管理功能，包括：
- 系统统计信息
- 用户管理增强功能
- 系统配置管理
"""

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentSuperUser, DBSession
from app.core.security import get_password_hash
from app.models.base import BaseResponse
from app.models.data_source import DataSource
from app.models.database_connection import DatabaseConnection
from app.models.message import ChatMessage
from app.models.raw_data import RawData
from app.models.session import AnalysisSession
from app.models.uploaded_file import UploadedFile
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.user import UserService

router = APIRouter(prefix="/admin", tags=["admin"])


# ==================== Schema 定义 ====================


class SystemStats(BaseModel):
    """系统统计信息"""

    total_users: int = Field(..., description="总用户数")
    active_users: int = Field(..., description="活跃用户数")
    total_sessions: int = Field(..., description="总会话数")
    total_messages: int = Field(..., description="总消息数")
    total_data_sources: int = Field(..., description="总数据源数")
    total_raw_data: int = Field(..., description="总数据对象数")
    total_connections: int = Field(..., description="总数据库连接数")
    total_files: int = Field(..., description="总上传文件数")
    users_today: int = Field(..., description="今日新增用户")
    sessions_today: int = Field(..., description="今日新增会话")
    messages_today: int = Field(..., description="今日新增消息")


class UserToggleRequest(BaseModel):
    """用户状态切换请求"""

    is_active: bool = Field(..., description="是否激活")


class UserRoleRequest(BaseModel):
    """用户角色更新请求"""

    is_superuser: bool = Field(..., description="是否超级管理员")


class ResetPasswordRequest(BaseModel):
    """重置密码请求"""

    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")


# ==================== 系统统计接口 ====================


@router.get("/stats", response_model=BaseResponse[SystemStats])
async def get_system_stats(
    _current_user: CurrentSuperUser,
    db: DBSession,
):
    """
    获取系统统计信息

    需要超级管理员权限
    """
    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    # 用户统计
    total_users = (await db.execute(select(func.count()).select_from(User).where(User.deleted == 0))).scalar() or 0
    active_users = (
        await db.execute(select(func.count()).select_from(User).where(User.deleted == 0, User.is_active == True))
    ).scalar() or 0
    users_today = (
        await db.execute(
            select(func.count()).select_from(User).where(User.deleted == 0, User.create_time >= today_start)
        )
    ).scalar() or 0

    # 会话统计
    total_sessions = (
        await db.execute(select(func.count()).select_from(AnalysisSession).where(AnalysisSession.deleted == 0))
    ).scalar() or 0
    sessions_today = (
        await db.execute(
            select(func.count())
            .select_from(AnalysisSession)
            .where(AnalysisSession.deleted == 0, AnalysisSession.create_time >= today_start)
        )
    ).scalar() or 0

    # 消息统计
    total_messages = (
        await db.execute(select(func.count()).select_from(ChatMessage).where(ChatMessage.deleted == 0))
    ).scalar() or 0
    messages_today = (
        await db.execute(
            select(func.count())
            .select_from(ChatMessage)
            .where(ChatMessage.deleted == 0, ChatMessage.create_time >= today_start)
        )
    ).scalar() or 0

    # 数据源统计
    total_data_sources = (
        await db.execute(select(func.count()).select_from(DataSource).where(DataSource.deleted == 0))
    ).scalar() or 0

    # 数据对象统计
    total_raw_data = (
        await db.execute(select(func.count()).select_from(RawData).where(RawData.deleted == 0))
    ).scalar() or 0

    # 数据库连接统计
    total_connections = (
        await db.execute(select(func.count()).select_from(DatabaseConnection).where(DatabaseConnection.deleted == 0))
    ).scalar() or 0

    # 上传文件统计
    total_files = (
        await db.execute(select(func.count()).select_from(UploadedFile).where(UploadedFile.deleted == 0))
    ).scalar() or 0

    return BaseResponse(
        success=True,
        code=200,
        msg="获取系统统计成功",
        data=SystemStats(
            total_users=total_users,
            active_users=active_users,
            total_sessions=total_sessions,
            total_messages=total_messages,
            total_data_sources=total_data_sources,
            total_raw_data=total_raw_data,
            total_connections=total_connections,
            total_files=total_files,
            users_today=users_today,
            sessions_today=sessions_today,
            messages_today=messages_today,
        ),
    )


# ==================== 用户管理增强接口 ====================


@router.patch("/users/{user_id}/toggle", response_model=BaseResponse[UserResponse])
async def toggle_user_status(
    user_id: uuid.UUID,
    request: UserToggleRequest,
    _current_user: CurrentSuperUser,
    db: DBSession,
):
    """
    切换用户激活状态

    需要超级管理员权限
    """
    user_service = UserService(db)
    user = await user_service.get_user(user_id)

    # 不允许禁用自己
    if user.id == _current_user.id and not request.is_active:
        return BaseResponse(success=False, code=400, msg="不能禁用自己的账号", data=None)

    user.is_active = request.is_active
    await db.commit()
    await db.refresh(user)

    return BaseResponse(
        success=True,
        code=200,
        msg=f"用户已{'激活' if request.is_active else '禁用'}",
        data=UserResponse.model_validate(user),
    )


@router.patch("/users/{user_id}/role", response_model=BaseResponse[UserResponse])
async def update_user_role(
    user_id: uuid.UUID,
    request: UserRoleRequest,
    _current_user: CurrentSuperUser,
    db: DBSession,
):
    """
    更新用户角色

    需要超级管理员权限
    """
    user_service = UserService(db)
    user = await user_service.get_user(user_id)

    # 不允许取消自己的管理员权限
    if user.id == _current_user.id and not request.is_superuser:
        return BaseResponse(success=False, code=400, msg="不能取消自己的管理员权限", data=None)

    user.is_superuser = request.is_superuser
    await db.commit()
    await db.refresh(user)

    return BaseResponse(
        success=True,
        code=200,
        msg=f"用户已{'设为管理员' if request.is_superuser else '取消管理员权限'}",
        data=UserResponse.model_validate(user),
    )


@router.post("/users/{user_id}/reset-password", response_model=BaseResponse[None])
async def reset_user_password(
    user_id: uuid.UUID,
    request: ResetPasswordRequest,
    _current_user: CurrentSuperUser,
    db: DBSession,
):
    """
    重置用户密码

    需要超级管理员权限
    """
    user_service = UserService(db)
    user = await user_service.get_user(user_id)

    user.hashed_password = get_password_hash(request.new_password)
    await db.commit()

    return BaseResponse(success=True, code=200, msg="密码重置成功", data=None)

