"""
数据源 API 集成测试
"""

import uuid

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestDataSourceAPI:
    """数据源 API 测试"""

    def test_create_data_source(self, client: TestClient, auth_headers: dict):
        """测试创建数据源"""
        response = client.post(
            "/api/v1/data-sources",
            json={
                "name": f"测试数据源_{uuid.uuid4().hex[:8]}",
                "description": "这是一个测试数据源",
                "source_type": "database",
                "db_config": {
                    "db_type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "database": "test_db",
                    "username": "test_user",
                    "password": "test_pass",
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["source_type"] == "database"
        assert data["data"]["db_type"] == "postgresql"

    def test_list_data_sources(self, client: TestClient, auth_headers: dict):
        """测试获取数据源列表"""
        # 先创建一个数据源
        client.post(
            "/api/v1/data-sources",
            json={
                "name": f"列表测试数据源_{uuid.uuid4().hex[:8]}",
                "source_type": "database",
                "db_config": {
                    "db_type": "mysql",
                    "host": "localhost",
                    "port": 3306,
                    "database": "test",
                    "username": "root",
                    "password": "root",
                },
            },
            headers=auth_headers,
        )

        # 获取列表
        response = client.get("/api/v1/data-sources", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 1

    def test_get_data_source(self, client: TestClient, auth_headers: dict):
        """测试获取单个数据源"""
        name = f"获取测试数据源_{uuid.uuid4().hex[:8]}"
        # 先创建
        create_response = client.post(
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
        data_source_id = create_response.json()["data"]["id"]

        # 获取
        response = client.get(f"/api/v1/data-sources/{data_source_id}", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == name

    def test_update_data_source(self, client: TestClient, auth_headers: dict):
        """测试更新数据源"""
        # 先创建
        create_response = client.post(
            "/api/v1/data-sources",
            json={
                "name": f"更新原名称_{uuid.uuid4().hex[:8]}",
                "source_type": "database",
                "db_config": {
                    "db_type": "mysql",
                    "host": "localhost",
                    "port": 3306,
                    "database": "test",
                    "username": "root",
                    "password": "root",
                },
            },
            headers=auth_headers,
        )
        data_source_id = create_response.json()["data"]["id"]

        # 更新
        new_name = f"更新新名称_{uuid.uuid4().hex[:8]}"
        response = client.put(
            f"/api/v1/data-sources/{data_source_id}",
            json={"name": new_name, "description": "新描述"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == new_name
        assert data["data"]["description"] == "新描述"

    def test_delete_data_source(self, client: TestClient, auth_headers: dict):
        """测试删除数据源"""
        # 先创建
        create_response = client.post(
            "/api/v1/data-sources",
            json={
                "name": f"待删除数据源_{uuid.uuid4().hex[:8]}",
                "source_type": "database",
                "db_config": {
                    "db_type": "mysql",
                    "host": "localhost",
                    "port": 3306,
                    "database": "test",
                    "username": "root",
                    "password": "root",
                },
            },
            headers=auth_headers,
        )
        data_source_id = create_response.json()["data"]["id"]

        # 删除
        response = client.delete(f"/api/v1/data-sources/{data_source_id}", headers=auth_headers)
        assert response.status_code == 200

        # 验证已删除
        response = client.get(f"/api/v1/data-sources/{data_source_id}", headers=auth_headers)
        assert response.status_code == 404

    def test_create_duplicate_name(self, client: TestClient, auth_headers: dict):
        """测试创建重复名称的数据源"""
        unique_name = f"重复名称数据源_{uuid.uuid4().hex[:8]}"
        # 先创建
        client.post(
            "/api/v1/data-sources",
            json={
                "name": unique_name,
                "source_type": "database",
                "db_config": {
                    "db_type": "mysql",
                    "host": "localhost",
                    "port": 3306,
                    "database": "test",
                    "username": "root",
                    "password": "root",
                },
            },
            headers=auth_headers,
        )

        # 再次创建同名
        response = client.post(
            "/api/v1/data-sources",
            json={
                "name": unique_name,
                "source_type": "database",
                "db_config": {
                    "db_type": "mysql",
                    "host": "localhost",
                    "port": 3306,
                    "database": "test",
                    "username": "root",
                    "password": "root",
                },
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "已存在" in response.json()["msg"]
