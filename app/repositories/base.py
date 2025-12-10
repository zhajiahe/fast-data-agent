"""
Repository 基类

提供通用的 CRUD 操作
"""

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base


class BaseRepository[ModelType: Base]:
    """通用 Repository 基类"""

    def __init__(self, model: type[ModelType], db: AsyncSession):
        """
        初始化 Repository

        Args:
            model: SQLAlchemy 模型类
            db: 数据库会话
        """
        self.model = model
        self.db = db

    async def get_by_id(self, id: uuid.UUID) -> ModelType | None:
        """
        根据 ID 获取单个记录

        Args:
            id: 记录 ID

        Returns:
            模型实例或 None
        """
        query = select(self.model).where(self.model.id == id)  # type: ignore[attr-defined]

        # 如果模型有 deleted 字段，过滤已删除记录
        if hasattr(self.model, "deleted"):
            query = query.where(self.model.deleted == 0)  # type: ignore[attr-defined]

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> list[ModelType]:
        """
        获取所有记录（支持分页和过滤）

        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            filters: 过滤条件

        Returns:
            模型实例列表
        """
        query = select(self.model)

        # 如果模型有 deleted 字段，过滤已删除记录
        if hasattr(self.model, "deleted"):
            query = query.where(self.model.deleted == 0)  # type: ignore[attr-defined]

        # 应用过滤条件
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)

        # 按创建时间倒序排列（如果有该字段）
        if hasattr(self.model, "create_time"):
            query = query.order_by(self.model.create_time.desc())  # type: ignore[attr-defined]

        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """
        统计记录数

        Args:
            filters: 过滤条件

        Returns:
            记录数
        """
        query = select(func.count()).select_from(self.model)

        # 如果模型有 deleted 字段，过滤已删除记录
        if hasattr(self.model, "deleted"):
            query = query.where(self.model.deleted == 0)  # type: ignore[attr-defined]

        # 应用过滤条件
        if filters:
            for field, value in filters.items():
                if hasattr(self.model, field) and value is not None:
                    query = query.where(getattr(self.model, field) == value)

        result = await self.db.execute(query)
        return result.scalar() or 0

    async def create(self, obj_in: dict[str, Any]) -> ModelType:
        """
        创建新记录

        Args:
            obj_in: 创建数据

        Returns:
            创建的模型实例
        """
        db_obj = self.model(**obj_in)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: ModelType,
        obj_in: dict[str, Any],
    ) -> ModelType:
        """
        更新记录

        Args:
            db_obj: 要更新的模型实例
            obj_in: 更新数据

        Returns:
            更新后的模型实例
        """
        for field, value in obj_in.items():
            if hasattr(db_obj, field) and value is not None:
                setattr(db_obj, field, value)

        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def delete(self, id: uuid.UUID, *, soft_delete: bool = True) -> bool:
        """
        删除记录

        Args:
            id: 记录 ID
            soft_delete: 是否软删除

        Returns:
            是否删除成功
        """
        db_obj = await self.get_by_id(id)
        if not db_obj:
            return False

        if soft_delete and hasattr(db_obj, "deleted"):
            db_obj.deleted = 1
            await self.db.flush()
        else:
            await self.db.delete(db_obj)
            await self.db.flush()

        return True
