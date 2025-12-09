"""
Pytest 配置和共享 fixtures

提供测试所需的 HTTP 客户端、认证用户等。
"""

import uuid
from collections.abc import Generator
from typing import Any

import pytest
from starlette.testclient import TestClient

from app.main import app


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """
    提供 HTTP 测试客户端 fixture（会话级别）

    整个测试会话使用同一个客户端，避免重复启动应用
    """
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture(scope="function")
def unique_user() -> dict[str, str]:
    """
    生成唯一的测试用户信息
    """
    uid = uuid.uuid4().hex[:8]
    return {
        "username": f"testuser_{uid}",
        "email": f"testuser_{uid}@example.com",
        "nickname": f"Test User {uid}",
        "password": "testpass123",
    }


@pytest.fixture(scope="function")
def auth_headers(client: TestClient, unique_user: dict[str, str]) -> dict[str, str]:
    """
    提供认证头 fixture

    自动注册和登录测试用户，返回带有 access_token 的请求头
    """
    # 注册测试用户
    client.post("/api/v1/auth/register", json=unique_user)

    # 登录获取 token
    login_response = client.post(
        "/api/v1/auth/login",
        json={"username": unique_user["username"], "password": unique_user["password"]},
    )

    if login_response.status_code != 200:
        pytest.fail(f"登录失败: {login_response.json()}")

    data = login_response.json()
    access_token = data.get("data", {}).get("access_token", "")

    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture(scope="function")
def test_user_data(auth_headers: dict[str, str], client: TestClient) -> dict[str, Any]:
    """
    获取当前测试用户信息
    """
    response = client.get("/api/v1/auth/me", headers=auth_headers)
    return response.json().get("data", {})


# ==================== 资源创建 Fixtures ====================


@pytest.fixture(scope="function")
def test_connection(
    client: TestClient, auth_headers: dict[str, str]
) -> Generator[dict[str, Any], None, None]:
    """
    创建测试用的数据库连接
    """
    response = client.post(
        "/api/v1/database-connections",
        headers=auth_headers,
        json={
            "name": "Test Connection",
            "description": "测试数据库连接",
            "config": {
                "db_type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database": "data_agent",
                "username": "postgres",
                "password": "postgres",
            },
        },
    )

    data = response.json().get("data", {})
    yield data

    # 清理：删除连接
    if data.get("id"):
        client.delete(
            f"/api/v1/database-connections/{data['id']}",
            headers=auth_headers,
        )


@pytest.fixture(scope="function")
def test_file(
    client: TestClient, auth_headers: dict[str, str]
) -> Generator[dict[str, Any], None, None]:
    """
    创建测试用的上传文件
    """
    csv_content = b"id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,300"
    files = {"file": ("test_data.csv", csv_content, "text/csv")}

    response = client.post(
        "/api/v1/files/upload",
        headers=auth_headers,
        files=files,
    )

    data = response.json().get("data", {})
    yield data

    # 清理：删除文件
    if data.get("id"):
        client.delete(
            f"/api/v1/files/{data['id']}",
            headers=auth_headers,
        )


@pytest.fixture(scope="function")
def test_raw_data(
    client: TestClient, auth_headers: dict[str, str], test_file: dict[str, Any]
) -> Generator[dict[str, Any], None, None]:
    """
    创建测试用的原始数据（文件类型）
    """
    response = client.post(
        "/api/v1/raw-data",
        headers=auth_headers,
        json={
            "name": "test_csv_raw",
            "description": "测试 CSV 原始数据",
            "raw_type": "file",
            "file_config": {"file_id": test_file["id"]},
        },
    )

    data = response.json().get("data", {})
    yield data

    # 清理：删除原始数据
    if data.get("id"):
        client.delete(
            f"/api/v1/raw-data/{data['id']}",
            headers=auth_headers,
        )


@pytest.fixture(scope="function")
def test_data_source(
    client: TestClient, auth_headers: dict[str, str], test_raw_data: dict[str, Any]
) -> Generator[dict[str, Any], None, None]:
    """
    创建测试用的数据源
    """
    response = client.post(
        "/api/v1/data-sources",
        headers=auth_headers,
        json={
            "name": "Test Data Source",
            "description": "测试数据源",
            "category": "fact",
            "target_fields": [
                {"name": "id", "data_type": "integer", "description": "ID"},
                {"name": "name", "data_type": "string", "description": "名称"},
                {"name": "value", "data_type": "integer", "description": "值"},
            ],
            "raw_mappings": [
                {
                    "raw_data_id": test_raw_data["id"],
                    "mappings": {"id": "id", "name": "name", "value": "value"},
                    "priority": 0,
                    "is_enabled": True,
                }
            ],
        },
    )

    data = response.json().get("data", {})
    yield data

    # 清理：删除数据源
    if data.get("id"):
        client.delete(
            f"/api/v1/data-sources/{data['id']}",
            headers=auth_headers,
        )


@pytest.fixture(scope="function")
def test_session(
    client: TestClient, auth_headers: dict[str, str], test_data_source: dict[str, Any]
) -> Generator[dict[str, Any], None, None]:
    """
    创建测试用的会话（单数据源）
    """
    data_source_id = test_data_source.get("id")

    response = client.post(
        "/api/v1/sessions",
        headers=auth_headers,
        json={
            "name": "Test Session",
            "description": "测试会话",
            "data_source_id": data_source_id,  # 单个数据源
        },
    )

    data = response.json().get("data", {})
    yield data

    # 清理：删除会话
    if data.get("id"):
        client.delete(
            f"/api/v1/sessions/{data['id']}",
            headers=auth_headers,
        )
