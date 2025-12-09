"""
认证 API 测试

测试 /api/v1/auth 端点：
- 用户注册
- 用户登录
- 获取当前用户
- 更新当前用户
- 修改密码
- 刷新令牌
"""

import uuid

from starlette.testclient import TestClient


class TestAuthRegister:
    """用户注册测试"""

    def test_register_success(self, client: TestClient):
        """测试成功注册"""
        uid = uuid.uuid4().hex[:8]
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": f"newuser_{uid}",
                "email": f"newuser_{uid}@example.com",
                "nickname": "New User",
                "password": "newpass123",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == f"newuser_{uid}"

    def test_register_duplicate_username(
        self, client: TestClient, auth_headers: dict, unique_user: dict
    ):
        """测试重复用户名注册"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": unique_user["username"],  # 已存在的用户名
                "email": "another@example.com",
                "nickname": "Another",
                "password": "pass123",
            },
        )

        assert response.status_code in (400, 409)
        data = response.json()
        assert data["success"] is False

    def test_register_invalid_email(self, client: TestClient):
        """测试无效邮箱"""
        uid = uuid.uuid4().hex[:8]
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": f"validuser_{uid}",
                "email": "invalid-email",
                "nickname": "Valid",
                "password": "pass123",
            },
        )

        assert response.status_code == 422


class TestAuthLogin:
    """用户登录测试"""

    def test_login_success(self, client: TestClient, auth_headers: dict, unique_user: dict):
        """测试成功登录"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": unique_user["username"], "password": unique_user["password"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]

    def test_login_wrong_password(
        self, client: TestClient, auth_headers: dict, unique_user: dict
    ):
        """测试密码错误"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": unique_user["username"], "password": "wrongpassword"},
        )

        assert response.status_code in (400, 401)
        data = response.json()
        assert data["success"] is False

    def test_login_nonexistent_user(self, client: TestClient):
        """测试不存在的用户"""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent_user_xyz", "password": "anypass"},
        )

        assert response.status_code in (400, 401, 404)
        data = response.json()
        assert data["success"] is False


class TestAuthMe:
    """当前用户信息测试"""

    def test_get_me_success(self, client: TestClient, auth_headers: dict, unique_user: dict):
        """测试获取当前用户信息"""
        response = client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == unique_user["username"]

    def test_get_me_unauthorized(self, client: TestClient):
        """测试未认证访问"""
        response = client.get("/api/v1/auth/me")

        # FastAPI/Starlette 返回 403 而不是 401
        assert response.status_code in (401, 403)

    def test_update_me_success(self, client: TestClient, auth_headers: dict):
        """测试更新当前用户信息"""
        response = client.put(
            "/api/v1/auth/me",
            headers=auth_headers,
            json={"nickname": "Updated Nickname"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["nickname"] == "Updated Nickname"


class TestAuthPassword:
    """密码修改测试"""

    def test_change_password_success(
        self, client: TestClient, auth_headers: dict, unique_user: dict
    ):
        """测试成功修改密码"""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": unique_user["password"],
                "new_password": "newpass456",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证新密码可以登录
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": unique_user["username"], "password": "newpass456"},
        )
        assert login_response.status_code == 200

    def test_change_password_wrong_old(self, client: TestClient, auth_headers: dict):
        """测试旧密码错误"""
        response = client.post(
            "/api/v1/auth/change-password",
            headers=auth_headers,
            json={
                "old_password": "wrongoldpass",
                "new_password": "newpass456",
            },
        )

        assert response.status_code in (400, 401)
        data = response.json()
        assert data["success"] is False


class TestAuthRefresh:
    """令牌刷新测试"""

    def test_refresh_token_success(
        self, client: TestClient, auth_headers: dict, unique_user: dict
    ):
        """测试刷新令牌"""
        # 先登录获取 refresh_token
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": unique_user["username"], "password": unique_user["password"]},
        )
        refresh_token = login_response.json()["data"]["refresh_token"]

        # 使用 refresh_token 获取新的 access_token
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]

    def test_refresh_token_invalid(self, client: TestClient):
        """测试无效的刷新令牌"""
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "invalid_token"},
        )

        assert response.status_code in (400, 401)
