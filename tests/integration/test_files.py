"""
文件上传 API 测试

测试 /api/v1/files 端点：
- 文件上传
- 文件列表
- 文件详情
- 文件预览
- 文件删除
"""

from typing import Any

from starlette.testclient import TestClient


class TestFileUpload:
    """文件上传测试"""

    def test_upload_csv(self, client: TestClient, auth_headers: dict):
        """测试上传 CSV 文件"""
        csv_content = b"id,name,value\n1,Alice,100\n2,Bob,200"
        files = {"file": ("data.csv", csv_content, "text/csv")}

        response = client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["data"]["original_name"] == "data.csv"

    def test_upload_json(self, client: TestClient, auth_headers: dict):
        """测试上传 JSON 文件"""
        json_content = b'[{"id": 1, "name": "test"}]'
        files = {"file": ("data.json", json_content, "application/json")}

        response = client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files=files,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True

    def test_upload_without_auth(self, client: TestClient):
        """测试未认证上传"""
        csv_content = b"id,name\n1,test"
        files = {"file": ("test.csv", csv_content, "text/csv")}

        response = client.post("/api/v1/files/upload", files=files)

        assert response.status_code in (401, 403)


class TestFileList:
    """文件列表测试"""

    def test_list_files(
        self, client: TestClient, auth_headers: dict, test_file: dict[str, Any]
    ):
        """测试获取文件列表"""
        response = client.get("/api/v1/files", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["total"] >= 1

    def test_list_files_pagination(
        self, client: TestClient, auth_headers: dict, test_file: dict[str, Any]
    ):
        """测试文件列表分页"""
        response = client.get(
            "/api/v1/files",
            headers=auth_headers,
            params={"page": 1, "page_size": 5},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "items" in data["data"]

    def test_list_files_filter(
        self, client: TestClient, auth_headers: dict, test_file: dict[str, Any]
    ):
        """测试文件列表过滤"""
        response = client.get(
            "/api/v1/files",
            headers=auth_headers,
            params={"file_type": "csv"},
        )

        assert response.status_code == 200


class TestFileDetail:
    """文件详情测试"""

    def test_get_file(
        self, client: TestClient, auth_headers: dict, test_file: dict[str, Any]
    ):
        """测试获取文件详情"""
        file_id = test_file["id"]
        response = client.get(f"/api/v1/files/{file_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["data"]["id"] == file_id

    def test_get_file_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在的文件"""
        response = client.get("/api/v1/files/00000000-0000-0000-0000-000000099999", headers=auth_headers)

        assert response.status_code == 404


class TestFilePreview:
    """文件预览测试"""

    def test_preview_file(
        self, client: TestClient, auth_headers: dict, test_file: dict[str, Any]
    ):
        """测试预览文件"""
        file_id = test_file["id"]
        response = client.get(
            f"/api/v1/files/{file_id}/preview",
            headers=auth_headers,
            params={"limit": 10},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_preview_file_not_found(self, client: TestClient, auth_headers: dict):
        """测试预览不存在的文件"""
        response = client.get("/api/v1/files/00000000-0000-0000-0000-000000099999/preview", headers=auth_headers)

        assert response.status_code == 404


class TestFileDownload:
    """文件下载测试"""

    def test_get_download_url(
        self, client: TestClient, auth_headers: dict, test_file: dict[str, Any]
    ):
        """测试获取下载 URL"""
        file_id = test_file["id"]
        response = client.get(f"/api/v1/files/{file_id}/download-url", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # 返回的是直接的 URL 字符串
        assert data["data"].startswith("http")

    def test_get_download_url_not_found(self, client: TestClient, auth_headers: dict):
        """测试获取不存在文件的下载 URL"""
        response = client.get("/api/v1/files/00000000-0000-0000-0000-000000099999/download-url", headers=auth_headers)

        assert response.status_code == 404


class TestFileDelete:
    """文件删除测试"""

    def test_delete_file(self, client: TestClient, auth_headers: dict):
        """测试删除文件"""
        # 先上传一个文件
        csv_content = b"id,name\n1,test"
        files = {"file": ("to_delete.csv", csv_content, "text/csv")}

        upload_response = client.post(
            "/api/v1/files/upload",
            headers=auth_headers,
            files=files,
        )
        file_id = upload_response.json()["data"]["id"]

        # 删除文件
        response = client.delete(f"/api/v1/files/{file_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证已删除
        get_response = client.get(f"/api/v1/files/{file_id}", headers=auth_headers)
        assert get_response.status_code == 404

    def test_delete_file_not_found(self, client: TestClient, auth_headers: dict):
        """测试删除不存在的文件"""
        response = client.delete("/api/v1/files/00000000-0000-0000-0000-000000099999", headers=auth_headers)

        assert response.status_code == 404
