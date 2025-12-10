"""
用户管理API路由

提供用户的CRUD操作和认证相关接口
"""

import uuid

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentSuperUser, CurrentUser, DBSession
from app.models.base import BasePageQuery, BaseResponse, PageResponse, Token
from app.schemas.user import (
    LoginRequest,
    PasswordChange,
    RefreshTokenRequest,
    UserCreate,
    UserListQuery,
    UserResponse,
    UserUpdate,
)
from app.services.auth import AuthService
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])
auth_router = APIRouter(prefix="/auth", tags=["auth"])


# ==================== 认证相关接口 ====================


@auth_router.post("/login", response_model=BaseResponse[Token])
async def login(login_data: LoginRequest, db: DBSession):
    """用户登录"""
    auth_service = AuthService(db)
    token = await auth_service.login(login_data)
    return BaseResponse(success=True, code=200, msg="登录成功", data=token)


@auth_router.post("/refresh", response_model=BaseResponse[Token])
async def refresh_token(token_data: RefreshTokenRequest, db: DBSession):
    """刷新访问令牌"""
    auth_service = AuthService(db)
    token = await auth_service.refresh_token(token_data.refresh_token)
    return BaseResponse(success=True, code=200, msg="令牌刷新成功", data=token)


@auth_router.post("/register", response_model=BaseResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: DBSession):
    """用户注册"""
    auth_service = AuthService(db)
    user = await auth_service.register(user_data)
    return BaseResponse(success=True, code=201, msg="注册成功", data=UserResponse.model_validate(user))


@auth_router.get("/me", response_model=BaseResponse[UserResponse])
async def get_current_user_info(current_user: CurrentUser):
    """获取当前登录用户信息"""
    return BaseResponse(success=True, code=200, msg="获取用户信息成功", data=UserResponse.model_validate(current_user))


@auth_router.put("/me", response_model=BaseResponse[UserResponse])
async def update_current_user(user_data: UserUpdate, current_user: CurrentUser, db: DBSession):
    """更新当前登录用户信息"""
    user_service = UserService(db)
    user = await user_service.update_current_user(current_user, user_data)
    return BaseResponse(success=True, code=200, msg="更新用户信息成功", data=UserResponse.model_validate(user))


@auth_router.post("/change-password", response_model=BaseResponse[None])
async def change_password(password_data: PasswordChange, current_user: CurrentUser, db: DBSession):
    """修改密码"""
    auth_service = AuthService(db)
    await auth_service.change_password(current_user, password_data.old_password, password_data.new_password)
    return BaseResponse(success=True, code=200, msg="密码修改成功", data=None)


# ==================== 用户管理接口（需要超级管理员权限） ====================


@router.get("", response_model=BaseResponse[PageResponse[UserResponse]])
async def get_users(
    db: DBSession,
    _current_user: CurrentSuperUser,
    page_query: BasePageQuery = Depends(),
    query_params: UserListQuery = Depends(),
):
    """获取用户列表（分页）- 需要超级管理员权限"""
    user_service = UserService(db)
    users, total = await user_service.get_users(
        query_params=query_params,
        page_num=page_query.page_num,
        page_size=page_query.page_size,
    )
    user_list = [UserResponse.model_validate(user) for user in users]
    return BaseResponse(
        success=True,
        code=200,
        msg="获取用户列表成功",
        data=PageResponse(page_num=page_query.page_num, page_size=page_query.page_size, total=total, items=user_list),
    )


@router.get("/{user_id}", response_model=BaseResponse[UserResponse])
async def get_user(user_id: uuid.UUID, _current_user: CurrentSuperUser, db: DBSession):
    """获取单个用户详情 - 需要超级管理员权限"""
    user_service = UserService(db)
    user = await user_service.get_user(user_id)
    return BaseResponse(success=True, code=200, msg="获取用户成功", data=UserResponse.model_validate(user))


@router.post("", response_model=BaseResponse[UserResponse], status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, _current_user: CurrentSuperUser, db: DBSession):
    """创建新用户 - 需要超级管理员权限"""
    user_service = UserService(db)
    user = await user_service.create_user(user_data)
    return BaseResponse(success=True, code=201, msg="创建用户成功", data=UserResponse.model_validate(user))


@router.put("/{user_id}", response_model=BaseResponse[UserResponse])
async def update_user(user_id: uuid.UUID, user_data: UserUpdate, _current_user: CurrentSuperUser, db: DBSession):
    """更新用户信息 - 需要超级管理员权限"""
    user_service = UserService(db)
    user = await user_service.update_user(user_id, user_data)
    return BaseResponse(success=True, code=200, msg="更新用户成功", data=UserResponse.model_validate(user))


@router.delete("/{user_id}", response_model=BaseResponse[None])
async def delete_user(user_id: uuid.UUID, _current_user: CurrentSuperUser, db: DBSession):
    """删除用户（逻辑删除）- 需要超级管理员权限"""
    user_service = UserService(db)
    await user_service.delete_user(user_id)
    return BaseResponse(success=True, code=200, msg="删除用户成功", data=None)
