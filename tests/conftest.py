"""
pytest 全局配置文件
定义全局 fixtures 和配置
"""

import os
from collections.abc import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.base import Base

try:
    from app.main import app
except (ImportError, AttributeError):
    from fastapi import FastAPI

    app = FastAPI()

# ============ 数据库配置 ============

# 使用 PostgreSQL 进行测试（模型使用了 PostgreSQL 特定类型如 ARRAY, JSONB）
# 测试数据库应与生产数据库分开
SQLALCHEMY_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres123@localhost:5432/data_agent_test",
)

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,  # 关闭SQL日志以提高测试速度
)

# 注意：由于异步测试配置复杂，建议使用 scripts/test_api.py 进行 API 测试

# ============ Pytest 配置 ============

# 配置 pytest-asyncio
pytest_plugins = ("pytest_asyncio",)


def pytest_configure(config):
    """pytest 启动时的配置"""
    # 设置测试环境变量
    os.environ["TESTING"] = "1"
    os.environ["DATABASE_URL"] = SQLALCHEMY_DATABASE_URL

    # 禁用loguru日志以提高测试速度
    from loguru import logger

    logger.disable("")


# ============ 数据库 Fixtures ============


@pytest.fixture(scope="session")
def event_loop():
    """创建一个事件循环用于整个测试会话"""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def db_engine():
    """
    创建测试数据库引擎（整个测试会话共享）
    """
    return engine


@pytest.fixture(scope="session", autouse=True)
async def setup_db(db_engine):
    """
    在测试会话开始时创建数据库表，结束时清理
    """
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await db_engine.dispose()


@pytest.fixture(scope="class")
async def db(db_engine):
    """
    创建数据库会话（类级别共享，每个测试后清理数据）
    性能优化：使用TRUNCATE代替重建表
    """
    AsyncSessionLocal = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with AsyncSessionLocal() as session:
        yield session

        # 测试后清理数据（保留表结构）
        try:
            from sqlalchemy import text

            # 按照外键依赖顺序删除
            await session.execute(text("DELETE FROM task_recommendations"))
            await session.execute(text("DELETE FROM chat_messages"))
            await session.execute(text("DELETE FROM analysis_sessions"))
            await session.execute(text("DELETE FROM data_sources"))
            await session.execute(text("DELETE FROM uploaded_files"))
            await session.execute(text("DELETE FROM users"))
            await session.commit()
        except Exception:
            await session.rollback()


@pytest.fixture(scope="class", autouse=True)
async def override_get_db(db: AsyncSession):
    """
    覆盖应用的数据库依赖（类级别自动应用）
    """

    async def _override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.clear()


# ============ 客户端 Fixtures ============


@pytest.fixture(scope="class")
def client(override_get_db) -> Generator[TestClient, None, None]:
    """
    同步测试客户端（类级别共享）
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(scope="class")
async def async_client(override_get_db) -> AsyncGenerator[AsyncClient, None]:
    """
    异步测试客户端（类级别共享）
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


# ============ 认证 Fixtures ============

# 缓存superuser token以加速测试
_cached_superuser_token: str | None = None
_cached_hashed_password: str | None = None


@pytest.fixture(scope="session")
def cached_admin_password_hash():
    """缓存管理员密码哈希以加速测试"""
    from app.core.security import get_password_hash

    global _cached_hashed_password
    if _cached_hashed_password is None:
        _cached_hashed_password = get_password_hash("admin123")
    return _cached_hashed_password


@pytest.fixture(scope="class")
async def superuser_token(client: TestClient, db: AsyncSession, cached_admin_password_hash: str) -> str:
    """
    创建超级管理员并返回其访问令牌（类级别共享，使用缓存的密码哈希）
    """
    from sqlalchemy import select

    from app.models.user import User

    # 检查是否已存在admin用户
    result = await db.execute(select(User).where(User.username == "admin", User.deleted == 0))
    existing_user = result.scalar_one_or_none()

    if not existing_user:
        # 创建超级管理员用户（使用缓存的密码哈希）
        superuser = User(
            username="admin",
            email="admin@example.com",
            nickname="Admin",
            hashed_password=cached_admin_password_hash,
            is_active=True,
            is_superuser=True,
        )
        db.add(superuser)
        await db.commit()
        await db.refresh(superuser)

    # 登录获取token（使用全局缓存）
    global _cached_superuser_token
    if _cached_superuser_token is None:
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        _cached_superuser_token = response.json()["data"]["access_token"]

    return _cached_superuser_token


@pytest.fixture(scope="class")
def auth_headers(superuser_token: str) -> dict[str, str]:
    """
    返回包含认证token的headers（类级别共享）
    """
    return {"Authorization": f"Bearer {superuser_token}"}
