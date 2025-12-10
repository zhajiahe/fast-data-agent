#!/usr/bin/env python3
"""
API 接口测试脚本

测试除 chat 和 recommend 外的所有 API Router：
- users (auth): 注册、登录、获取当前用户
- database_connections: CRUD、测试连接
- files: 上传、列表、预览、下载链接
- raw_data: CRUD、预览、同步
- data_sources: CRUD、预览
- sessions: CRUD、归档、文件管理

使用方法:
    python scripts/test_api.py

环境要求:
    - 后端服务运行在 http://localhost:8000
    - PostgreSQL 数据库已启动
    - MinIO 对象存储已启动（用于文件上传测试）
"""

import asyncio
import sys
from dataclasses import dataclass
from typing import Any

import httpx

BASE_URL = "http://localhost:8000/api/v1"
TIMEOUT = 30.0


@dataclass
class TestContext:
    """测试上下文，存储测试过程中的状态"""

    access_token: str = ""
    user_id: int = 0
    connection_id: int = 0
    file_id: int = 0
    raw_data_id: int = 0
    data_source_id: int = 0
    session_id: int = 0


def print_result(test_name: str, success: bool, message: str = ""):
    """打印测试结果"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if message and not success:
        print(f"       └─ {message}")


def check_response(response: httpx.Response, expected_code: int = 200) -> tuple[bool, dict[str, Any]]:
    """检查响应状态"""
    try:
        data = response.json()
        success = response.status_code in (expected_code, 200, 201) and data.get("success", False)
        return success, data
    except Exception as e:
        return False, {"error": str(e)}


class APITester:
    """API 测试器"""

    def __init__(self):
        self.client = httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT)
        self.ctx = TestContext()
        self.results: list[tuple[str, bool]] = []

    async def close(self):
        await self.client.aclose()

    def _headers(self) -> dict[str, str]:
        """获取认证头"""
        if self.ctx.access_token:
            return {"Authorization": f"Bearer {self.ctx.access_token}"}
        return {}

    async def record(self, test_name: str, success: bool, message: str = ""):
        """记录测试结果"""
        self.results.append((test_name, success))
        print_result(test_name, success, message)

    # ==================== Auth 测试 ====================

    async def test_register(self):
        """测试用户注册"""
        response = await self.client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "testuser@example.com",
                "nickname": "Test User",
                "password": "testpass123",
            },
        )
        success, data = check_response(response, 201)
        if success:
            self.ctx.user_id = data.get("data", {}).get("id", 0)
        await self.record("注册用户", success, data.get("msg", ""))

    async def test_login(self):
        """测试用户登录"""
        response = await self.client.post(
            "/auth/login",
            json={"username": "testuser", "password": "testpass123"},
        )
        success, data = check_response(response)
        if success:
            self.ctx.access_token = data.get("data", {}).get("access_token", "")
        await self.record("用户登录", success, data.get("msg", ""))

    async def test_get_me(self):
        """测试获取当前用户信息"""
        response = await self.client.get("/auth/me", headers=self._headers())
        success, data = check_response(response)
        await self.record("获取当前用户", success, data.get("msg", ""))

    async def test_update_me(self):
        """测试更新当前用户信息"""
        response = await self.client.put(
            "/auth/me",
            headers=self._headers(),
            json={"nickname": "Updated User"},
        )
        success, data = check_response(response)
        await self.record("更新当前用户", success, data.get("msg", ""))

    # ==================== Database Connections 测试 ====================

    async def test_create_connection(self):
        """测试创建数据库连接"""
        response = await self.client.post(
            "/database-connections",
            headers=self._headers(),
            json={
                "name": "Test PostgreSQL",
                "description": "测试数据库连接",
                "config": {
                    "db_type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "database": "data_agent",
                    "username": "postgres",
                    "password": "postgres",
                },
            },
        )
        success, data = check_response(response, 201)
        if success:
            self.ctx.connection_id = data.get("data", {}).get("id", 0)
        await self.record("创建数据库连接", success, data.get("msg", ""))

    async def test_list_connections(self):
        """测试获取连接列表"""
        response = await self.client.get("/database-connections", headers=self._headers())
        success, data = check_response(response)
        await self.record("获取连接列表", success, data.get("msg", ""))

    async def test_get_connection(self):
        """测试获取单个连接"""
        if not self.ctx.connection_id:
            await self.record("获取单个连接", False, "无连接 ID")
            return
        response = await self.client.get(
            f"/database-connections/{self.ctx.connection_id}",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("获取单个连接", success, data.get("msg", ""))

    async def test_update_connection(self):
        """测试更新连接"""
        if not self.ctx.connection_id:
            await self.record("更新连接", False, "无连接 ID")
            return
        response = await self.client.put(
            f"/database-connections/{self.ctx.connection_id}",
            headers=self._headers(),
            json={"description": "更新后的描述"},
        )
        success, data = check_response(response)
        await self.record("更新连接", success, data.get("msg", ""))

    async def test_test_connection(self):
        """测试连接测试"""
        if not self.ctx.connection_id:
            await self.record("测试连接", False, "无连接 ID")
            return
        response = await self.client.post(
            f"/database-connections/{self.ctx.connection_id}/test",
            headers=self._headers(),
        )
        success, data = check_response(response)
        test_result = data.get("data", {})
        conn_success = test_result.get("success", False)
        await self.record(
            "测试数据库连接",
            success,
            f"连接{'成功' if conn_success else '失败'}: {test_result.get('message', '')}",
        )

    async def test_get_tables(self):
        """测试获取表列表"""
        if not self.ctx.connection_id:
            await self.record("获取表列表", False, "无连接 ID")
            return
        response = await self.client.get(
            f"/database-connections/{self.ctx.connection_id}/tables",
            headers=self._headers(),
        )
        success, data = check_response(response)
        tables = data.get("data", {}).get("tables", [])
        await self.record("获取表列表", success, f"找到 {len(tables)} 个表")

    # ==================== Files 测试 ====================

    async def test_upload_file(self):
        """测试文件上传"""
        # 创建测试 CSV 内容
        csv_content = b"id,name,value\n1,Alice,100\n2,Bob,200\n3,Charlie,300"
        files = {"file": ("test_data.csv", csv_content, "text/csv")}
        response = await self.client.post(
            "/files/upload",
            headers=self._headers(),
            files=files,
        )
        success, data = check_response(response, 201)
        if success:
            self.ctx.file_id = data.get("data", {}).get("id", 0)
        await self.record("上传文件", success, data.get("msg", ""))

    async def test_list_files(self):
        """测试获取文件列表"""
        response = await self.client.get("/files", headers=self._headers())
        success, data = check_response(response)
        await self.record("获取文件列表", success, data.get("msg", ""))

    async def test_get_file(self):
        """测试获取单个文件"""
        if not self.ctx.file_id:
            await self.record("获取单个文件", False, "无文件 ID")
            return
        response = await self.client.get(
            f"/files/{self.ctx.file_id}",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("获取单个文件", success, data.get("msg", ""))

    async def test_preview_file(self):
        """测试文件预览"""
        if not self.ctx.file_id:
            await self.record("文件预览", False, "无文件 ID")
            return
        response = await self.client.get(
            f"/files/{self.ctx.file_id}/preview",
            headers=self._headers(),
            params={"rows": 10},
        )
        success, data = check_response(response)
        await self.record("文件预览", success, data.get("msg", ""))

    async def test_download_url(self):
        """测试获取下载链接"""
        if not self.ctx.file_id:
            await self.record("获取下载链接", False, "无文件 ID")
            return
        response = await self.client.get(
            f"/files/{self.ctx.file_id}/download-url",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("获取下载链接", success, data.get("msg", ""))

    # ==================== Raw Data 测试 ====================

    async def test_create_raw_data_file(self):
        """测试创建原始数据（文件类型）"""
        if not self.ctx.file_id:
            await self.record("创建原始数据(文件)", False, "无文件 ID")
            return
        response = await self.client.post(
            "/raw-data",
            headers=self._headers(),
            json={
                "name": "test_csv_raw",
                "description": "测试 CSV 原始数据",
                "raw_type": "file",
                "file_config": {"file_id": self.ctx.file_id},
            },
        )
        success, data = check_response(response, 201)
        if success:
            self.ctx.raw_data_id = data.get("data", {}).get("id", 0)
        await self.record("创建原始数据(文件)", success, data.get("msg", ""))

    async def test_list_raw_data(self):
        """测试获取原始数据列表"""
        response = await self.client.get("/raw-data", headers=self._headers())
        success, data = check_response(response)
        await self.record("获取原始数据列表", success, data.get("msg", ""))

    async def test_get_raw_data(self):
        """测试获取单个原始数据"""
        if not self.ctx.raw_data_id:
            await self.record("获取单个原始数据", False, "无原始数据 ID")
            return
        response = await self.client.get(
            f"/raw-data/{self.ctx.raw_data_id}",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("获取单个原始数据", success, data.get("msg", ""))

    async def test_update_raw_data(self):
        """测试更新原始数据"""
        if not self.ctx.raw_data_id:
            await self.record("更新原始数据", False, "无原始数据 ID")
            return
        response = await self.client.put(
            f"/raw-data/{self.ctx.raw_data_id}",
            headers=self._headers(),
            json={"description": "更新后的描述"},
        )
        success, data = check_response(response)
        await self.record("更新原始数据", success, data.get("msg", ""))

    async def test_preview_raw_data(self):
        """测试预览原始数据"""
        if not self.ctx.raw_data_id:
            await self.record("预览原始数据", False, "无原始数据 ID")
            return
        response = await self.client.post(
            f"/raw-data/{self.ctx.raw_data_id}/preview",
            headers=self._headers(),
            json={"limit": 50},
        )
        success, data = check_response(response)
        preview_data = data.get("data", {})
        rows = preview_data.get("rows", [])
        await self.record("预览原始数据", success, f"获取 {len(rows)} 行数据")

    async def test_sync_raw_data(self):
        """测试同步原始数据"""
        if not self.ctx.raw_data_id:
            await self.record("同步原始数据", False, "无原始数据 ID")
            return
        response = await self.client.post(
            f"/raw-data/{self.ctx.raw_data_id}/sync",
            headers=self._headers(),
        )
        success, data = check_response(response)
        status = data.get("data", {}).get("status", "")
        await self.record("同步原始数据", success, f"状态: {status}")

    # ==================== Data Sources 测试 ====================

    async def test_create_data_source(self):
        """测试创建数据源"""
        if not self.ctx.raw_data_id:
            await self.record("创建数据源", False, "无原始数据 ID")
            return
        response = await self.client.post(
            "/data-sources",
            headers=self._headers(),
            json={
                "name": "Test Data Source",
                "description": "测试数据源",
                "category": "fact",
                "target_fields": [
                    {"name": "id", "data_type": "integer", "description": "ID"},
                    {"name": "name", "data_type": "string", "description": "名称"},
                    {"name": "value", "data_type": "integer", "description": "值"},
                ],
                "raw_mappings": [
                    {
                        "raw_data_id": self.ctx.raw_data_id,
                        "mappings": {"id": "id", "name": "name", "value": "value"},
                        "priority": 0,
                        "is_enabled": True,
                    }
                ],
            },
        )
        success, data = check_response(response, 201)
        if success:
            self.ctx.data_source_id = data.get("data", {}).get("id", 0)
        await self.record("创建数据源", success, data.get("msg", ""))

    async def test_list_data_sources(self):
        """测试获取数据源列表"""
        response = await self.client.get("/data-sources", headers=self._headers())
        success, data = check_response(response)
        await self.record("获取数据源列表", success, data.get("msg", ""))

    async def test_get_data_source(self):
        """测试获取单个数据源"""
        if not self.ctx.data_source_id:
            await self.record("获取单个数据源", False, "无数据源 ID")
            return
        response = await self.client.get(
            f"/data-sources/{self.ctx.data_source_id}",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("获取单个数据源", success, data.get("msg", ""))

    async def test_update_data_source(self):
        """测试更新数据源"""
        if not self.ctx.data_source_id:
            await self.record("更新数据源", False, "无数据源 ID")
            return
        response = await self.client.put(
            f"/data-sources/{self.ctx.data_source_id}",
            headers=self._headers(),
            json={"description": "更新后的描述"},
        )
        success, data = check_response(response)
        await self.record("更新数据源", success, data.get("msg", ""))

    async def test_preview_data_source(self):
        """测试预览数据源"""
        if not self.ctx.data_source_id:
            await self.record("预览数据源", False, "无数据源 ID")
            return
        response = await self.client.post(
            f"/data-sources/{self.ctx.data_source_id}/preview",
            headers=self._headers(),
            json={"limit": 50},
        )
        success, data = check_response(response)
        await self.record("预览数据源", success, data.get("msg", ""))

    # ==================== Sessions 测试 ====================

    async def test_create_session(self):
        """测试创建会话"""
        data_source_ids = [self.ctx.data_source_id] if self.ctx.data_source_id else []
        response = await self.client.post(
            "/sessions",
            headers=self._headers(),
            json={
                "name": "Test Session",
                "description": "测试会话",
                "data_source_ids": data_source_ids,
            },
        )
        success, data = check_response(response, 201)
        if success:
            self.ctx.session_id = data.get("data", {}).get("id", 0)
        await self.record("创建会话", success, data.get("msg", ""))

    async def test_list_sessions(self):
        """测试获取会话列表"""
        response = await self.client.get("/sessions", headers=self._headers())
        success, data = check_response(response)
        await self.record("获取会话列表", success, data.get("msg", ""))

    async def test_get_session(self):
        """测试获取单个会话"""
        if not self.ctx.session_id:
            await self.record("获取单个会话", False, "无会话 ID")
            return
        response = await self.client.get(
            f"/sessions/{self.ctx.session_id}",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("获取单个会话", success, data.get("msg", ""))

    async def test_update_session(self):
        """测试更新会话"""
        if not self.ctx.session_id:
            await self.record("更新会话", False, "无会话 ID")
            return
        response = await self.client.put(
            f"/sessions/{self.ctx.session_id}",
            headers=self._headers(),
            json={"description": "更新后的描述"},
        )
        success, data = check_response(response)
        await self.record("更新会话", success, data.get("msg", ""))

    async def test_list_session_files(self):
        """测试获取会话文件列表"""
        if not self.ctx.session_id:
            await self.record("获取会话文件", False, "无会话 ID")
            return
        response = await self.client.get(
            f"/sessions/{self.ctx.session_id}/files",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("获取会话文件", success, data.get("msg", ""))

    async def test_archive_session(self):
        """测试归档会话"""
        if not self.ctx.session_id:
            await self.record("归档会话", False, "无会话 ID")
            return
        response = await self.client.post(
            f"/sessions/{self.ctx.session_id}/archive",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("归档会话", success, data.get("msg", ""))

    # ==================== 清理测试 ====================

    async def test_delete_session(self):
        """测试删除会话"""
        if not self.ctx.session_id:
            await self.record("删除会话", False, "无会话 ID")
            return
        response = await self.client.delete(
            f"/sessions/{self.ctx.session_id}",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("删除会话", success, data.get("msg", ""))

    async def test_delete_data_source(self):
        """测试删除数据源"""
        if not self.ctx.data_source_id:
            await self.record("删除数据源", False, "无数据源 ID")
            return
        response = await self.client.delete(
            f"/data-sources/{self.ctx.data_source_id}",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("删除数据源", success, data.get("msg", ""))

    async def test_delete_raw_data(self):
        """测试删除原始数据"""
        if not self.ctx.raw_data_id:
            await self.record("删除原始数据", False, "无原始数据 ID")
            return
        response = await self.client.delete(
            f"/raw-data/{self.ctx.raw_data_id}",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("删除原始数据", success, data.get("msg", ""))

    async def test_delete_file(self):
        """测试删除文件"""
        if not self.ctx.file_id:
            await self.record("删除文件", False, "无文件 ID")
            return
        response = await self.client.delete(
            f"/files/{self.ctx.file_id}",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("删除文件", success, data.get("msg", ""))

    async def test_delete_connection(self):
        """测试删除连接"""
        if not self.ctx.connection_id:
            await self.record("删除连接", False, "无连接 ID")
            return
        response = await self.client.delete(
            f"/database-connections/{self.ctx.connection_id}",
            headers=self._headers(),
        )
        success, data = check_response(response)
        await self.record("删除连接", success, data.get("msg", ""))

    # ==================== 运行测试 ====================

    async def run_all_tests(self):
        """运行所有测试"""
        print("\n" + "=" * 60)
        print("🧪 API 接口测试")
        print("=" * 60 + "\n")

        # Auth 测试
        print("📋 Auth API")
        print("-" * 40)
        await self.test_register()
        await self.test_login()
        await self.test_get_me()
        await self.test_update_me()
        print()

        # Database Connections 测试
        print("📋 Database Connections API")
        print("-" * 40)
        await self.test_create_connection()
        await self.test_list_connections()
        await self.test_get_connection()
        await self.test_update_connection()
        await self.test_test_connection()
        await self.test_get_tables()
        print()

        # Files 测试
        print("📋 Files API")
        print("-" * 40)
        await self.test_upload_file()
        await self.test_list_files()
        await self.test_get_file()
        await self.test_preview_file()
        await self.test_download_url()
        print()

        # Raw Data 测试
        print("📋 Raw Data API")
        print("-" * 40)
        await self.test_create_raw_data_file()
        await self.test_list_raw_data()
        await self.test_get_raw_data()
        await self.test_update_raw_data()
        await self.test_preview_raw_data()
        await self.test_sync_raw_data()
        print()

        # Data Sources 测试
        print("📋 Data Sources API")
        print("-" * 40)
        await self.test_create_data_source()
        await self.test_list_data_sources()
        await self.test_get_data_source()
        await self.test_update_data_source()
        await self.test_preview_data_source()
        print()

        # Sessions 测试
        print("📋 Sessions API")
        print("-" * 40)
        await self.test_create_session()
        await self.test_list_sessions()
        await self.test_get_session()
        await self.test_update_session()
        await self.test_list_session_files()
        await self.test_archive_session()
        print()

        # 清理测试
        print("📋 清理测试数据")
        print("-" * 40)
        await self.test_delete_session()
        await self.test_delete_data_source()
        await self.test_delete_raw_data()
        await self.test_delete_file()
        await self.test_delete_connection()
        print()

        # 统计结果
        print("=" * 60)
        passed = sum(1 for _, success in self.results if success)
        total = len(self.results)
        print(f"📊 测试结果: {passed}/{total} 通过")

        if passed == total:
            print("🎉 所有测试通过！")
        else:
            failed = [(name, success) for name, success in self.results if not success]
            print(f"⚠️  {len(failed)} 个测试失败:")
            for name, _ in failed:
                print(f"   - {name}")
        print("=" * 60 + "\n")

        return passed == total


async def main():
    """主函数"""
    tester = APITester()
    try:
        success = await tester.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())


