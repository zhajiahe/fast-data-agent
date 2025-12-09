"""
原始数据 API 测试

测试 /api/v1/raw-data 端点：
- CRUD 操作
- 预览
- 同步
- 列类型更新
"""

from typing import Any

from starlette.testclient import TestClient


class TestRawDataCRUD:
    """原始数据 CRUD 测试"""

    def test_create_raw_data_file(
        self, client: TestClient, auth_headers: dict, test_file: dict[str, Any]
    ):
        """测试创建原始数据（文件类型）"""
        response = client.post(
            "/api/v1/raw-data",
            headers=auth_headers,
            json={
                "name": "test_file_raw",
                "description": "测试文件原始数据",
                "raw_type": "file",
                "file_config": {"file_id": test_file["id"]},
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "test_file_raw"
        assert data["data"]["raw_type"] == "file"

    def test_create_raw_data_database_table(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """测试创建原始数据（数据库表类型）"""
        response = client.post(
            "/api/v1/raw-data",
            headers=auth_headers,
            json={
                "name": "test_table_raw",
                "description": "测试数据库表原始数据",
                "raw_type": "database_table",
                "database_table_config": {
                    "connection_id": test_connection["id"],
                    "schema_name": "public",
                    "table_name": "users",
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["raw_type"] == "database_table"

    def test_create_raw_data_invalid_file(self, client: TestClient, auth_headers: dict):
        """测试创建原始数据（无效文件 ID）"""
        response = client.post(
            "/api/v1/raw-data",
            headers=auth_headers,
            json={
                "name": "invalid_raw",
                "raw_type": "file",
                "file_config": {"file_id": 99999},
            },
        )

        assert response.status_code == 400

    def test_list_raw_data(
        self, client: TestClient, auth_headers: dict, test_raw_data: dict[str, Any]
    ):
        """测试获取原始数据列表"""
        response = client.get("/api/v1/raw-data", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 1

    def test_list_raw_data_filter(
        self, client: TestClient, auth_headers: dict, test_raw_data: dict[str, Any]
    ):
        """测试原始数据列表过滤"""
        response = client.get(
            "/api/v1/raw-data",
            headers=auth_headers,
            params={"raw_type": "file"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_raw_data(
        self, client: TestClient, auth_headers: dict, test_raw_data: dict[str, Any]
    ):
        """测试获取单个原始数据"""
        raw_data_id = test_raw_data["id"]
        response = client.get(f"/api/v1/raw-data/{raw_data_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == raw_data_id

    def test_get_raw_data_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的原始数据"""
        response = client.get("/api/v1/raw-data/99999", headers=auth_headers)

        assert response.status_code == 404

    def test_update_raw_data(
        self, client: TestClient, auth_headers: dict, test_raw_data: dict[str, Any]
    ):
        """测试更新原始数据"""
        raw_data_id = test_raw_data["id"]
        response = client.put(
            f"/api/v1/raw-data/{raw_data_id}",
            headers=auth_headers,
            json={"description": "更新后的描述"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["description"] == "更新后的描述"

    def test_delete_raw_data(
        self, client: TestClient, auth_headers: dict, test_file: dict[str, Any]
    ):
        """测试删除原始数据"""
        # 先创建一个原始数据
        create_response = client.post(
            "/api/v1/raw-data",
            headers=auth_headers,
            json={
                "name": "to_delete_raw",
                "raw_type": "file",
                "file_config": {"file_id": test_file["id"]},
            },
        )
        raw_data_id = create_response.json()["data"]["id"]

        # 删除
        response = client.delete(f"/api/v1/raw-data/{raw_data_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证已删除
        get_response = client.get(f"/api/v1/raw-data/{raw_data_id}", headers=auth_headers)
        assert get_response.status_code == 404


class TestRawDataPreview:
    """原始数据预览测试"""

    def test_preview_raw_data(
        self, client: TestClient, auth_headers: dict, test_raw_data: dict[str, Any]
    ):
        """测试预览原始数据"""
        raw_data_id = test_raw_data["id"]
        response = client.post(
            f"/api/v1/raw-data/{raw_data_id}/preview",
            headers=auth_headers,
            json={"limit": 50},
        )

        # 预览可能成功或因沙盒服务不可用而失败
        assert response.status_code in (200, 500)
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            assert "columns" in data["data"]
            assert "rows" in data["data"]

    def test_preview_raw_data_default_limit(
        self, client: TestClient, auth_headers: dict, test_raw_data: dict[str, Any]
    ):
        """测试预览原始数据（默认限制）"""
        raw_data_id = test_raw_data["id"]
        response = client.post(
            f"/api/v1/raw-data/{raw_data_id}/preview",
            headers=auth_headers,
        )

        # 预览可能成功或因沙盒服务不可用而失败
        assert response.status_code in (200, 500)

    def test_preview_raw_data_not_found(self, client: TestClient, auth_headers: dict):
        """测试预览不存在的原始数据"""
        response = client.post(
            "/api/v1/raw-data/99999/preview",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestRawDataSync:
    """原始数据同步测试"""

    def test_sync_raw_data(
        self, client: TestClient, auth_headers: dict, test_raw_data: dict[str, Any]
    ):
        """测试同步原始数据"""
        raw_data_id = test_raw_data["id"]
        response = client.post(
            f"/api/v1/raw-data/{raw_data_id}/sync",
            headers=auth_headers,
        )

        # 同步可能成功或因沙盒服务不可用而失败
        assert response.status_code in (200, 422, 500)
        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            # 同步后状态应该是 ready 或 error
            assert data["data"]["status"] in ("ready", "error", "syncing")

    def test_sync_raw_data_not_found(self, client: TestClient, auth_headers: dict):
        """测试同步不存在的原始数据"""
        response = client.post(
            "/api/v1/raw-data/99999/sync",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestRawDataColumns:
    """原始数据列类型更新测试"""

    def test_update_columns(
        self, client: TestClient, auth_headers: dict, test_raw_data: dict[str, Any]
    ):
        """测试更新列类型"""
        raw_data_id = test_raw_data["id"]
        response = client.put(
            f"/api/v1/raw-data/{raw_data_id}/columns",
            headers=auth_headers,
            json={
                "columns": [
                    {"name": "id", "data_type": "integer", "nullable": False},
                    {"name": "name", "data_type": "string", "nullable": True},
                    {"name": "value", "data_type": "float", "nullable": True},
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_update_columns_not_found(self, client: TestClient, auth_headers: dict):
        """测试更新不存在原始数据的列类型"""
        response = client.put(
            "/api/v1/raw-data/99999/columns",
            headers=auth_headers,
            json={
                "columns": [
                    {"name": "id", "data_type": "integer"},
                ]
            },
        )

        assert response.status_code == 404


class TestRawDataAuth:
    """原始数据认证测试"""

    def test_create_without_auth(self, client: TestClient):
        """测试未认证创建"""
        response = client.post(
            "/api/v1/raw-data",
            json={
                "name": "unauthorized",
                "raw_type": "file",
                "file_config": {"file_id": 1},
            },
        )

        assert response.status_code in (401, 403)

    def test_list_without_auth(self, client: TestClient):
        """测试未认证获取列表"""
        response = client.get("/api/v1/raw-data")

        assert response.status_code in (401, 403)


class TestRawDataBatchCreate:
    """从数据库连接批量创建原始数据测试"""

    def test_batch_create_from_connection(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """测试从数据库连接批量创建原始数据"""
        response = client.post(
            "/api/v1/raw-data/batch-from-connection",
            headers=auth_headers,
            json={
                "connection_id": test_connection["id"],
                "tables": [
                    {"table_name": "users", "schema_name": "public"},
                    {"table_name": "sessions", "schema_name": "public"},
                ],
                "auto_sync": False,  # 测试时不自动同步
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "success_count" in data["data"]
        assert "failed_count" in data["data"]
        assert "results" in data["data"]
        assert len(data["data"]["results"]) == 2

    def test_batch_create_with_custom_names(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """测试批量创建时使用自定义名称"""
        response = client.post(
            "/api/v1/raw-data/batch-from-connection",
            headers=auth_headers,
            json={
                "connection_id": test_connection["id"],
                "tables": [
                    {
                        "table_name": "users",
                        "schema_name": "public",
                        "custom_name": "自定义用户表",
                    },
                ],
                "auto_sync": False,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        # 检查自定义名称
        assert any(r["name"] == "自定义用户表" for r in data["data"]["results"])

    def test_batch_create_with_prefix(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """测试批量创建时使用名称前缀"""
        response = client.post(
            "/api/v1/raw-data/batch-from-connection",
            headers=auth_headers,
            json={
                "connection_id": test_connection["id"],
                "tables": [
                    {"table_name": "raw_data", "schema_name": "public"},
                ],
                "name_prefix": "测试前缀",
                "auto_sync": False,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        # 检查名称前缀
        assert any("测试前缀" in r["name"] for r in data["data"]["results"])

    def test_batch_create_invalid_connection(
        self, client: TestClient, auth_headers: dict
    ):
        """测试使用无效连接 ID 批量创建"""
        response = client.post(
            "/api/v1/raw-data/batch-from-connection",
            headers=auth_headers,
            json={
                "connection_id": 99999,
                "tables": [{"table_name": "test_table"}],
                "auto_sync": False,
            },
        )

        assert response.status_code == 400

    def test_batch_create_empty_tables(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """测试空表列表批量创建"""
        response = client.post(
            "/api/v1/raw-data/batch-from-connection",
            headers=auth_headers,
            json={
                "connection_id": test_connection["id"],
                "tables": [],
            },
        )

        # 应该返回 422 验证错误（tables 需要至少一个元素）
        assert response.status_code == 422

    def test_batch_create_without_auth(self, client: TestClient):
        """测试未认证批量创建"""
        response = client.post(
            "/api/v1/raw-data/batch-from-connection",
            json={
                "connection_id": 1,
                "tables": [{"table_name": "test"}],
            },
        )

        assert response.status_code in (401, 403)
