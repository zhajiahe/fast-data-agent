"""
分析会话 API 集成测试
"""

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestSessionAPI:
    """分析会话 API 测试"""

    def _create_data_source(self, client: TestClient, auth_headers: dict, name: str | None = None) -> int:
        """辅助方法：创建数据源并返回ID，使用唯一名称"""
        if name is None:
            name = f"测试数据源_{uuid.uuid4().hex[:8]}"
        response = client.post(
            "/api/v1/data-sources",
            json={
                "name": name,
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
        json_data = response.json()
        if not json_data.get("success"):
            raise RuntimeError(f"创建数据源失败: {json_data}")
        return json_data["data"]["id"]

    def test_create_session(self, client: TestClient, auth_headers: dict):
        """测试创建会话"""
        ds_id = self._create_data_source(client, auth_headers)

        response = client.post(
            "/api/v1/sessions",
            json={
                "name": f"测试会话_{uuid.uuid4().hex[:8]}",
                "description": "这是一个测试会话",
                "data_source_ids": [ds_id],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert ds_id in data["data"]["data_source_ids"]

    def test_create_session_with_multiple_sources(self, client: TestClient, auth_headers: dict):
        """测试创建包含多个数据源的会话"""
        ds_id1 = self._create_data_source(client, auth_headers)
        ds_id2 = self._create_data_source(client, auth_headers)

        response = client.post(
            "/api/v1/sessions",
            json={
                "name": f"多数据源会话_{uuid.uuid4().hex[:8]}",
                "data_source_ids": [ds_id1, ds_id2],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert len(data["data"]["data_source_ids"]) == 2

    def test_list_sessions(self, client: TestClient, auth_headers: dict):
        """测试获取会话列表"""
        ds_id = self._create_data_source(client, auth_headers)
        client.post(
            "/api/v1/sessions",
            json={"name": f"会话列表测试_{uuid.uuid4().hex[:8]}", "data_source_ids": [ds_id]},
            headers=auth_headers,
        )

        response = client.get("/api/v1/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["total"] >= 1

    def test_get_session_detail(self, client: TestClient, auth_headers: dict):
        """测试获取会话详情"""
        ds_id = self._create_data_source(client, auth_headers)
        session_name = f"详情测试会话_{uuid.uuid4().hex[:8]}"
        create_response = client.post(
            "/api/v1/sessions",
            json={"name": session_name, "data_source_ids": [ds_id]},
            headers=auth_headers,
        )
        session_id = create_response.json()["data"]["id"]

        response = client.get(f"/api/v1/sessions/{session_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == session_name
        assert len(data["data"]["data_sources"]) == 1

    def test_update_session(self, client: TestClient, auth_headers: dict):
        """测试更新会话"""
        ds_id = self._create_data_source(client, auth_headers)
        create_response = client.post(
            "/api/v1/sessions",
            json={"name": f"原名称_{uuid.uuid4().hex[:8]}", "data_source_ids": [ds_id]},
            headers=auth_headers,
        )
        session_id = create_response.json()["data"]["id"]

        new_name = f"新名称_{uuid.uuid4().hex[:8]}"
        response = client.put(
            f"/api/v1/sessions/{session_id}",
            json={"name": new_name, "description": "新描述"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == new_name

    def test_delete_session(self, client: TestClient, auth_headers: dict):
        """测试删除会话"""
        ds_id = self._create_data_source(client, auth_headers)
        create_response = client.post(
            "/api/v1/sessions",
            json={"name": f"待删除_{uuid.uuid4().hex[:8]}", "data_source_ids": [ds_id]},
            headers=auth_headers,
        )
        session_id = create_response.json()["data"]["id"]

        response = client.delete(f"/api/v1/sessions/{session_id}", headers=auth_headers)
        assert response.status_code == 200

        response = client.get(f"/api/v1/sessions/{session_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_archive_session(self, client: TestClient, auth_headers: dict):
        """测试归档会话"""
        ds_id = self._create_data_source(client, auth_headers)
        create_response = client.post(
            "/api/v1/sessions",
            json={"name": f"待归档_{uuid.uuid4().hex[:8]}", "data_source_ids": [ds_id]},
            headers=auth_headers,
        )
        session_id = create_response.json()["data"]["id"]

        response = client.post(f"/api/v1/sessions/{session_id}/archive", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "archived"

    def test_create_session_with_invalid_data_source(self, client: TestClient, auth_headers: dict):
        """测试使用不存在的数据源创建会话"""
        response = client.post(
            "/api/v1/sessions",
            json={"name": f"测试_{uuid.uuid4().hex[:8]}", "data_source_ids": [99999]},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "不存在" in response.json()["msg"]
