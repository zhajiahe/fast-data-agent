"""
超级管理员 API 路由

提供系统管理功能，包括：
- 系统统计信息
- 用户管理增强功能
- 用户资源查看
- 批量用户删除（级联删除资源）
- 系统配置管理
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import CurrentSuperUser, DBSession
from app.core.minio import minio_client
from app.core.security import get_password_hash
from app.models.base import BaseResponse
from app.models.database_connection import DatabaseConnection
from app.models.message import ChatMessage
from app.models.raw_data import RawData
from app.models.session import AnalysisSession, SessionRawData
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


class UserResourceStats(BaseModel):
    """用户资源统计"""

    user_id: uuid.UUID = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    nickname: str = Field(..., description="昵称")
    sessions_count: int = Field(..., description="会话数")
    messages_count: int = Field(..., description="消息数")
    raw_data_count: int = Field(..., description="数据对象数")
    connections_count: int = Field(..., description="数据库连接数")
    files_count: int = Field(..., description="上传文件数")
    total_file_size: int = Field(..., description="文件总大小(bytes)")


class UserResourceDetail(BaseModel):
    """用户资源详情"""

    user: UserResponse = Field(..., description="用户信息")
    resources: UserResourceStats = Field(..., description="资源统计")
    sessions: list[dict[str, Any]] = Field(default_factory=list, description="会话列表")
    raw_data: list[dict[str, Any]] = Field(default_factory=list, description="数据对象列表")
    connections: list[dict[str, Any]] = Field(default_factory=list, description="数据库连接列表")
    files: list[dict[str, Any]] = Field(default_factory=list, description="文件列表")


class BatchDeleteRequest(BaseModel):
    """批量删除请求"""

    user_ids: list[uuid.UUID] = Field(..., min_length=1, description="要删除的用户ID列表")


class BatchDeleteResult(BaseModel):
    """批量删除结果"""

    success_count: int = Field(..., description="成功删除数")
    failed_count: int = Field(..., description="失败数")
    skipped_count: int = Field(..., description="跳过数（如当前用户）")
    details: list[dict[str, Any]] = Field(default_factory=list, description="详细结果")


class CascadeDeleteResult(BaseModel):
    """级联删除结果"""

    user_id: uuid.UUID = Field(..., description="用户ID")
    username: str = Field(..., description="用户名")
    deleted_sessions: int = Field(..., description="删除的会话数")
    deleted_messages: int = Field(..., description="删除的消息数")
    deleted_raw_data: int = Field(..., description="删除的数据对象数")
    deleted_connections: int = Field(..., description="删除的数据库连接数")
    deleted_files: int = Field(..., description="删除的文件数")
    sandbox_cleaned: bool = Field(..., description="沙箱是否已清理")
    minio_files_deleted: int = Field(..., description="MinIO文件删除数")


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
        await db.execute(select(func.count()).select_from(User).where(User.deleted == 0, User.is_active.is_(True)))
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


# ==================== 用户资源查看接口 ====================


@router.get("/users/{user_id}/resources", response_model=BaseResponse[UserResourceDetail])
async def get_user_resources(
    user_id: uuid.UUID,
    _current_user: CurrentSuperUser,
    db: DBSession,
):
    """
    获取用户所有资源详情

    包括会话、数据对象、数据库连接、文件等

    需要超级管理员权限
    """
    user_service = UserService(db)
    user = await user_service.get_user(user_id)

    # 获取各类资源统计
    sessions_count = (
        await db.execute(
            select(func.count())
            .select_from(AnalysisSession)
            .where(AnalysisSession.user_id == user_id, AnalysisSession.deleted == 0)
        )
    ).scalar() or 0

    messages_count = (
        await db.execute(
            select(func.count())
            .select_from(ChatMessage)
            .join(AnalysisSession, ChatMessage.session_id == AnalysisSession.id)
            .where(AnalysisSession.user_id == user_id, ChatMessage.deleted == 0)
        )
    ).scalar() or 0

    raw_data_count = (
        await db.execute(
            select(func.count()).select_from(RawData).where(RawData.user_id == user_id, RawData.deleted == 0)
        )
    ).scalar() or 0

    connections_count = (
        await db.execute(
            select(func.count())
            .select_from(DatabaseConnection)
            .where(DatabaseConnection.user_id == user_id, DatabaseConnection.deleted == 0)
        )
    ).scalar() or 0

    files_result = await db.execute(
        select(func.count(), func.coalesce(func.sum(UploadedFile.file_size), 0))
        .select_from(UploadedFile)
        .where(UploadedFile.user_id == user_id, UploadedFile.deleted == 0)
    )
    files_row = files_result.one()
    files_count = files_row[0] or 0
    total_file_size = files_row[1] or 0

    # 获取详细列表（最近20条）
    sessions_result = await db.execute(
        select(AnalysisSession)
        .where(AnalysisSession.user_id == user_id, AnalysisSession.deleted == 0)
        .order_by(AnalysisSession.create_time.desc())
        .limit(20)
    )
    sessions = [
        {
            "id": str(s.id),
            "name": s.name,
            "status": s.status,
            "message_count": s.message_count,
            "create_time": s.create_time.isoformat() if s.create_time else None,
        }
        for s in sessions_result.scalars().all()
    ]

    raw_data_result = await db.execute(
        select(RawData)
        .where(RawData.user_id == user_id, RawData.deleted == 0)
        .order_by(RawData.create_time.desc())
        .limit(20)
    )
    raw_data_list = [
        {
            "id": str(rd.id),
            "name": rd.name,
            "raw_type": rd.raw_type,
            "description": rd.description,
            "create_time": rd.create_time.isoformat() if rd.create_time else None,
        }
        for rd in raw_data_result.scalars().all()
    ]

    connections_result = await db.execute(
        select(DatabaseConnection)
        .where(DatabaseConnection.user_id == user_id, DatabaseConnection.deleted == 0)
        .order_by(DatabaseConnection.create_time.desc())
        .limit(20)
    )
    connections = [
        {
            "id": str(c.id),
            "name": c.name,
            "db_type": c.db_type,
            "host": c.host,
            "database": c.database,
            "create_time": c.create_time.isoformat() if c.create_time else None,
        }
        for c in connections_result.scalars().all()
    ]

    files_list_result = await db.execute(
        select(UploadedFile)
        .where(UploadedFile.user_id == user_id, UploadedFile.deleted == 0)
        .order_by(UploadedFile.create_time.desc())
        .limit(20)
    )
    files = [
        {
            "id": str(f.id),
            "original_name": f.original_name,
            "file_type": f.file_type,
            "file_size": f.file_size,
            "status": f.status,
            "create_time": f.create_time.isoformat() if f.create_time else None,
        }
        for f in files_list_result.scalars().all()
    ]

    return BaseResponse(
        success=True,
        code=200,
        msg="获取用户资源成功",
        data=UserResourceDetail(
            user=UserResponse.model_validate(user),
            resources=UserResourceStats(
                user_id=user.id,
                username=user.username,
                nickname=user.nickname,
                sessions_count=sessions_count,
                messages_count=messages_count,
                raw_data_count=raw_data_count,
                connections_count=connections_count,
                files_count=files_count,
                total_file_size=total_file_size,
            ),
            sessions=sessions,
            raw_data=raw_data_list,
            connections=connections,
            files=files,
        ),
    )


# ==================== 批量删除接口 ====================


async def _cascade_delete_user(
    db: AsyncSession,
    user_id: uuid.UUID,
    username: str,
) -> CascadeDeleteResult:
    """
    级联删除用户及其所有关联资源

    删除顺序（考虑外键依赖）：
    1. 消息 (ChatMessage) - 依赖会话
    2. 会话-数据关联 (SessionRawData) - 依赖会话
    3. 会话 (AnalysisSession)
    4. 原始数据 (RawData) - 依赖文件和数据库连接
    5. 上传文件 (UploadedFile) - 需要清理 MinIO
    6. 数据库连接 (DatabaseConnection)
    7. 沙箱文件 - 调用沙箱 API
    8. 用户 (User)

    Args:
        db: 数据库会话
        user_id: 用户ID
        username: 用户名

    Returns:
        CascadeDeleteResult: 删除结果
    """
    from app.utils.tools import get_sandbox_client

    result = CascadeDeleteResult(
        user_id=user_id,
        username=username,
        deleted_sessions=0,
        deleted_messages=0,
        deleted_raw_data=0,
        deleted_connections=0,
        deleted_files=0,
        sandbox_cleaned=False,
        minio_files_deleted=0,
    )

    try:
        # 1. 获取用户的所有会话ID
        session_ids_result = await db.execute(
            select(AnalysisSession.id).where(
                AnalysisSession.user_id == user_id,
                AnalysisSession.deleted == 0,
            )
        )
        session_ids = [row[0] for row in session_ids_result.fetchall()]

        # 2. 删除消息（软删除）
        if session_ids:
            msg_update = await db.execute(
                update(ChatMessage)
                .where(ChatMessage.session_id.in_(session_ids), ChatMessage.deleted == 0)
                .values(deleted=1)
            )
            result.deleted_messages = msg_update.rowcount or 0  # type: ignore[attr-defined]

            # 删除会话-数据关联（软删除）
            await db.execute(
                update(SessionRawData)
                .where(SessionRawData.session_id.in_(session_ids), SessionRawData.deleted == 0)
                .values(deleted=1)
            )

        # 3. 删除会话（软删除）
        session_update = await db.execute(
            update(AnalysisSession)
            .where(AnalysisSession.user_id == user_id, AnalysisSession.deleted == 0)
            .values(deleted=1)
        )
        result.deleted_sessions = session_update.rowcount or 0  # type: ignore[attr-defined]

        # 4. 删除原始数据（软删除）
        rd_update = await db.execute(
            update(RawData).where(RawData.user_id == user_id, RawData.deleted == 0).values(deleted=1)
        )
        result.deleted_raw_data = rd_update.rowcount or 0  # type: ignore[attr-defined]

        # 5. 获取文件列表并从 MinIO 删除
        files_result = await db.execute(
            select(UploadedFile.object_key).where(
                UploadedFile.user_id == user_id,
                UploadedFile.deleted == 0,
            )
        )
        file_keys = [row[0] for row in files_result.fetchall()]

        for object_key in file_keys:
            try:
                await minio_client.delete_file(object_key)
                result.minio_files_deleted += 1
            except Exception as e:
                logger.warning(f"Failed to delete MinIO file {object_key}: {e}")

        # 6. 删除文件记录（软删除）
        file_update = await db.execute(
            update(UploadedFile).where(UploadedFile.user_id == user_id, UploadedFile.deleted == 0).values(deleted=1)
        )
        result.deleted_files = file_update.rowcount or 0  # type: ignore[attr-defined]

        # 7. 删除数据库连接（软删除）
        conn_update = await db.execute(
            update(DatabaseConnection)
            .where(DatabaseConnection.user_id == user_id, DatabaseConnection.deleted == 0)
            .values(deleted=1)
        )
        result.deleted_connections = conn_update.rowcount or 0  # type: ignore[attr-defined]

        # 8. 清理沙箱用户目录
        try:
            client = get_sandbox_client()
            sandbox_response = await client.post("/reset/user", params={"user_id": str(user_id)})
            sandbox_result = sandbox_response.json()
            result.sandbox_cleaned = sandbox_result.get("success", False)
            logger.info(f"Sandbox cleanup for user {user_id}: {sandbox_result}")
        except Exception as e:
            logger.warning(f"Failed to cleanup sandbox for user {user_id}: {e}")
            result.sandbox_cleaned = False

        # 9. 删除用户（软删除）
        await db.execute(update(User).where(User.id == user_id, User.deleted == 0).values(deleted=1))

        await db.commit()
        logger.info(f"Successfully cascade deleted user {username} ({user_id})")

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to cascade delete user {username} ({user_id}): {e}")
        raise

    return result


@router.post("/users/batch-delete", response_model=BaseResponse[BatchDeleteResult])
async def batch_delete_users(
    request: BatchDeleteRequest,
    current_user: CurrentSuperUser,
    db: DBSession,
):
    """
    批量删除用户（级联删除所有关联资源）

    删除内容包括：
    - 用户的所有会话和消息
    - 用户的所有原始数据对象
    - 用户的所有数据库连接
    - 用户的所有上传文件（包括 MinIO 存储）
    - 用户的沙箱工作目录

    注意：
    - 不能删除当前登录的管理员账号
    - 删除操作为软删除，可以通过数据库恢复

    需要超级管理员权限
    """
    result = BatchDeleteResult(
        success_count=0,
        failed_count=0,
        skipped_count=0,
        details=[],
    )

    for user_id in request.user_ids:
        # 不能删除自己
        if user_id == current_user.id:
            result.skipped_count += 1
            result.details.append(
                {
                    "user_id": str(user_id),
                    "status": "skipped",
                    "reason": "不能删除当前登录的管理员账号",
                }
            )
            continue

        try:
            # 获取用户信息
            user_service = UserService(db)
            user = await user_service.get_user(user_id)

            # 执行级联删除
            delete_result = await _cascade_delete_user(db, user_id, user.username)

            result.success_count += 1
            result.details.append(
                {
                    "user_id": str(user_id),
                    "username": delete_result.username,
                    "status": "success",
                    "deleted_resources": {
                        "sessions": delete_result.deleted_sessions,
                        "messages": delete_result.deleted_messages,
                        "raw_data": delete_result.deleted_raw_data,
                        "connections": delete_result.deleted_connections,
                        "files": delete_result.deleted_files,
                        "minio_files": delete_result.minio_files_deleted,
                        "sandbox_cleaned": delete_result.sandbox_cleaned,
                    },
                }
            )

        except Exception as e:
            result.failed_count += 1
            result.details.append(
                {
                    "user_id": str(user_id),
                    "status": "failed",
                    "reason": str(e),
                }
            )
            logger.error(f"Failed to delete user {user_id}: {e}")

    return BaseResponse(
        success=True,
        code=200,
        msg=f"批量删除完成: 成功 {result.success_count}, 失败 {result.failed_count}, 跳过 {result.skipped_count}",
        data=result,
    )


@router.delete("/users/{user_id}/cascade", response_model=BaseResponse[CascadeDeleteResult])
async def cascade_delete_user(
    user_id: uuid.UUID,
    current_user: CurrentSuperUser,
    db: DBSession,
):
    """
    级联删除单个用户及其所有关联资源

    删除内容包括：
    - 用户的所有会话和消息
    - 用户的所有原始数据对象
    - 用户的所有数据库连接
    - 用户的所有上传文件（包括 MinIO 存储）
    - 用户的沙箱工作目录

    需要超级管理员权限
    """
    # 不能删除自己
    if user_id == current_user.id:
        return BaseResponse(success=False, code=400, msg="不能删除当前登录的管理员账号", data=None)

    # 获取用户信息
    user_service = UserService(db)
    user = await user_service.get_user(user_id)

    # 执行级联删除
    delete_result = await _cascade_delete_user(db, user_id, user.username)

    return BaseResponse(
        success=True,
        code=200,
        msg=f"用户 {user.username} 及其所有资源已删除",
        data=delete_result,
    )
