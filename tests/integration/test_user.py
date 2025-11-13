"""
用户 API 集成测试
"""

from fastapi import status
from fastapi.testclient import TestClient


class TestUserAPI:
    """用户 API 测试类"""

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
