#!/usr/bin/env python3
"""
端到端测试：通过 API 测试 quick_analysis 功能

测试流程：
1. 用户登录
2. 上传文件
3. 创建文件类型数据源
4. 调用 Sandbox quick_analysis API
"""

import asyncio
import io
import sqlite3
import tempfile
import time
from pathlib import Path

import httpx
import pandas as pd

BASE_URL = "http://localhost:8000"
SANDBOX_URL = "http://localhost:8080"


def create_sample_dataframe() -> pd.DataFrame:
    """创建示例数据"""
    data = {
        "id": range(1, 51),
        "product": [f"产品_{i}" for i in range(1, 51)],
        "category": ["电子", "服装", "食品", "家居", "运动"] * 10,
        "price": [100 + (i * 10) + (i % 5) * 20 for i in range(50)],
        "quantity": [5 + (i % 20) for i in range(50)],
        "revenue": [(100 + (i * 10)) * (5 + (i % 20)) for i in range(50)],
        "region": ["华东", "华北", "华南", "西南", "西北"] * 10,
    }
    return pd.DataFrame(data)


async def register_and_login() -> tuple[str, int]:
    """注册并登录用户"""
    timestamp = int(time.time())
    username = f"test_quick_{timestamp}"
    password = "Test123456!"
    
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        # 注册
        resp = await client.post("/api/v1/auth/register", json={
            "username": username,
            "password": password,
            "email": f"{username}@test.com",
            "nickname": f"测试用户_{timestamp}"
        })
        reg_data = resp.json()
        if not reg_data.get("success"):
            raise Exception(f"注册失败: {reg_data}")
        
        # 登录
        resp = await client.post("/api/v1/auth/login", json={
            "username": username,
            "password": password
        })
        data = resp.json()
        if not data.get("success"):
            raise Exception(f"登录失败: {data}")
            
        token = data["data"]["access_token"]
        user_id = data["data"]["id"]
        
        return token, user_id


async def upload_file(token: str, file_data: bytes, filename: str, content_type: str) -> tuple[int, str]:
    """上传文件，返回文件ID和object_key"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60) as client:
        files = {"file": (filename, file_data, content_type)}
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = await client.post("/api/v1/files/upload", files=files, headers=headers)
        data = resp.json()
        
        if not data.get("success"):
            raise Exception(f"文件上传失败: {data}")
        
        return data["data"]["id"], data["data"]["object_key"]


async def create_data_source(token: str, name: str, file_id: int, file_type: str) -> dict:
    """创建数据源"""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=30) as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        resp = await client.post("/api/v1/data-sources", headers=headers, json={
            "name": name,
            "source_type": "file",
            "file_type": file_type,
            "file_id": file_id
        })
        data = resp.json()
        
        if not data.get("success"):
            raise Exception(f"数据源创建失败: {data}")
        
        return data["data"]


async def test_sandbox_quick_analysis(object_key: str, file_type: str) -> dict:
    """直接调用 Sandbox 的 quick_analysis API"""
    request_data = {
        "data_source": {
            "source_type": "file",
            "file_type": file_type,
            "object_key": object_key,
            "bucket_name": "data-agent",
        }
    }
    
    async with httpx.AsyncClient(timeout=120) as client:
        response = await client.post(
            f"{SANDBOX_URL}/quick_analysis",
            params={"user_id": 1, "thread_id": 1},
            json=request_data,
        )
        return response.json()


async def main():
    print("\n" + "🚀" * 20)
    print("  Quick Analysis API 端到端测试")
    print("🚀" * 20)
    
    # 1. 登录
    print("\n" + "=" * 60)
    print("📝 步骤 1: 用户登录")
    print("=" * 60)
    token, user_id = await register_and_login()
    print(f"✅ 登录成功, 用户ID: {user_id}")
    
    # 2. 准备测试数据
    df = create_sample_dataframe()
    
    test_cases = []
    
    # CSV
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    test_cases.append({
        "name": "CSV 文件",
        "file_type": "csv",
        "data": csv_buffer.getvalue().encode("utf-8"),
        "filename": "products.csv",
        "content_type": "text/csv"
    })
    
    # JSON
    json_str = df.to_json(orient="records", force_ascii=False)
    test_cases.append({
        "name": "JSON 文件",
        "file_type": "json",
        "data": json_str.encode("utf-8"),
        "filename": "products.json",
        "content_type": "application/json"
    })
    
    # Parquet
    parquet_buffer = io.BytesIO()
    df.to_parquet(parquet_buffer, index=False)
    test_cases.append({
        "name": "Parquet 文件",
        "file_type": "parquet",
        "data": parquet_buffer.getvalue(),
        "filename": "products.parquet",
        "content_type": "application/octet-stream"
    })
    
    # Excel
    excel_buffer = io.BytesIO()
    df.to_excel(excel_buffer, index=False)
    test_cases.append({
        "name": "Excel 文件",
        "file_type": "excel",
        "data": excel_buffer.getvalue(),
        "filename": "products.xlsx",
        "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    })
    
    # SQLite
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    conn = sqlite3.connect(db_path)
    df.to_sql("products", conn, index=False, if_exists="replace")
    conn.close()
    with open(db_path, "rb") as f:
        sqlite_data = f.read()
    Path(db_path).unlink()
    test_cases.append({
        "name": "SQLite 文件",
        "file_type": "sqlite",
        "data": sqlite_data,
        "filename": "products.db",
        "content_type": "application/x-sqlite3"
    })
    
    # 3. 测试每种文件类型
    results = {}
    
    for tc in test_cases:
        print("\n" + "=" * 60)
        print(f"📦 测试: {tc['name']}")
        print("=" * 60)
        
        try:
            # 上传文件
            print(f"   📤 上传文件: {tc['filename']} ({len(tc['data']):,} bytes)")
            file_id, object_key = await upload_file(token, tc["data"], tc["filename"], tc["content_type"])
            print(f"   ✅ 文件ID: {file_id}, object_key: {object_key}")
            
            # 创建数据源
            ds_name = f"测试数据源_{tc['file_type']}_{int(time.time())}"
            ds = await create_data_source(token, ds_name, file_id, tc["file_type"])
            print(f"   ✅ 数据源ID: {ds['id']}")
            
            # 调用 quick_analysis
            print(f"   🔍 调用 Quick Analysis...")
            result = await test_sandbox_quick_analysis(object_key, tc["file_type"])
            
            if result.get("success"):
                analysis = result.get("analysis", {})
                print(f"   ✅ 分析成功!")
                print(f"      - 行数: {analysis.get('row_count', 'N/A')}")
                print(f"      - 列数: {analysis.get('column_count', 'N/A')}")
                
                # 显示数值列统计
                if analysis.get("numeric_summary"):
                    print(f"      - 数值列统计:")
                    for col, stats in list(analysis["numeric_summary"].items())[:3]:
                        print(f"        {col}: 均值={stats.get('mean', 'N/A'):.2f}, "
                              f"标准差={stats.get('std', 'N/A'):.2f}")
                
                results[tc["name"]] = True
            else:
                print(f"   ❌ 分析失败: {result.get('error')}")
                results[tc["name"]] = False
                
        except Exception as e:
            print(f"   ❌ 测试失败: {e}")
            import traceback
            traceback.print_exc()
            results[tc["name"]] = False
    
    # 4. 总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {name:>15}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有 Quick Analysis 测试通过!")
    else:
        print("⚠️ 部分测试失败")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

