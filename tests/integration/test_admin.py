"""
管理后台 API 测试

测试 /api/v1/admin 端点：
- 系统统计
- 用户资源查看
- 级联删除
"""

import uuid
from typing import Any

import pytest
from starlette.testclient import TestClient


class TestAdminFixtures:
    """管理员测试辅助"""

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


class TestSystemStats(TestAdminFixtures):
    """系统统计测试"""

    def test_get_stats_as_admin(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试管理员获取系统统计"""
        response = client.get("/api/v1/admin/stats", headers=admin_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        stats = data["data"]
        assert "total_users" in stats
        assert "active_users" in stats
        assert "total_sessions" in stats
        assert "total_messages" in stats
        assert "total_raw_data" in stats
        assert "total_connections" in stats
        assert "total_files" in stats
        assert "users_today" in stats
        assert "sessions_today" in stats
        assert "messages_today" in stats

    def test_get_stats_as_user(self, client: TestClient, auth_headers: dict):
        """测试普通用户无权访问系统统计"""
        response = client.get("/api/v1/admin/stats", headers=auth_headers)

        assert response.status_code == 403

    def test_get_stats_unauthorized(self, client: TestClient):
        """测试未认证访问系统统计"""
        response = client.get("/api/v1/admin/stats")

        assert response.status_code in (401, 403)


class TestUserResources(TestAdminFixtures):
    """用户资源测试"""

    def test_get_user_resources(
        self,
        client: TestClient,
        admin_headers: dict[str, str],
        test_user_data: dict[str, Any],
    ):
        """测试获取用户资源统计"""
        user_id = test_user_data["id"]
        response = client.get(
            f"/api/v1/admin/users/{user_id}/resources",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "user" in data["data"]
        assert "resources" in data["data"]

    def test_get_user_resources_not_found(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试获取不存在用户的资源统计"""
        response = client.get(
            "/api/v1/admin/users/00000000-0000-0000-0000-000000099999/resources",
            headers=admin_headers,
        )

        assert response.status_code == 404


class TestUserStatus(TestAdminFixtures):
    """用户状态管理测试"""

    def test_toggle_user_status(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试切换用户状态 (PATCH 方法)"""
        # 先创建一个测试用户
        uid = uuid.uuid4().hex[:8]
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "username": f"toggle_test_{uid}",
                "email": f"toggle_{uid}@example.com",
                "nickname": "Toggle Test",
                "password": "testpass123",
            },
        )
        user_id = register_response.json()["data"]["id"]

        # 禁用用户 (使用 PATCH 方法)
        response = client.patch(
            f"/api/v1/admin/users/{user_id}/toggle",
            headers=admin_headers,
            json={"is_active": False},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["is_active"] is False

        # 重新启用
        response = client.patch(
            f"/api/v1/admin/users/{user_id}/toggle",
            headers=admin_headers,
            json={"is_active": True},
        )

        assert response.status_code == 200
        assert response.json()["data"]["is_active"] is True

        # 清理
        client.delete(f"/api/v1/admin/users/{user_id}/cascade", headers=admin_headers)


class TestCascadeDelete(TestAdminFixtures):
    """级联删除测试"""

    def test_cascade_delete_user(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试级联删除用户"""
        # 创建一个测试用户
        uid = uuid.uuid4().hex[:8]
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "username": f"cascade_test_{uid}",
                "email": f"cascade_{uid}@example.com",
                "nickname": "Cascade Test",
                "password": "testpass123",
            },
        )
        user_id = register_response.json()["data"]["id"]

        # 级联删除
        response = client.delete(
            f"/api/v1/admin/users/{user_id}/cascade",
            headers=admin_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["user_id"] == user_id

        # 验证用户已删除 (通过 /users 端点)
        get_response = client.get(
            f"/api/v1/users/{user_id}",
            headers=admin_headers,
        )
        assert get_response.status_code == 404

    def test_cascade_delete_not_found(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试级联删除不存在的用户"""
        response = client.delete(
            "/api/v1/admin/users/00000000-0000-0000-0000-000000099999/cascade",
            headers=admin_headers,
        )

        assert response.status_code == 404


class TestBatchDelete(TestAdminFixtures):
    """批量删除测试"""

    def test_batch_delete_users(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试批量删除用户 (使用 POST 方法)"""
        # 创建两个测试用户
        user_ids = []
        for i in range(2):
            uid = uuid.uuid4().hex[:8]
            register_response = client.post(
                "/api/v1/auth/register",
                json={
                    "username": f"batch_test_{i}_{uid}",
                    "email": f"batch_{i}_{uid}@example.com",
                    "nickname": f"Batch Test {i}",
                    "password": "testpass123",
                },
            )
            user_ids.append(register_response.json()["data"]["id"])

        # 批量删除 (使用 POST 方法，不是 DELETE)
        response = client.post(
            "/api/v1/admin/users/batch-delete",
            headers=admin_headers,
            json={"user_ids": user_ids},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["success_count"] == 2

    def test_batch_delete_empty(
        self, client: TestClient, admin_headers: dict[str, str]
    ):
        """测试空列表批量删除"""
        response = client.post(
            "/api/v1/admin/users/batch-delete",
            headers=admin_headers,
            json={"user_ids": []},
        )

        # 空列表应该返回验证错误
        assert response.status_code == 422

