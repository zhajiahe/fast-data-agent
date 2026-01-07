"""
用户管理 API 测试

测试 /api/v1/users 端点（需要超级管理员权限）：
- 用户 CRUD 操作
- 用户列表分页
"""

import uuid
from typing import Any

import pytest
from starlette.testclient import TestClient


class TestUsersFixtures:
    """用户管理测试辅助"""

    @pytest.fixture(scope="function")
    def admin_headers(self, client: TestClient) -> dict[str, str]:
        """管理员认证头"""
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": "admin", "password": "admin123"},
        )
        if login_response.status_code != 200:
            pytest.skip("管理员账户不存在或密码错误")

        token = login_response.json()["data"]["access_token"]
        return {"Authorization": f"Bearer {token}"}


class TestUsersList(TestUsersFixtures):
    """用户列表测试"""

    def test_list_users_as_admin(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试管理员获取用户列表"""
        response = client.get("/api/v1/users", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert "page_num" in data["data"]
        assert "page_size" in data["data"]

    def test_list_users_pagination(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试用户列表分页"""
        response = client.get(
            "/api/v1/users",
            headers=admin_headers,
            params={"page_num": 1, "page_size": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["page_num"] == 1
        assert data["data"]["page_size"] == 5

    def test_list_users_as_user(self, client: TestClient, auth_headers: dict):
        """测试普通用户无权访问用户列表"""
        response = client.get("/api/v1/users", headers=auth_headers)

        assert response.status_code == 403

    def test_list_users_unauthorized(self, client: TestClient):
        """测试未认证访问用户列表"""
        response = client.get("/api/v1/users")

        assert response.status_code in (401, 403)


class TestUserCRUD(TestUsersFixtures):
    """用户 CRUD 测试"""

    def test_create_user(self, client: TestClient, admin_headers: dict[str, str]):
        """测试管理员创建用户"""
        uid = uuid.uuid4().hex[:8]
        response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "username": f"created_user_{uid}",
                "email": f"created_{uid}@example.com",
                "nickname": "Created User",
                "password": "testpass123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == f"created_user_{uid}"

        # 清理
        user_id = data["data"]["id"]
        client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)

    def test_create_user_duplicate_username(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试创建重复用户名"""
        response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "username": "admin",  # 已存在的用户名
                "email": "another@example.com",
                "nickname": "Another",
                "password": "testpass123",
            },
        )

        assert response.status_code in (400, 409)

    def test_create_user_as_user(self, client: TestClient, auth_headers: dict):
        """测试普通用户无权创建用户"""
        uid = uuid.uuid4().hex[:8]
        response = client.post(
            "/api/v1/users",
            headers=auth_headers,
            json={
                "username": f"user_{uid}",
                "email": f"user_{uid}@example.com",
                "nickname": "User",
                "password": "testpass123",
            },
        )

        assert response.status_code == 403

    def test_get_user(
        self, client: TestClient, admin_headers: dict[str, str], test_user_data: dict[str, Any]
    ):
        """测试管理员获取用户详情"""
        user_id = test_user_data["id"]
        response = client.get(
            f"/api/v1/users/{user_id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == user_id

    def test_get_user_not_found(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试获取不存在的用户"""
        response = client.get(
            "/api/v1/users/00000000-0000-0000-0000-000000099999",
            headers=admin_headers,
        )

        assert response.status_code == 404

    def test_update_user(self, client: TestClient, admin_headers: dict[str, str]):
        """测试管理员更新用户"""
        # 先创建一个用户
        uid = uuid.uuid4().hex[:8]
        create_response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "username": f"update_test_{uid}",
                "email": f"update_{uid}@example.com",
                "nickname": "Update Test",
                "password": "testpass123",
            },
        )
        user_id = create_response.json()["data"]["id"]

        # 更新用户
        response = client.put(
            f"/api/v1/users/{user_id}",
            headers=admin_headers,
            json={"nickname": "Updated Nickname"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["nickname"] == "Updated Nickname"

        # 清理
        client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)

    def test_update_user_not_found(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试更新不存在的用户"""
        response = client.put(
            "/api/v1/users/00000000-0000-0000-0000-000000099999",
            headers=admin_headers,
            json={"nickname": "Updated"},
        )

        assert response.status_code == 404

    def test_delete_user(self, client: TestClient, admin_headers: dict[str, str]):
        """测试管理员删除用户"""
        # 先创建一个用户
        uid = uuid.uuid4().hex[:8]
        create_response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "username": f"delete_test_{uid}",
                "email": f"delete_{uid}@example.com",
                "nickname": "Delete Test",
                "password": "testpass123",
            },
        )
        user_id = create_response.json()["data"]["id"]

        # 删除用户
        response = client.delete(
            f"/api/v1/users/{user_id}",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证已删除
        get_response = client.get(
            f"/api/v1/users/{user_id}",
            headers=admin_headers,
        )
        assert get_response.status_code == 404

    def test_delete_user_not_found(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试删除不存在的用户"""
        response = client.delete(
            "/api/v1/users/00000000-0000-0000-0000-000000099999",
            headers=admin_headers,
        )

        assert response.status_code == 404

    def test_delete_user_as_user(self, client: TestClient, auth_headers: dict):
        """测试普通用户无权删除用户"""
        response = client.delete(
            "/api/v1/users/00000000-0000-0000-0000-000000000001",
            headers=auth_headers,
        )

        assert response.status_code == 403

