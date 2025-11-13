"""
用户 API 集成测试

包含用户管理和认证相关的测试
"""

from fastapi import status
from fastapi.testclient import TestClient


class TestAuthAPI:
    """认证 API 测试类"""

    def test_register(self, client: TestClient):
        """测试用户注册"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "nickname": "New User",
                "password": "password123",
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == "newuser"
        assert data["data"]["is_active"] is True
        assert data["data"]["is_superuser"] is False

    def test_register_duplicate_username(self, client: TestClient):
        """测试注册重复用户名"""
        # 第一次注册
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test1@example.com",
                "nickname": "Test",
                "password": "password123",
            },
        )
        # 第二次注册相同用户名
        response = client.post(
            "/api/v1/auth/register",
            json={
                "username": "testuser",
                "email": "test2@example.com",
                "nickname": "Test",
                "password": "password123",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "用户名已存在" in response.json()["detail"]

    def test_login_success(self, client: TestClient):
        """测试登录成功"""
        # 先注册用户
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "loginuser",
                "email": "login@example.com",
                "nickname": "Login User",
                "password": "password123",
            },
        )
        # 登录
        response = client.post("/api/v1/auth/login?username=loginuser&password=password123")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert "access_token" in data["data"]
        assert "refresh_token" in data["data"]
        assert data["data"]["token_type"] == "bearer"

    def test_login_wrong_password(self, client: TestClient):
        """测试登录密码错误"""
        # 先注册用户
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "wrongpwduser",
                "email": "wrongpwd@example.com",
                "nickname": "Wrong Password User",
                "password": "correct_password",
            },
        )
        # 使用错误密码登录
        response = client.post("/api/v1/auth/login?username=wrongpwduser&password=wrong_password")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "用户名或密码错误" in response.json()["detail"]

    def test_login_user_not_exist(self, client: TestClient):
        """测试登录用户不存在"""
        response = client.post("/api/v1/auth/login?username=nonexistent&password=password123")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_current_user(self, client: TestClient):
        """测试获取当前用户信息"""
        # 注册并登录
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "currentuser",
                "email": "current@example.com",
                "nickname": "Current User",
                "password": "password123",
            },
        )
        login_response = client.post("/api/v1/auth/login?username=currentuser&password=password123")
        token = login_response.json()["data"]["access_token"]

        # 获取当前用户信息
        response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["username"] == "currentuser"

    def test_get_current_user_without_token(self, client: TestClient):
        """测试未登录获取当前用户信息"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_current_user(self, client: TestClient):
        """测试更新当前用户信息"""
        # 注册并登录
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "updateme",
                "email": "updateme@example.com",
                "nickname": "Update Me",
                "password": "password123",
            },
        )
        login_response = client.post("/api/v1/auth/login?username=updateme&password=password123")
        token = login_response.json()["data"]["access_token"]

        # 更新用户信息
        response = client.put(
            "/api/v1/auth/me",
            json={"nickname": "Updated Name", "email": "updated@example.com"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["nickname"] == "Updated Name"
        assert data["data"]["email"] == "updated@example.com"

    def test_change_password(self, client: TestClient):
        """测试修改密码"""
        # 注册并登录
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "changepwd",
                "email": "changepwd@example.com",
                "nickname": "Change Password",
                "password": "old_password",
            },
        )
        login_response = client.post("/api/v1/auth/login?username=changepwd&password=old_password")
        token = login_response.json()["data"]["access_token"]

        # 修改密码
        response = client.post(
            "/api/v1/auth/change-password",
            json={"old_password": "old_password", "new_password": "new_password"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True

        # 用新密码登录
        new_login_response = client.post("/api/v1/auth/login?username=changepwd&password=new_password")
        assert new_login_response.status_code == status.HTTP_200_OK

    def test_change_password_wrong_old_password(self, client: TestClient):
        """测试修改密码时旧密码错误"""
        # 注册并登录
        client.post(
            "/api/v1/auth/register",
            json={
                "username": "wrongoldpwd",
                "email": "wrongoldpwd@example.com",
                "nickname": "Wrong Old Password",
                "password": "correct_password",
            },
        )
        login_response = client.post("/api/v1/auth/login?username=wrongoldpwd&password=correct_password")
        token = login_response.json()["data"]["access_token"]

        # 使用错误的旧密码修改
        response = client.post(
            "/api/v1/auth/change-password",
            json={"old_password": "wrong_password", "new_password": "new_password"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "旧密码错误" in response.json()["detail"]


class TestUserAPI:
    """用户管理 API 测试类（需要超级管理员权限）"""

    def test_create_user(self, client: TestClient):
        """测试创建用户"""
        response = client.post(
            "/api/v1/users",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "nickname": "Test User",
                "password": "test123456",
                "is_active": True,
                "is_superuser": False,
            },
        )
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["success"] is True
        assert data["code"] == 201
        assert data["data"]["username"] == "testuser"
        assert data["data"]["email"] == "test@example.com"
        assert "id" in data["data"]

    def test_create_user_duplicate_username(self, client: TestClient):
        """测试创建重复用户名的用户"""
        # 第一次创建
        client.post(
            "/api/v1/users",
            json={
                "username": "duplicate",
                "email": "user1@example.com",
                "nickname": "User 1",
                "password": "test123456",
            },
        )
        # 第二次创建相同用户名
        response = client.post(
            "/api/v1/users",
            json={
                "username": "duplicate",
                "email": "user2@example.com",
                "nickname": "User 2",
                "password": "test123456",
            },
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "用户名已存在" in response.json()["detail"]

    def test_create_user_invalid_email(self, client: TestClient):
        """测试创建用户时邮箱格式错误"""
        response = client.post(
            "/api/v1/users",
            json={
                "username": "testuser",
                "email": "invalid-email",
                "nickname": "Test User",
                "password": "test123456",
            },
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_get_users(self, client: TestClient):
        """测试获取用户列表"""
        # 创建几个测试用户
        for i in range(3):
            client.post(
                "/api/v1/users",
                json={
                    "username": f"user{i}",
                    "email": f"user{i}@example.com",
                    "nickname": f"User {i}",
                    "password": "test123456",
                },
            )

        # 获取用户列表
        response = client.get("/api/v1/users")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 3
        assert len(data["data"]["items"]) >= 3

    def test_get_users_with_pagination(self, client: TestClient):
        """测试分页获取用户列表"""
        # 创建10个用户
        for i in range(10):
            client.post(
                "/api/v1/users",
                json={
                    "username": f"pageuser{i}",
                    "email": f"pageuser{i}@example.com",
                    "nickname": f"Page User {i}",
                    "password": "test123456",
                },
            )

        # 测试分页
        response = client.get("/api/v1/users?page_num=1&page_size=5")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["data"]["page_num"] == 1
        assert data["data"]["page_size"] == 5
        assert len(data["data"]["items"]) == 5

    def test_get_users_with_keyword_search(self, client: TestClient):
        """测试关键词搜索"""
        # 创建测试用户
        client.post(
            "/api/v1/users",
            json={
                "username": "searchuser",
                "email": "search@example.com",
                "nickname": "Search User",
                "password": "test123456",
            },
        )

        # 搜索用户
        response = client.get("/api/v1/users?keyword=search")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 1
        assert any("search" in item["username"].lower() for item in data["data"]["items"])

    def test_get_user_by_id(self, client: TestClient):
        """测试根据ID获取用户"""
        # 创建用户
        create_response = client.post(
            "/api/v1/users",
            json={
                "username": "getuser",
                "email": "getuser@example.com",
                "nickname": "Get User",
                "password": "test123456",
            },
        )
        user_id = create_response.json()["data"]["id"]

        # 获取用户
        response = client.get(f"/api/v1/users/{user_id}")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == user_id
        assert data["data"]["username"] == "getuser"

    def test_get_user_not_found(self, client: TestClient):
        """测试获取不存在的用户"""
        response = client.get("/api/v1/users/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "用户不存在" in response.json()["detail"]

    def test_update_user(self, client: TestClient):
        """测试更新用户"""
        # 创建用户
        create_response = client.post(
            "/api/v1/users",
            json={
                "username": "updateuser",
                "email": "update@example.com",
                "nickname": "Update User",
                "password": "test123456",
            },
        )
        user_id = create_response.json()["data"]["id"]

        # 更新用户
        response = client.put(
            f"/api/v1/users/{user_id}",
            json={"nickname": "Updated User", "email": "updated@example.com"},
        )
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["success"] is True
        assert data["data"]["nickname"] == "Updated User"
        assert data["data"]["email"] == "updated@example.com"

    def test_update_user_not_found(self, client: TestClient):
        """测试更新不存在的用户"""
        response = client.put("/api/v1/users/99999", json={"nickname": "Test"})
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_user(self, client: TestClient):
        """测试删除用户"""
        # 创建用户
        create_response = client.post(
            "/api/v1/users",
            json={
                "username": "deleteuser",
                "email": "delete@example.com",
                "nickname": "Delete User",
                "password": "test123456",
            },
        )
        user_id = create_response.json()["data"]["id"]

        # 删除用户
        response = client.delete(f"/api/v1/users/{user_id}")
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["success"] is True

        # 验证用户已删除
        get_response = client.get(f"/api/v1/users/{user_id}")
        assert get_response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_user_not_found(self, client: TestClient):
        """测试删除不存在的用户"""
        response = client.delete("/api/v1/users/99999")
        assert response.status_code == status.HTTP_404_NOT_FOUND
