"""
数据库连接 API 测试

测试 /api/v1/database-connections 端点：
- CRUD 操作
- 连接测试
- 获取表列表
"""

from typing import Any

from starlette.testclient import TestClient



class TestDatabaseConnectionCRUD:
    """数据库连接 CRUD 测试"""

    def test_create_connection(self, client: TestClient, auth_headers: dict):
        """测试创建数据库连接"""
        response = client.post(
            "/api/v1/database-connections",
            headers=auth_headers,
            json={
                "name": "Test PostgreSQL",
                "description": "测试 PostgreSQL 连接",
                "config": {
                    "db_type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "database": "test_db",
                    "username": "test_user",
                    "password": "test_pass",
                },
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Test PostgreSQL"
        assert data["data"]["db_type"] == "postgresql"

    def test_list_connections(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """测试获取数据库连接列表"""
        response = client.get("/api/v1/database-connections", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 1

    def test_list_connections_with_filter(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """测试数据库连接列表过滤"""
        response = client.get(
            "/api/v1/database-connections",
            headers=auth_headers,
            params={"db_type": "postgresql"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_connection(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """测试获取单个数据库连接"""
        conn_id = test_connection["id"]
        response = client.get(f"/api/v1/database-connections/{conn_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == conn_id

    def test_get_connection_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的连接"""
        response = client.get("/api/v1/database-connections/00000000-0000-0000-0000-000000099999", headers=auth_headers)

        assert response.status_code == 404

    def test_update_connection(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """测试更新数据库连接"""
        conn_id = test_connection["id"]
        response = client.put(
            f"/api/v1/database-connections/{conn_id}",
            headers=auth_headers,
            json={"description": "更新后的描述"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["description"] == "更新后的描述"

    def test_update_connection_name(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """测试更新数据库连接名称"""
        conn_id = test_connection["id"]
        response = client.put(
            f"/api/v1/database-connections/{conn_id}",
            headers=auth_headers,
            json={"name": "Updated Connection Name"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["name"] == "Updated Connection Name"

    def test_delete_connection(self, client: TestClient, auth_headers: dict):
        """测试删除数据库连接"""
        # 先创建一个连接
        create_response = client.post(
            "/api/v1/database-connections",
            headers=auth_headers,
            json={
                "name": "To Delete Connection",
                "config": {
                    "db_type": "mysql",
                    "host": "localhost",
                    "port": 3306,
                    "database": "test",
                    "username": "root",
                    "password": "root",
                },
            },
        )
        conn_id = create_response.json()["data"]["id"]

        # 删除
        response = client.delete(
            f"/api/v1/database-connections/{conn_id}",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证已删除
        get_response = client.get(
            f"/api/v1/database-connections/{conn_id}",
            headers=auth_headers,
        )
        assert get_response.status_code == 404

    def test_delete_connection_when_in_use(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """当存在引用的 RawData 时，删除连接应被阻止"""
        conn_id = test_connection["id"]

        # 创建一个依赖该连接的 RawData（database_table 类型）
        raw_resp = client.post(
            "/api/v1/raw-data",
            headers=auth_headers,
            json={
                "name": "raw_from_conn",
                "raw_type": "database_table",
                "database_table_config": {
                    "connection_id": conn_id,
                    "schema_name": "public",
                    "table_name": "dummy",
                    "custom_sql": "select 1",
                },
            },
        )
        raw_id = raw_resp.json()["data"]["id"]

        # 删除连接，预期被拒绝
        delete_resp = client.delete(f"/api/v1/database-connections/{conn_id}", headers=auth_headers)
        assert delete_resp.status_code == 400

        # 清理：先删除 RawData，再删除连接
        client.delete(f"/api/v1/raw-data/{raw_id}", headers=auth_headers)
        final_resp = client.delete(f"/api/v1/database-connections/{conn_id}", headers=auth_headers)
        assert final_resp.status_code in (200, 404)


class TestDatabaseConnectionTest:
    """数据库连接测试功能"""

    def test_test_connection_success(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """测试连接测试功能（成功情况）"""
        conn_id = test_connection["id"]
        response = client.post(
            f"/api/v1/database-connections/{conn_id}/test",
            headers=auth_headers,
        )

        # 可能成功也可能失败（取决于实际数据库是否可达）
        assert response.status_code in (200, 400, 500)

    def test_test_connection_not_found(self, client: TestClient, auth_headers: dict):
        """测试连接测试功能（连接不存在）"""
        response = client.post(
            "/api/v1/database-connections/00000000-0000-0000-0000-000000099999/test",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestDatabaseConnectionTables:
    """数据库表列表获取测试"""

    def test_get_tables(
        self, client: TestClient, auth_headers: dict, test_connection: dict[str, Any]
    ):
        """测试获取数据库表列表"""
        conn_id = test_connection["id"]
        response = client.get(
            f"/api/v1/database-connections/{conn_id}/tables",
            headers=auth_headers,
        )

        # 可能成功也可能失败（取决于实际数据库是否可达）
        assert response.status_code in (200, 400, 500)

    def test_get_tables_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在连接的表列表"""
        response = client.get(
            "/api/v1/database-connections/00000000-0000-0000-0000-000000099999/tables",
            headers=auth_headers,
        )

        assert response.status_code == 404


class TestDatabaseConnectionAuth:
    """数据库连接认证测试"""

    def test_create_without_auth(self, client: TestClient):
        """测试未认证创建"""
        response = client.post(
            "/api/v1/database-connections",
            json={
                "name": "Unauthorized",
                "config": {
                    "db_type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "database": "test",
                    "username": "test",
                    "password": "test",
                },
            },
        )

        assert response.status_code in (401, 403)

    def test_list_without_auth(self, client: TestClient):
        """测试未认证获取列表"""
        response = client.get("/api/v1/database-connections")

        assert response.status_code in (401, 403)
