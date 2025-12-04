#!/usr/bin/env python3
"""
模拟用户行为测试脚本

测试完整的用户流程：
1. 用户登录
2. 上传文件 (CSV, JSON, SQLite)
3. 创建数据源
4. 创建分析会话
5. 发送聊天消息让 AI 分析数据

运行方式：
    cd /data/zhanghuaao/project/fast-data-agent
    source .venv/bin/activate
    python scripts/test_user_flow.py
"""

import asyncio
import io
import json
import sqlite3
import tempfile
from pathlib import Path

import httpx
import pandas as pd

# API 基础地址
BASE_URL = "http://localhost:8000/api/v1"


def create_sample_dataframe() -> pd.DataFrame:
    """创建示例数据"""
    return pd.DataFrame({
        "id": range(1, 51),
        "product": [f"产品_{i}" for i in range(1, 51)],
        "category": ["电子", "服装", "食品", "家居", "运动"] * 10,
        "price": [100 + i * 10 for i in range(50)],
        "quantity": [10 + (i % 20) for i in range(50)],
        "revenue": [(100 + i * 10) * (10 + (i % 20)) for i in range(50)],
    })


def create_csv_data() -> tuple[bytes, str]:
    """创建 CSV 数据"""
    df = create_sample_dataframe()
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8"), "sales_data.csv"


def create_json_data() -> tuple[bytes, str]:
    """创建 JSON 数据"""
    df = create_sample_dataframe()
    # 添加一些额外的字段
    df["region"] = ["华北", "华东", "华南", "西南", "西北"] * 10
    return df.to_json(orient="records", force_ascii=False).encode("utf-8"), "regional_sales.json"


def create_sqlite_data() -> tuple[bytes, str]:
    """创建 SQLite 数据"""
    df = create_sample_dataframe()
    df["month"] = ["1月", "2月", "3月", "4月", "5月"] * 10
    
    # 创建临时 SQLite 文件
    temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = temp_file.name
    temp_file.close()
    
    conn = sqlite3.connect(db_path)
    df.to_sql("monthly_sales", conn, index=False, if_exists="replace")
    conn.close()
    
    with open(db_path, "rb") as f:
        content = f.read()
    
    Path(db_path).unlink(missing_ok=True)
    return content, "monthly_sales.db"


class UserFlowTest:
    """用户流程测试类"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=60)
        self.token: str | None = None
        self.user_id: int | None = None
        self.file_ids: list[int] = []
        self.data_source_ids: list[int] = []
        self.session_id: int | None = None
    
    async def close(self):
        await self.client.aclose()
    
    def _headers(self) -> dict:
        """获取带认证的请求头"""
        if self.token:
            return {"Authorization": f"Bearer {self.token}"}
        return {}
    
    async def step1_login(self) -> bool:
        """步骤1: 用户登录"""
        print("\n" + "=" * 60)
        print("📝 步骤 1: 用户登录")
        print("=" * 60)
        
        import time
        timestamp = int(time.time())
        
        # 使用唯一的用户名
        username = f"test_user_{timestamp}"
        
        # 先尝试注册用户
        register_data = {
            "username": username,
            "email": f"test_{timestamp}@example.com",
            "password": "test123456",
            "nickname": "测试用户",
        }
        
        response = await self.client.post(
            f"{BASE_URL}/auth/register",
            json=register_data,
        )
        
        if response.status_code == 201:
            print(f"✅ 用户注册成功: {username}")
        elif response.status_code == 400:
            print("ℹ️ 用户已存在，尝试登录")
        else:
            print(f"⚠️ 注册响应: {response.status_code} - {response.text}")
        
        # 登录
        login_data = {
            "username": username,
            "password": "test123456",
        }
        
        response = await self.client.post(
            f"{BASE_URL}/auth/login",
            json=login_data,
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get("success") and result.get("data"):
                self.token = result["data"]["access_token"]
                print(f"✅ 登录成功")
                
                # 获取用户信息
                me_response = await self.client.get(
                    f"{BASE_URL}/auth/me",
                    headers=self._headers(),
                )
                if me_response.status_code == 200:
                    me_result = me_response.json()
                    if me_result.get("success"):
                        self.user_id = me_result["data"]["id"]
                        print(f"   用户ID: {self.user_id}")
                
                return True
        
        print(f"❌ 登录失败: {response.status_code} - {response.text}")
        return False
    
    async def step2_upload_files(self) -> bool:
        """步骤2: 上传文件"""
        print("\n" + "=" * 60)
        print("📤 步骤 2: 上传文件")
        print("=" * 60)
        
        files_to_upload = [
            ("CSV", *create_csv_data(), "text/csv"),
            ("JSON", *create_json_data(), "application/json"),
            ("SQLite", *create_sqlite_data(), "application/x-sqlite3"),
        ]
        
        success_count = 0
        
        for file_type, content, filename, mime_type in files_to_upload:
            print(f"\n📁 上传 {file_type} 文件: {filename}")
            
            files = {
                "file": (filename, content, mime_type),
            }
            
            response = await self.client.post(
                f"{BASE_URL}/files/upload",
                headers=self._headers(),
                files=files,
            )
            
            if response.status_code == 201:
                result = response.json()
                if result.get("success") and result.get("data"):
                    file_id = result["data"]["id"]
                    self.file_ids.append(file_id)
                    print(f"   ✅ 上传成功, 文件ID: {file_id}")
                    print(f"   - 文件类型: {result['data'].get('file_type')}")
                    print(f"   - 文件大小: {result['data'].get('file_size')} bytes")
                    success_count += 1
                else:
                    print(f"   ❌ 响应错误: {result}")
            else:
                print(f"   ❌ 上传失败: {response.status_code} - {response.text}")
        
        return success_count == len(files_to_upload)
    
    async def step3_create_data_sources(self) -> bool:
        """步骤3: 创建数据源"""
        print("\n" + "=" * 60)
        print("🔗 步骤 3: 创建数据源")
        print("=" * 60)
        
        data_source_configs = [
            ("销售数据(CSV)", "CSV格式的销售数据"),
            ("区域销售(JSON)", "JSON格式的区域销售数据"),
            ("月度销售(SQLite)", "SQLite数据库格式的月度销售数据"),
        ]
        
        success_count = 0
        
        for i, (name, description) in enumerate(data_source_configs):
            if i >= len(self.file_ids):
                break
            
            print(f"\n📊 创建数据源: {name}")
            
            data = {
                "name": name,
                "description": description,
                "source_type": "file",
                "file_id": self.file_ids[i],
            }
            
            response = await self.client.post(
                f"{BASE_URL}/data-sources",
                headers=self._headers(),
                json=data,
            )
            
            if response.status_code == 201:
                result = response.json()
                if result.get("success") and result.get("data"):
                    ds_id = result["data"]["id"]
                    self.data_source_ids.append(ds_id)
                    print(f"   ✅ 创建成功, 数据源ID: {ds_id}")
                    success_count += 1
                else:
                    print(f"   ❌ 响应错误: {result}")
            else:
                print(f"   ❌ 创建失败: {response.status_code} - {response.text}")
        
        return success_count == len(data_source_configs)
    
    async def step4_create_session(self) -> bool:
        """步骤4: 创建分析会话"""
        print("\n" + "=" * 60)
        print("💬 步骤 4: 创建分析会话")
        print("=" * 60)
        
        data = {
            "name": "多数据源分析会话",
            "description": "同时分析CSV、JSON、SQLite数据",
            "data_source_ids": self.data_source_ids,
        }
        
        response = await self.client.post(
            f"{BASE_URL}/sessions",
            headers=self._headers(),
            json=data,
        )
        
        if response.status_code == 201:
            result = response.json()
            if result.get("success") and result.get("data"):
                self.session_id = result["data"]["id"]
                print(f"✅ 会话创建成功")
                print(f"   - 会话ID: {self.session_id}")
                print(f"   - 关联数据源: {self.data_source_ids}")
                return True
            else:
                print(f"❌ 响应错误: {result}")
        else:
            print(f"❌ 创建失败: {response.status_code} - {response.text}")
        
        return False
    
    async def step5_chat_analysis(self) -> bool:
        """步骤5: 发送聊天消息进行分析"""
        print("\n" + "=" * 60)
        print("🤖 步骤 5: AI 分析对话")
        print("=" * 60)
        
        messages = [
            "请分析一下这三个数据源的数据概况",
            "生成一个柱状图，展示各数据源的数据特点",
        ]
        
        for msg in messages:
            print(f"\n👤 用户: {msg}")
            
            # 使用 SSE 流式请求
            url = f"{BASE_URL}/sessions/{self.session_id}/chat"
            
            async with self.client.stream(
                "POST",
                url,
                headers={**self._headers(), "Content-Type": "application/json"},
                json={"content": msg},
            ) as response:
                if response.status_code == 200:
                    ai_response = ""
                    current_tool_call = None
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                mode = data.get("mode", "")
                                
                                # 处理 messages 模式（流式 token）
                                if mode == "messages":
                                    msg_type = data.get("type", "")
                                    content = data.get("content", "")
                                    
                                    # AI 文本流式输出（过滤空白内容）
                                    if "ai" in msg_type.lower() and content and content.strip():
                                        if not ai_response.strip():
                                            print("🤖 AI: ", end="", flush=True)
                                        print(content, end="", flush=True)
                                        ai_response += content
                                    
                                    # AI 决定调用工具
                                    if data.get("tool_calls"):
                                        tool_calls = data["tool_calls"]
                                        for tc in tool_calls:
                                            if tc.get("name"):
                                                current_tool_call = tc["name"]
                                                print(f"\n   🔧 调用工具: {tc['name']}", end="", flush=True)
                                    
                                    # 工具执行结果
                                    if data.get("tool_call_id"):
                                        tool_name = data.get("name", "工具")
                                        tool_content = content[:100] + "..." if len(content) > 100 else content
                                        print(f"\n   ✅ {tool_name} 返回: {tool_content}", flush=True)
                                
                                # 处理 updates 模式（节点状态更新）
                                elif mode == "updates":
                                    node = data.get("node", "")
                                    msgs = data.get("messages", [])
                                    
                                    for m in msgs:
                                        m_type = m.get("type", "")
                                        m_content = m.get("content", "")
                                        
                                        # 工具调用（完整参数）
                                        if m.get("tool_calls"):
                                            for tc in m["tool_calls"]:
                                                args = tc.get("args", {})
                                                args_str = json.dumps(args, ensure_ascii=False)[:80]
                                                print(f" ({args_str})", flush=True)
                                
                                # 处理错误
                                elif "error" in data:
                                    print(f"\n⚠️ Error: {data['error'].get('message', data['error'])}")
                                    
                            except json.JSONDecodeError:
                                pass
                    
                    print()  # 换行
                    
                    if ai_response:
                        print(f"   (响应长度: {len(ai_response)} 字符)")
                else:
                    print(f"❌ 请求失败: {response.status_code}")
                    error_text = await response.aread()
                    print(f"   错误详情: {error_text.decode()[:500]}")
        
        return True
    
    async def cleanup(self):
        """清理测试数据"""
        print("\n" + "=" * 60)
        print("🧹 清理测试数据")
        print("=" * 60)
        
        # 删除会话
        if self.session_id:
            response = await self.client.delete(
                f"{BASE_URL}/sessions/{self.session_id}",
                headers=self._headers(),
            )
            print(f"   删除会话: {'✅' if response.status_code == 200 else '❌'}")
        
        # 删除数据源
        for ds_id in self.data_source_ids:
            response = await self.client.delete(
                f"{BASE_URL}/data-sources/{ds_id}",
                headers=self._headers(),
            )
            print(f"   删除数据源 {ds_id}: {'✅' if response.status_code == 200 else '❌'}")
        
        # 删除文件
        for file_id in self.file_ids:
            response = await self.client.delete(
                f"{BASE_URL}/files/{file_id}",
                headers=self._headers(),
            )
            print(f"   删除文件 {file_id}: {'✅' if response.status_code == 200 else '❌'}")


async def main():
    """主测试流程"""
    print("\n" + "🚀" * 20)
    print("  用户流程完整测试")
    print("🚀" * 20)
    
    test = UserFlowTest()
    
    try:
        # 步骤1: 登录
        if not await test.step1_login():
            print("\n❌ 测试终止: 登录失败")
            return 1
        
        # 步骤2: 上传文件
        if not await test.step2_upload_files():
            print("\n⚠️ 部分文件上传失败")
        
        # 步骤3: 创建数据源
        if not await test.step3_create_data_sources():
            print("\n⚠️ 部分数据源创建失败")
        
        # 步骤4: 创建会话
        if not await test.step4_create_session():
            print("\n❌ 测试终止: 会话创建失败")
            return 1
        
        # 步骤5: AI 分析
        await test.step5_chat_analysis()
        
        # 清理
        # await test.cleanup()
        
        print("\n" + "=" * 60)
        print("✅ 用户流程测试完成!")
        print("=" * 60)
        print(f"\n📊 测试数据保留:")
        print(f"   - 用户ID: {test.user_id}")
        print(f"   - 文件IDs: {test.file_ids}")
        print(f"   - 数据源IDs: {test.data_source_ids}")
        print(f"   - 会话ID: {test.session_id}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        await test.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

