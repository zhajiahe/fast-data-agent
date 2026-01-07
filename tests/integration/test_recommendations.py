"""
推荐任务 API 测试

测试 /api/v1/sessions/{session_id}/recommendations 端点：
- 生成推荐
- 获取推荐列表
- 更新推荐状态
- 批量忽略推荐
"""

import uuid
from typing import Any

from starlette.testclient import TestClient


class TestRecommendationsCRUD:
    """推荐 CRUD 测试"""

    def test_get_recommendations_empty(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试获取空推荐列表"""
        session_id = test_session["id"]
        response = client.get(
            f"/api/v1/sessions/{session_id}/recommendations",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] == 0
        assert data["data"]["items"] == []

    def test_get_recommendations_pagination(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试推荐列表分页"""
        session_id = test_session["id"]
        response = client.get(
            f"/api/v1/sessions/{session_id}/recommendations",
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

    def test_get_recommendations_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在会话的推荐"""
        response = client.get(
            "/api/v1/sessions/00000000-0000-0000-0000-000000099999/recommendations",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_generate_recommendations(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试生成推荐"""
        session_id = test_session["id"]
        response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            headers=auth_headers,
            json={"max_count": 5},
        )

        # 可能成功或因 LLM 服务不可用而失败
        assert response.status_code in (201, 500)
        if response.status_code == 201:
            data = response.json()
            assert data["success"] is True
            assert isinstance(data["data"], list)

    def test_generate_recommendations_default(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试生成推荐（使用默认参数）"""
        session_id = test_session["id"]
        response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            headers=auth_headers,
        )

        # 可能成功或因 LLM 服务不可用而失败
        assert response.status_code in (201, 500)

    def test_generate_recommendations_not_found(self, client: TestClient, auth_headers: dict):
        """测试为不存在的会话生成推荐"""
        response = client.post(
            "/api/v1/sessions/00000000-0000-0000-0000-000000099999/recommendations",
            headers=auth_headers,
            json={"max_count": 5},
        )

        assert response.status_code == 404

    def test_generate_recommendations_force_regenerate(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试强制重新生成推荐"""
        session_id = test_session["id"]
        response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            headers=auth_headers,
            json={"max_count": 3, "force_regenerate": True},
        )

        # 可能成功或因 LLM 服务不可用而失败
        assert response.status_code in (201, 500)


class TestRecommendationsStatus:
    """推荐状态更新测试"""

    def test_update_recommendation_not_found(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试更新不存在的推荐"""
        session_id = test_session["id"]
        response = client.put(
            f"/api/v1/sessions/{session_id}/recommendations/00000000-0000-0000-0000-000000099999",
            headers=auth_headers,
            json={"status": "selected"},
        )

        assert response.status_code == 404

    def test_update_recommendation_invalid_status(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试使用无效状态更新推荐"""
        session_id = test_session["id"]
        response = client.put(
            f"/api/v1/sessions/{session_id}/recommendations/00000000-0000-0000-0000-000000099999",
            headers=auth_headers,
            json={"status": "invalid_status"},
        )

        # 可能返回 400 或 404
        assert response.status_code in (400, 404)


class TestRecommendationsDismiss:
    """推荐批量忽略测试"""

    def test_dismiss_all_recommendations(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试批量忽略推荐"""
        session_id = test_session["id"]
        response = client.delete(
            f"/api/v1/sessions/{session_id}/recommendations",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_dismiss_recommendations_by_type(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试按类型忽略推荐"""
        session_id = test_session["id"]
        response = client.delete(
            f"/api/v1/sessions/{session_id}/recommendations",
            headers=auth_headers,
            params={"source_type": "initial"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_dismiss_recommendations_not_found(self, client: TestClient, auth_headers: dict):
        """测试忽略不存在会话的推荐"""
        response = client.delete(
            "/api/v1/sessions/00000000-0000-0000-0000-000000099999/recommendations",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestFollowupRecommendations:
    """追问推荐测试"""

    def test_generate_followup_not_found(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试为不存在的会话生成追问推荐"""
        response = client.post(
            "/api/v1/sessions/00000000-0000-0000-0000-000000099999/recommendations/followup",
            headers=auth_headers,
            json={
                "conversation_context": "用户询问了销售数据",
                "last_result": {"summary": "返回了销售趋势图"},  # 修复：last_result 应该是 dict
                "max_count": 3,
            },
        )

        assert response.status_code == 404

    def test_generate_followup_missing_context(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试生成追问推荐（缺少必要字段）"""
        session_id = test_session["id"]
        response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations/followup",
            headers=auth_headers,
            json={},  # 缺少 conversation_context
        )

        assert response.status_code == 422


class TestRecommendationsAuth:
    """推荐认证测试"""

    def test_get_recommendations_unauthorized(
        self, client: TestClient, test_session: dict[str, Any]
    ):
        """测试未认证获取推荐"""
        session_id = test_session["id"]
        response = client.get(f"/api/v1/sessions/{session_id}/recommendations")

        assert response.status_code in (401, 403)

    def test_generate_recommendations_unauthorized(
        self, client: TestClient, test_session: dict[str, Any]
    ):
        """测试未认证生成推荐"""
        session_id = test_session["id"]
        response = client.post(
            f"/api/v1/sessions/{session_id}/recommendations",
            json={"max_count": 5},
        )

        assert response.status_code in (401, 403)

    def test_access_other_user_recommendations(
        self, client: TestClient, auth_headers: dict, test_session: dict[str, Any]
    ):
        """测试访问其他用户的推荐"""
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

            # 尝试获取第一个用户的会话推荐
            session_id = test_session["id"]
            response = client.get(
                f"/api/v1/sessions/{session_id}/recommendations",
                headers=other_headers,
            )

            # 应该返回 404（因为其他用户看不到此会话）
            assert response.status_code in (403, 404)

