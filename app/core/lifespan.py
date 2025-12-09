"""
应用生命周期管理

管理应用启动和关闭时的资源初始化和清理
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.core.database import close_db, init_db
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
