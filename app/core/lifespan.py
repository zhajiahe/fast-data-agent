"""
应用生命周期管理

管理应用启动和关闭时的资源初始化和清理
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.core.config import settings
from app.core.database import AsyncSessionLocal, close_db, init_db
from app.core.security import get_password_hash
from app.repositories.user import UserRepository
from app.utils.tools import SandboxHttpClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理器

    启动时:
    - 初始化数据库连接
    - 创建数据库表（开发环境）

    关闭时:
    - 关闭数据库连接
    - 清理资源
    """
    # 启动时
    logger.info("🚀 应用启动中...")

    try:
        # 初始化数据库
        await init_db()
        logger.info("✅ 数据库初始化成功")

        # 确保默认超级管理员存在（仅在没有超级管理员时创建）
        await _ensure_default_superuser()
    except Exception as e:
        logger.error(f"❌ 数据库初始化失败: {e}")
        raise

    logger.info("✅ 应用启动完成")

    yield

    # 关闭时
    logger.info("🛑 应用关闭中...")

    try:
        await close_db()
        logger.info("✅ 数据库连接已关闭")
        await SandboxHttpClient.close()
        logger.info("✅ 沙盒 HTTP 连接池已关闭")
    except Exception as e:
        logger.error(f"❌ 数据库关闭失败: {e}")

    logger.info("✅ 应用已关闭")


async def _ensure_default_superuser() -> None:
    """
    如果系统中不存在超级管理员，则创建默认超级管理员。

    通过配置 DEFAULT_ADMIN_* 提供默认凭证，避免首次运行无法登录。
    """
    async with AsyncSessionLocal() as db:
        repo = UserRepository(db)

        # 已存在超级管理员则跳过
        superuser_count = await repo.count({"is_superuser": True})
        if superuser_count > 0:
            logger.info("🔒 已存在超级管理员，跳过默认账户创建")
            return

        # 避免与已存在的普通账号冲突
        if await repo.username_exists(settings.DEFAULT_ADMIN_USERNAME):
            logger.warning(
                "⚠️ 检测到用户名与默认管理员相同的账户，但无超级管理员；请手动授予权限或调整 DEFAULT_ADMIN_USERNAME"
            )
            return
        if await repo.email_exists(settings.DEFAULT_ADMIN_EMAIL):
            logger.warning(
                "⚠️ 检测到邮箱与默认管理员相同的账户，但无超级管理员；请手动授予权限或调整 DEFAULT_ADMIN_EMAIL"
            )
            return

        admin = await repo.create(
            {
                "username": settings.DEFAULT_ADMIN_USERNAME,
                "email": settings.DEFAULT_ADMIN_EMAIL,
                "nickname": settings.DEFAULT_ADMIN_NICKNAME,
                "hashed_password": get_password_hash(settings.DEFAULT_ADMIN_PASSWORD),
                "is_active": True,
                "is_superuser": True,
            }
        )
        await db.commit()
        logger.info(
            "✅ 默认超级管理员已创建",
            username=admin.username,
            email=admin.email,
        )
