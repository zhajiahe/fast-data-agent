"""
对话 API 集成测试 (Mock)
"""

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestChatAPI:
    """对话 API 测试"""

    def _create_session(self, client: TestClient, auth_headers: dict) -> int:
        """辅助方法：创建数据源和会话，返回会话ID"""
        unique_id = uuid.uuid4().hex[:8]
        ds_response = client.post(
            "/api/v1/data-sources",
            json={
                "name": f"聊天测试数据源_{unique_id}",
                "source_type": "database",
                "db_config": {
                    "db_type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "database": "test",
                    "username": "test",
                    "password": "test",
                },
            },
            headers=auth_headers,
        )
        ds_json = ds_response.json()
        if not ds_json.get("success"):
            raise RuntimeError(f"创建数据源失败: {ds_json}")
        ds_id = ds_json["data"]["id"]

        session_response = client.post(
            "/api/v1/sessions",
            json={"name": f"聊天测试会话_{unique_id}", "data_source_ids": [ds_id]},
            headers=auth_headers,
        )
        session_json = session_response.json()
        if not session_json.get("success"):
            raise RuntimeError(f"创建会话失败: {session_json}")
        return session_json["data"]["id"]

    def test_chat_streaming(self, client: TestClient, auth_headers: dict):
        """测试流式对话（SSE）"""
        session_id = self._create_session(client, auth_headers)

        response = client.post(
            f"/api/v1/sessions/{session_id}/chat",
            json={"content": "帮我分析用户数据"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        assert "data:" in response.text

    def test_get_messages(self, client: TestClient, auth_headers: dict):
        """测试获取历史消息"""
        session_id = self._create_session(client, auth_headers)

        response = client.get(f"/api/v1/sessions/{session_id}/messages", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]

    def test_get_recommendations(self, client: TestClient, auth_headers: dict):
        """测试获取任务推荐（空列表）"""
        session_id = self._create_session(client, auth_headers)

        response = client.get(f"/api/v1/sessions/{session_id}/recommendations", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 返回分页格式
        assert "items" in data["data"]
        assert "total" in data["data"]
        assert isinstance(data["data"]["items"], list)

    def test_update_recommendation_status(self, client: TestClient, auth_headers: dict):
        """测试更新推荐状态"""
        session_id = self._create_session(client, auth_headers)

        # 先生成推荐
        gen_response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            headers=auth_headers,
        )
        assert gen_response.status_code == 201
        gen_data = gen_response.json()
        assert gen_data["success"] is True
        assert len(gen_data["data"]) > 0

        # 获取第一个推荐的 ID
        recommendation_id = gen_data["data"][0]["id"]

        # 更新状态为 selected
        update_response = client.put(
            f"/api/v1/sessions/{session_id}/recommendations/{recommendation_id}",
            json={"status": "selected"},
            headers=auth_headers,
        )
        assert update_response.status_code == 200
        update_data = update_response.json()
        assert update_data["success"] is True
        assert update_data["data"]["status"] == "selected"

    def test_chat_without_auth(self, client: TestClient):
        """测试未认证访问"""
        response = client.post(
            "/api/v1/sessions/1/chat",
            json={"content": "test"},
        )
        # 可能返回 401 或 403
        assert response.status_code in [401, 403]

    def test_chat_invalid_session(self, client: TestClient, auth_headers: dict):
        """测试访问不存在的会话"""
        response = client.post(
            "/api/v1/sessions/99999/chat",
            json={"content": "test"},
            headers=auth_headers,
        )
        assert response.status_code == 404
