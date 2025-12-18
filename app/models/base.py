import uuid
from datetime import datetime

from pydantic import BaseModel, Field, computed_field
from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有SQLAlchemy模型的基类"""

    pass


class BaseTableMixin:
    """所有数据库表的Mixin，包含通用字段"""

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="主键ID")
    create_by: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="创建人")
    update_by: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="更新人")
    create_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), comment="创建时间"
    )
    update_time: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now(), comment="更新时间"
    )
    deleted: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="逻辑删除(0:未删除 1:已删除)")


class BaseResponse[T](BaseModel):
    """所有API响应的基类"""

    success: bool
    code: int  # 状态码 (200=成功, 其他=错误码)
    msg: str  # 用户友好的消息
    data: T | None = None
    err: T | None = None


class BasePageQuery(BaseModel):
    """分页查询基础数据"""

    page_num: int = Field(default=1, description="页码", ge=1)
    page_size: int = Field(default=10, description="数量", ge=1)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def offset(self) -> int:
        return (self.page_num - 1) * self.page_size

    @computed_field  # type: ignore[prop-decorator]
    @property
    def limit(self) -> int:
        return self.page_size


# 分页数据
class PageResponse[T](BaseModel):
    """分页响应基础数据"""

    page_num: int = Field(1, description="当前页码")
    page_size: int = Field(10, description="每页数量")
    total: int = Field(0, description="总记录数")
    items: list[T] = Field(default_factory=list, description="分页数据")


class Token(BaseModel):
    """Token基础数据"""

    id: uuid.UUID
    username: str
    nickname: str
    email: str
    is_active: bool
    is_superuser: bool
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(BaseModel):
    """TokenPayload基础数据"""

    exp: int  # 过期时间（Unix时间戳，必须为整数）
    sub: str | None = None
