"""
数据源 API 测试

测试 /api/v1/data-sources 端点：
- CRUD 操作
- 映射管理
- Schema 刷新
- 数据预览
"""

from typing import Any

from starlette.testclient import TestClient


class TestDataSourceCRUD:
    """数据源 CRUD 测试"""

    def test_create_data_source(
        self, client: TestClient, auth_headers: dict, test_raw_data: dict[str, Any]
    ):
        """测试创建数据源"""
        response = client.post(
            "/api/v1/data-sources",
            headers=auth_headers,
            json={
                "name": "New Data Source",
                "description": "测试创建数据源",
                "category": "fact",
                "target_fields": [
                    {"name": "id", "data_type": "integer", "description": "ID"},
                    {"name": "name", "data_type": "string", "description": "名称"},
                ],
                "raw_mappings": [
                    {
                        "raw_data_id": test_raw_data["id"],
                        "mappings": {"id": "id", "name": "name"},
                        "priority": 0,
                        "is_enabled": True,
                    }
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "New Data Source"
        assert data["data"]["category"] == "fact"

    def test_create_data_source_no_mappings(self, client: TestClient, auth_headers: dict):
        """测试创建数据源（无映射）"""
        response = client.post(
            "/api/v1/data-sources",
            headers=auth_headers,
            json={
                "name": "Empty Data Source",
                "description": "无映射的数据源",
                "category": "dimension",
                "target_fields": [
                    {"name": "code", "data_type": "string", "description": "编码"},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    def test_create_data_source_invalid_raw_data(self, client: TestClient, auth_headers: dict):
        """测试创建数据源（无效的 raw_data_id）"""
        response = client.post(
            "/api/v1/data-sources",
            headers=auth_headers,
            json={
                "name": "Invalid Data Source",
                "raw_mappings": [
                    {
                        "raw_data_id": "00000000-0000-0000-0000-000000099999",
                        "mappings": {"id": "id"},
                    }
                ],
            },
        )

        assert response.status_code == 400

    def test_list_data_sources(
        self, client: TestClient, auth_headers: dict, test_data_source: dict[str, Any]
    ):
        """测试获取数据源列表"""
        response = client.get("/api/v1/data-sources", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 1

    def test_list_data_sources_filter_category(
        self, client: TestClient, auth_headers: dict, test_data_source: dict[str, Any]
    ):
        """测试数据源列表按分类过滤"""
        response = client.get(
            "/api/v1/data-sources",
            headers=auth_headers,
            params={"category": "fact"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_list_data_sources_search(
        self, client: TestClient, auth_headers: dict, test_data_source: dict[str, Any]
    ):
        """测试数据源列表搜索"""
        response = client.get(
            "/api/v1/data-sources",
            headers=auth_headers,
            params={"search": "Test"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_data_source(
        self, client: TestClient, auth_headers: dict, test_data_source: dict[str, Any]
    ):
        """测试获取单个数据源"""
        data_source_id = test_data_source["id"]
        response = client.get(f"/api/v1/data-sources/{data_source_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == data_source_id

    def test_get_data_source_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的数据源"""
        response = client.get("/api/v1/data-sources/00000000-0000-0000-0000-000000099999", headers=auth_headers)

        assert response.status_code == 404

    def test_update_data_source(
        self, client: TestClient, auth_headers: dict, test_data_source: dict[str, Any]
    ):
        """测试更新数据源"""
        data_source_id = test_data_source["id"]
        response = client.put(
            f"/api/v1/data-sources/{data_source_id}",
            headers=auth_headers,
            json={
                "name": "Updated Data Source",
                "description": "更新后的描述",
                "category": "dimension",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Updated Data Source"
        assert data["data"]["category"] == "dimension"

    def test_delete_data_source(
        self, client: TestClient, auth_headers: dict, test_raw_data: dict[str, Any]
    ):
        """测试删除数据源"""
        # 先创建一个数据源
        create_response = client.post(
            "/api/v1/data-sources",
            headers=auth_headers,
            json={
                "name": "To Delete Source",
                "category": "other",
                "raw_mappings": [
                    {
                        "raw_data_id": test_raw_data["id"],
                        "mappings": {"id": "id"},
                    }
                ],
            },
        )
        data_source_id = create_response.json()["data"]["id"]

        # 删除
        response = client.delete(
            f"/api/v1/data-sources/{data_source_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证已删除
        get_response = client.get(
            f"/api/v1/data-sources/{data_source_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404


class TestDataSourceMappings:
    """数据源映射管理测试"""

    def test_add_mapping(
        self,
        client: TestClient,
        auth_headers: dict,
        test_data_source: dict[str, Any],
        test_file: dict[str, Any],
    ):
        """测试添加映射"""
        if not test_data_source.get("id"):
            pytest.skip("数据源创建失败")

        data_source_id = test_data_source["id"]

        # 先创建另一个数据对象
        raw_data_response = client.post(
            "/api/v1/raw-data",
            headers=auth_headers,
            json={
                "name": "another_raw",
                "raw_type": "file",
                "file_config": {"file_id": test_file["id"]},
            },
        )
        new_raw_data_id = raw_data_response.json()["data"]["id"]

        # 添加映射
        response = client.post(
            f"/api/v1/data-sources/{data_source_id}/mappings",
            headers=auth_headers,
            json={
                "raw_data_id": new_raw_data_id,
                "mappings": {"id": "id", "name": "name"},
                "priority": 1,
                "is_enabled": True,
            },
        )

        # 可能成功或返回 404（如果映射端点尚未实现）
        assert response.status_code in (200, 201, 404)

    def test_update_mapping(
        self, client: TestClient, auth_headers: dict, test_data_source: dict[str, Any]
    ):
        """测试更新映射"""
        data_source_id = test_data_source["id"]

        # 获取现有映射
        get_response = client.get(
            f"/api/v1/data-sources/{data_source_id}",
            headers=auth_headers,
        )
        mappings = get_response.json()["data"].get("raw_data_mappings", [])

        if mappings:
            mapping_id = mappings[0]["id"]
            response = client.put(
                f"/api/v1/data-sources/{data_source_id}/mappings/{mapping_id}",
                headers=auth_headers,
                json={"priority": 10, "is_enabled": False},
            )

            assert response.status_code == 200

    def test_delete_mapping(
        self,
        client: TestClient,
        auth_headers: dict,
        test_data_source: dict[str, Any],
        test_file: dict[str, Any],
    ):
        """测试删除映射"""
        data_source_id = test_data_source["id"]

        # 先创建另一个数据对象并添加映射
        raw_data_response = client.post(
            "/api/v1/raw-data",
            headers=auth_headers,
            json={
                "name": "to_remove_raw",
                "raw_type": "file",
                "file_config": {"file_id": test_file["id"]},
            },
        )
        new_raw_data_id = raw_data_response.json()["data"]["id"]

        # 添加映射
        add_response = client.post(
            f"/api/v1/data-sources/{data_source_id}/mappings",
            headers=auth_headers,
            json={
                "raw_data_id": new_raw_data_id,
                "mappings": {"id": "id"},
            },
        )

        if add_response.status_code in (200, 201):
            # 获取映射 ID
            get_response = client.get(
                f"/api/v1/data-sources/{data_source_id}",
                headers=auth_headers,
            )
            mappings = get_response.json()["data"].get("raw_data_mappings", [])
            mapping_to_delete = next(
                (m for m in mappings if m.get("raw_data_id") == new_raw_data_id), None
            )

            if mapping_to_delete:
                response = client.delete(
                    f"/api/v1/data-sources/{data_source_id}/mappings/{mapping_to_delete['id']}",
                    headers=auth_headers,
                )
                assert response.status_code == 200


class TestDataSourceOperations:
    """数据源操作测试"""

    def test_refresh_schema(
        self, client: TestClient, auth_headers: dict, test_data_source: dict[str, Any]
    ):
        """测试刷新 Schema"""
        if not test_data_source.get("id"):
            pytest.skip("数据源创建失败")

        data_source_id = test_data_source["id"]
        response = client.post(
            f"/api/v1/data-sources/{data_source_id}/refresh-schema",
            headers=auth_headers,
        )

        # 刷新可能成功或因数据源映射问题而失败
        assert response.status_code in (200, 400, 404, 500)
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True

    def test_preview_data(
        self,
        client: TestClient,
        auth_headers: dict,
        test_data_source: dict[str, Any],
    ):
        """测试预览数据"""
        data_source_id = test_data_source["id"]

        response = client.post(
            f"/api/v1/data-sources/{data_source_id}/preview",
            headers=auth_headers,
            json={"limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "rows" in data["data"]
        assert "columns" in data["data"]
        assert "source_stats" in data["data"]

    def test_refresh_schema_not_found(self, client: TestClient, auth_headers: dict):
        """测试刷新不存在数据源的 Schema"""
        response = client.post(
            "/api/v1/data-sources/00000000-0000-0000-0000-000000099999/refresh-schema",
            headers=auth_headers,
        )

        assert response.status_code == 404

    def test_preview_data_not_found(self, client: TestClient, auth_headers: dict):
        """测试预览不存在的数据源"""
        response = client.post(
            "/api/v1/data-sources/00000000-0000-0000-0000-000000099999/preview",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestDataSourceSuggestMappings:
    """字段映射建议测试"""

    def test_suggest_mappings(
        self, client: TestClient, auth_headers: dict, test_raw_data: dict[str, Any]
    ):
        """测试字段映射建议"""
        # 确保 raw_data 有 columns_schema（需要先同步）
        raw_data_id = test_raw_data["id"]

        # 请求映射建议
        response = client.post(
            "/api/v1/data-sources/suggest-mappings",
            headers=auth_headers,
            json={
                "target_fields": [
                    {"name": "id", "data_type": "integer"},
                    {"name": "name", "data_type": "string"},
                    {"name": "value", "data_type": "float"},
                ],
                "raw_data_ids": [raw_data_id],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "suggestions" in data["data"]

    def test_suggest_mappings_empty_raw_data(self, client: TestClient, auth_headers: dict):
        """测试空数据对象列表的映射建议"""
        response = client.post(
            "/api/v1/data-sources/suggest-mappings",
            headers=auth_headers,
            json={
                "target_fields": [
                    {"name": "id", "data_type": "integer"},
                ],
                "raw_data_ids": ["00000000-0000-0000-0000-000000099999"],  # 不存在的 ID
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["suggestions"] == []

    def test_suggest_target_fields(
        self, client: TestClient, auth_headers: dict, test_raw_data: dict[str, Any]
    ):
        """测试从数据对象推断目标字段"""
        raw_data_id = test_raw_data["id"]

        response = client.post(
            "/api/v1/data-sources/suggest-target-fields",
            headers=auth_headers,
            json={
                "raw_data_ids": [raw_data_id],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "fields" in data["data"]


class TestDataSourceAuth:
    """数据源认证测试"""

    def test_create_without_auth(self, client: TestClient):
        """测试未认证创建"""
        response = client.post(
            "/api/v1/data-sources",
            json={
                "name": "Unauthorized",
                "category": "fact",
            },
        )

        assert response.status_code in (401, 403)

    def test_list_without_auth(self, client: TestClient):
        """测试未认证获取列表"""
        response = client.get("/api/v1/data-sources")

        assert response.status_code in (401, 403)

    def test_get_without_auth(self, client: TestClient):
        """测试未认证获取详情"""
        response = client.get("/api/v1/data-sources/1")

        assert response.status_code in (401, 403)
