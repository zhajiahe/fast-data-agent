"""
任务推荐 API 集成测试
"""

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestRecommendationAPI:
    """任务推荐 API 测试"""

    def _create_data_source(self, client: TestClient, auth_headers: dict, name: str | None = None) -> int:
        """辅助方法：创建数据源并返回ID"""
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

    def _create_session(self, client: TestClient, auth_headers: dict, ds_id: int) -> int:
        """辅助方法：创建会话并返回ID"""
        response = client.post(
            "/api/v1/sessions",
            json={
                "name": f"测试会话_{uuid.uuid4().hex[:8]}",
                "data_source_ids": [ds_id],
            },
            headers=auth_headers,
        )
        json_data = response.json()
        if not json_data.get("success"):
            raise RuntimeError(f"创建会话失败: {json_data}")
        return json_data["data"]["id"]

    def test_get_empty_recommendations(self, client: TestClient, auth_headers: dict):
        """测试获取空的推荐列表"""
        ds_id = self._create_data_source(client, auth_headers)
        session_id = self._create_session(client, auth_headers, ds_id)

        response = client.get(
            f"/api/v1/sessions/{session_id}/recommendations",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 会话创建时会自动生成推荐，所以列表可能不为空
        assert "items" in data["data"]

    def test_generate_initial_recommendations(self, client: TestClient, auth_headers: dict):
        """测试生成初始推荐"""
        ds_id = self._create_data_source(client, auth_headers)
        session_id = self._create_session(client, auth_headers, ds_id)

        response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            json={"max_count": 3, "force_regenerate": True},
            headers=auth_headers,
        )
        # 即使 LLM 不可用，也应该返回基于规则的推荐
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert len(data["data"]) <= 3

    def test_generate_recommendations_without_body(self, client: TestClient, auth_headers: dict):
        """测试不带请求体生成推荐"""
        ds_id = self._create_data_source(client, auth_headers)
        session_id = self._create_session(client, auth_headers, ds_id)

        response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            headers=auth_headers,
        )
        assert response.status_code == 201

    def test_update_recommendation_status(self, client: TestClient, auth_headers: dict):
        """测试更新推荐状态"""
        ds_id = self._create_data_source(client, auth_headers)
        session_id = self._create_session(client, auth_headers, ds_id)

        # 先生成推荐
        gen_response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            json={"max_count": 1, "force_regenerate": True},
            headers=auth_headers,
        )
        recommendations = gen_response.json()["data"]
        if not recommendations:
            pytest.skip("无法生成推荐")

        rec_id = recommendations[0]["id"]

        # 更新状态为 selected
        response = client.put(
            f"/api/v1/sessions/{session_id}/recommendations/{rec_id}",
            json={"status": "selected"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["status"] == "selected"

    def test_update_recommendation_to_dismissed(self, client: TestClient, auth_headers: dict):
        """测试将推荐标记为已忽略"""
        ds_id = self._create_data_source(client, auth_headers)
        session_id = self._create_session(client, auth_headers, ds_id)

        # 生成推荐
        gen_response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            json={"max_count": 1, "force_regenerate": True},
            headers=auth_headers,
        )
        recommendations = gen_response.json()["data"]
        if not recommendations:
            pytest.skip("无法生成推荐")

        rec_id = recommendations[0]["id"]

        # 更新状态为 dismissed
        response = client.put(
            f"/api/v1/sessions/{session_id}/recommendations/{rec_id}",
            json={"status": "dismissed"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "dismissed"

    def test_update_with_invalid_status(self, client: TestClient, auth_headers: dict):
        """测试使用无效状态更新"""
        ds_id = self._create_data_source(client, auth_headers)
        session_id = self._create_session(client, auth_headers, ds_id)

        # 生成推荐
        gen_response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            json={"max_count": 1, "force_regenerate": True},
            headers=auth_headers,
        )
        recommendations = gen_response.json()["data"]
        if not recommendations:
            pytest.skip("无法生成推荐")

        rec_id = recommendations[0]["id"]

        # 尝试使用无效状态
        response = client.put(
            f"/api/v1/sessions/{session_id}/recommendations/{rec_id}",
            json={"status": "invalid_status"},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_dismiss_all_recommendations(self, client: TestClient, auth_headers: dict):
        """测试批量忽略推荐"""
        ds_id = self._create_data_source(client, auth_headers)
        session_id = self._create_session(client, auth_headers, ds_id)

        # 生成推荐
        client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            json={"max_count": 3, "force_regenerate": True},
            headers=auth_headers,
        )

        # 批量忽略
        response = client.delete(
            f"/api/v1/sessions/{session_id}/recommendations",
            headers=auth_headers,
        )
        assert response.status_code == 200

    def test_filter_recommendations_by_status(self, client: TestClient, auth_headers: dict):
        """测试按状态过滤推荐"""
        ds_id = self._create_data_source(client, auth_headers)
        session_id = self._create_session(client, auth_headers, ds_id)

        # 生成推荐
        gen_response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            json={"max_count": 2, "force_regenerate": True},
            headers=auth_headers,
        )
        recommendations = gen_response.json()["data"]
        if not recommendations:
            pytest.skip("无法生成推荐")

        # 将第一个标记为 selected
        rec_id = recommendations[0]["id"]
        client.put(
            f"/api/v1/sessions/{session_id}/recommendations/{rec_id}",
            json={"status": "selected"},
            headers=auth_headers,
        )

        # 按 pending 过滤
        response = client.get(
            f"/api/v1/sessions/{session_id}/recommendations",
            params={"status_filter": "pending"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        for item in items:
            assert item["status"] == "pending"

    def test_filter_recommendations_by_source_type(self, client: TestClient, auth_headers: dict):
        """测试按来源类型过滤推荐"""
        ds_id = self._create_data_source(client, auth_headers)
        session_id = self._create_session(client, auth_headers, ds_id)

        # 生成初始推荐
        client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            json={"max_count": 2, "force_regenerate": True},
            headers=auth_headers,
        )

        # 按 initial 过滤
        response = client.get(
            f"/api/v1/sessions/{session_id}/recommendations",
            params={"source_type": "initial"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        items = response.json()["data"]["items"]
        for item in items:
            assert item["source_type"] == "initial"

    def test_generate_followup_recommendations(self, client: TestClient, auth_headers: dict):
        """测试生成追问推荐"""
        ds_id = self._create_data_source(client, auth_headers)
        session_id = self._create_session(client, auth_headers, ds_id)

        response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations/followup",
            json={
                "conversation_context": "用户询问了销售趋势",
                "max_count": 2,
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        # 追问推荐应该返回 follow_up 类型
        for item in data["data"]:
            assert item["source_type"] == "follow_up"

    def test_recommendation_not_found(self, client: TestClient, auth_headers: dict):
        """测试推荐不存在"""
        ds_id = self._create_data_source(client, auth_headers)
        session_id = self._create_session(client, auth_headers, ds_id)

        response = client.put(
            f"/api/v1/sessions/{session_id}/recommendations/99999",
            json={"status": "selected"},
            headers=auth_headers,
        )
        assert response.status_code == 404

    def test_unauthorized_access(self, client: TestClient, auth_headers: dict):
        """测试未授权访问"""
        ds_id = self._create_data_source(client, auth_headers)
        session_id = self._create_session(client, auth_headers, ds_id)

        # 不带 auth_headers - HTTPBearer 返回 403 Forbidden
        response = client.get(f"/api/v1/sessions/{session_id}/recommendations")
        assert response.status_code == 403

    def test_session_not_found(self, client: TestClient, auth_headers: dict):
        """测试会话不存在"""
        response = client.get(
            "/api/v1/sessions/99999/recommendations",
            headers=auth_headers,
        )
        assert response.status_code == 404

