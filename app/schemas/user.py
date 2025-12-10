"""
用户相关的 Pydantic Schema

用于 API 请求和响应的数据验证和序列化
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """用户基础字段"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    nickname: str = Field(..., min_length=1, max_length=50, description="昵称")


class UserCreate(UserBase):
    """创建用户请求"""

    password: str = Field(..., min_length=6, max_length=128, description="密码")
    is_active: bool = Field(default=True, description="是否激活")
    is_superuser: bool = Field(default=False, description="是否超级管理员")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证密码强度"""
        if len(v) < 6:
            raise ValueError("密码长度不能少于6位")
        return v


class UserUpdate(BaseModel):
    """更新用户请求"""

    email: EmailStr | None = Field(default=None, description="邮箱")
    nickname: str | None = Field(default=None, min_length=1, max_length=50, description="昵称")
    is_active: bool | None = Field(default=None, description="是否激活")
    is_superuser: bool | None = Field(default=None, description="是否超级管理员")


class UserResponse(UserBase):
    """用户响应"""

    id: uuid.UUID = Field(..., description="用户ID")
    is_active: bool = Field(..., description="是否激活")
    is_superuser: bool = Field(..., description="是否超级管理员")
    create_time: datetime | None = Field(default=None, description="创建时间")
    update_time: datetime | None = Field(default=None, description="更新时间")

    model_config = {"from_attributes": True}


class UserListQuery(BaseModel):
    """用户列表查询参数"""

    keyword: str | None = Field(default=None, description="搜索关键词（用户名、邮箱、昵称）")
    is_active: bool | None = Field(default=None, description="是否激活")
    is_superuser: bool | None = Field(default=None, description="是否超级管理员")


class PasswordChange(BaseModel):
    """修改密码请求"""

    old_password: str = Field(..., min_length=6, max_length=128, description="旧密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """验证新密码"""
        if len(v) < 6:
            raise ValueError("密码长度不能少于6位")
        return v


class LoginRequest(BaseModel):
    """登录请求"""

    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    password: str = Field(..., min_length=6, max_length=128, description="密码")


class RefreshTokenRequest(BaseModel):
    """刷新令牌请求"""

    refresh_token: str = Field(..., description="刷新令牌")
