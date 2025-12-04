"""
pytest 全局配置文件
定义全局 fixtures 和配置
"""

import asyncio
import os
from collections.abc import Generator

# 必须在导入任何 app 模块之前设置环境变量
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres123@localhost:5432/data_agent_test",
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# 现在可以安全导入 app 模块
from app.models.base import Base

try:
    from app.main import app
except (ImportError, AttributeError):
    from fastapi import FastAPI

    app = FastAPI()

# ============ 数据库配置 ============

# 使用 PostgreSQL 进行测试（模型使用了 PostgreSQL 特定类型如 ARRAY, JSONB）
SQLALCHEMY_DATABASE_URL = os.environ["DATABASE_URL"]

# 创建测试引擎
test_engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
)

TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ============ Pytest 配置 ============


def pytest_configure(config):
    """pytest 启动时的配置"""
    # 禁用loguru日志以提高测试速度
    from loguru import logger

    logger.disable("")


# ============ 事件循环 Fixture ============


@pytest.fixture(scope="session")
def event_loop():
    """创建一个事件循环用于整个测试会话"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


# ============ 数据库 Fixtures ============


@pytest.fixture(scope="session")
def _setup_db(event_loop):
    """
    在测试会话开始时创建数据库表
    """

    async def _create_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    event_loop.run_until_complete(_create_tables())
    yield

    async def _drop_tables():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await test_engine.dispose()

    event_loop.run_until_complete(_drop_tables())


@pytest.fixture(scope="function")
def db_session(_setup_db, event_loop) -> Generator[AsyncSession, None, None]:
    """
    创建数据库会话（每个测试函数独立）
    """

    async def _get_session():
        async with TestingSessionLocal() as session:
            return session

    session = event_loop.run_until_complete(_get_session())
    yield session

    # 清理数据
    async def _cleanup():
        try:
            # 使用 TRUNCATE CASCADE 更高效地清理数据
            await session.execute(text("TRUNCATE task_recommendations CASCADE"))
            await session.execute(text("TRUNCATE chat_messages CASCADE"))
            await session.execute(text("TRUNCATE analysis_sessions CASCADE"))
            await session.execute(text("TRUNCATE data_sources CASCADE"))
            await session.execute(text("TRUNCATE uploaded_files CASCADE"))
            await session.execute(text("TRUNCATE users CASCADE"))
            await session.commit()
        except Exception:
            await session.rollback()
        finally:
            await session.close()

    event_loop.run_until_complete(_cleanup())


# ============ 客户端 Fixtures ============


@pytest.fixture(scope="function")
def client(_setup_db) -> Generator[TestClient, None, None]:
    """
    同步测试客户端 - 使用应用程序自己的数据库连接
    """
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


# ============ 认证 Fixtures ============

# 缓存密码哈希以加速测试
_cached_hashed_password: str | None = None


@pytest.fixture(scope="session")
def cached_admin_password_hash():
    """缓存管理员密码哈希以加速测试"""
    from app.core.security import get_password_hash

    global _cached_hashed_password
    if _cached_hashed_password is None:
        _cached_hashed_password = get_password_hash("admin123")
    return _cached_hashed_password


@pytest.fixture(scope="function")
def superuser_token(
    client: TestClient,
    cached_admin_password_hash: str,
    event_loop,
) -> str:
    """
    创建超级管理员并返回其访问令牌
    """
    from sqlalchemy import select

    from app.models.user import User

    async def _create_admin():
        async with TestingSessionLocal() as session:
            # 检查是否已存在admin用户
            result = await session.execute(
                select(User).where(User.username == "admin", User.deleted == 0)
            )
            existing_user = result.scalar_one_or_none()

            if not existing_user:
                superuser = User(
                    username="admin",
                    email="admin@example.com",
                    nickname="Admin",
                    hashed_password=cached_admin_password_hash,
                    is_active=True,
                    is_superuser=True,
                )
                session.add(superuser)
                await session.commit()

    event_loop.run_until_complete(_create_admin())

    # 登录获取token
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    json_data = response.json()
    if not json_data.get("success") or not json_data.get("data"):
        raise RuntimeError(
            f"Login failed: status={response.status_code}, response={json_data}"
        )
    return json_data["data"]["access_token"]


@pytest.fixture(scope="function")
def auth_headers(superuser_token: str) -> dict[str, str]:
    """
    返回包含认证token的headers
    """
    return {"Authorization": f"Bearer {superuser_token}"}
