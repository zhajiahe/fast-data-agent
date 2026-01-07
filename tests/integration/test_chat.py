"""
聊天 API 测试

测试 /api/v1/sessions/{session_id}/chat 和 /api/v1/sessions/{session_id}/messages 端点：
- 消息历史
- 消息清空
- 批量消息获取
"""

from typing import Any

import pytest
from starlette.testclient import TestClient


class TestChatMessages:
    """聊天消息测试"""

    def test_get_messages_empty(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试获取空消息历史"""
        session_id = test_session["id"]
        response = client.get(
            f"/api/v1/sessions/{session_id}/messages",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 0
        assert data["data"]["items"] == []

    def test_get_messages_pagination(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试消息分页参数"""
        session_id = test_session["id"]
        response = client.get(
            f"/api/v1/sessions/{session_id}/messages",
            headers=auth_headers,
            params={"page_num": 1, "page_size": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "page_num" in data["data"]
        assert "page_size" in data["data"]
        assert "total" in data["data"]
        assert "items" in data["data"]

    def test_get_messages_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在会话的消息"""
        response = client.get(
            "/api/v1/sessions/00000000-0000-0000-0000-000000099999/messages",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_get_messages_unauthorized(self, client: TestClient, test_session: dict[str, Any]):
        """测试未认证获取消息"""
        session_id = test_session["id"]
        response = client.get(f"/api/v1/sessions/{session_id}/messages")

        assert response.status_code in (401, 403)

    def test_clear_messages(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试清空消息"""
        session_id = test_session["id"]
        response = client.delete(
            f"/api/v1/sessions/{session_id}/messages",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 返回清空的消息数
        assert isinstance(data["data"], int)

    def test_clear_messages_not_found(self, client: TestClient, auth_headers: dict):
        """测试清空不存在会话的消息"""
        response = client.delete(
            "/api/v1/sessions/00000000-0000-0000-0000-000000099999/messages",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_clear_messages_unauthorized(
        self, client: TestClient, test_session: dict[str, Any]
    ):
        """测试未认证清空消息"""
        session_id = test_session["id"]
        response = client.delete(f"/api/v1/sessions/{session_id}/messages")

        assert response.status_code in (401, 403)


class TestBatchMessages:
    """批量消息获取测试"""

    def test_batch_messages_empty(self, client: TestClient, auth_headers: dict):
        """测试空会话列表（需要至少一个 session_id）"""
        response = client.post(
            "/api/v1/messages/batch",
            headers=auth_headers,
            json={"session_ids": []},
        )

        # session_ids 需要至少一个元素，空列表返回验证错误
        assert response.status_code == 422

    def test_batch_messages_single(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试单个会话批量获取"""
        session_id = test_session["id"]
        response = client.post(
            "/api/v1/messages/batch",
            headers=auth_headers,
            json={"session_ids": [session_id]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]["items"]) == 1
        assert data["data"]["items"][0]["session_id"] == session_id

    def test_batch_messages_invalid_session(self, client: TestClient, auth_headers: dict):
        """测试包含无效会话 ID 的批量获取"""
        response = client.post(
            "/api/v1/messages/batch",
            headers=auth_headers,
            json={"session_ids": ["00000000-0000-0000-0000-000000099999"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 无效的会话会被静默忽略
        assert data["data"]["items"] == []

    def test_batch_messages_with_page_size(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试批量获取带分页参数"""
        session_id = test_session["id"]
        response = client.post(
            "/api/v1/messages/batch",
            headers=auth_headers,
            json={"session_ids": [session_id], "page_size": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_batch_messages_unauthorized(self, client: TestClient):
        """测试未认证批量获取"""
        response = client.post(
            "/api/v1/messages/batch",
            json={"session_ids": []},
        )

        assert response.status_code in (401, 403)


class TestChatStream:
    """聊天流测试（SSE）"""

    def test_chat_not_found(self, client: TestClient, auth_headers: dict):
        """测试向不存在的会话发送消息"""
        response = client.post(
            "/api/v1/sessions/00000000-0000-0000-0000-000000099999/chat",
            headers=auth_headers,
            json={"content": "Hello"},
        )

        assert response.status_code == 404

    def test_chat_unauthorized(self, client: TestClient, test_session: dict[str, Any]):
        """测试未认证发送消息"""
        session_id = test_session["id"]
        response = client.post(
            f"/api/v1/sessions/{session_id}/chat",
            json={"content": "Hello"},
        )

        assert response.status_code in (401, 403)

    def test_chat_empty_content(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试发送空消息内容"""
        session_id = test_session["id"]
        response = client.post(
            f"/api/v1/sessions/{session_id}/chat",
            headers=auth_headers,
            json={"content": ""},
        )

        # 空内容应该返回验证错误
        assert response.status_code == 422

    def test_chat_stream_response_headers(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试聊天流响应头（不完整测试，只检查是否返回 SSE）"""
        session_id = test_session["id"]

        # 由于 TestClient 对 SSE 支持有限，我们只检查是否能开始请求
        # 实际的流测试需要使用 httpx 或其他支持 SSE 的客户端
        response = client.post(
            f"/api/v1/sessions/{session_id}/chat",
            headers=auth_headers,
            json={"content": "测试消息"},
        )

        # SSE 响应应该是 200
        assert response.status_code == 200
        # 检查响应头
        assert "text/event-stream" in response.headers.get("content-type", "")


class TestChatAuth:
    """聊天认证测试"""

    def test_access_other_user_chat(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试访问其他用户的聊天消息"""
        import uuid

        # 注册另一个用户
        uid = uuid.uuid4().hex[:8]
        client.post(
            "/api/v1/auth/register",
            json={
                "username": f"otheruser_{uid}",
                "email": f"other_{uid}@example.com",
                "nickname": "Other User",
                "password": "otherpass123",
            },
        )

        # 登录另一个用户
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": f"otheruser_{uid}", "password": "otherpass123"},
        )

        if login_response.status_code == 200:
            other_token = login_response.json()["data"]["access_token"]
            other_headers = {"Authorization": f"Bearer {other_token}"}

            # 尝试获取第一个用户的会话消息
            session_id = test_session["id"]
            response = client.get(
                f"/api/v1/sessions/{session_id}/messages",
                headers=other_headers,
            )

            # 应该返回 404（因为其他用户看不到此会话）
            assert response.status_code in (403, 404)

