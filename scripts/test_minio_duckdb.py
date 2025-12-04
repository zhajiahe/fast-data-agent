#!/usr/bin/env python3
"""
测试脚本：多种文件格式上传到 MinIO + DuckDB 直接从 S3 分析

测试内容：
1. 文件类型: CSV, JSON, Parquet, Excel
2. 数据库类型: SQLite
3. DuckDB 直接从 S3 分析
4. Sandbox API quick_analysis 接口

运行方式：
    cd /data/zhanghuaao/project/fast-data-agent
    source .venv/bin/activate
    python scripts/test_minio_duckdb.py
"""

import asyncio
import io
import sqlite3
import tempfile
from pathlib import Path

import duckdb
import httpx
import pandas as pd

# 添加项目根目录到 Python 路径
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.minio import minio_client
from app.core.config import settings


def create_sample_dataframe() -> pd.DataFrame:
    """创建示例数据 DataFrame"""
    data = {
        "id": range(1, 101),
        "name": [f"用户_{i}" for i in range(1, 101)],
        "age": [20 + (i % 50) for i in range(100)],
        "salary": [5000 + (i * 100) + (i % 7) * 500 for i in range(100)],
        "department": ["技术", "销售", "运营", "财务", "人事"] * 20,
        "city": ["北京", "上海", "广州", "深圳", "杭州"] * 20,
        "score": [60 + (i % 40) + (i % 3) * 5 for i in range(100)],
    }
    df = pd.DataFrame(data)
    
    # 添加一些空值用于测试
    df.loc[5, "age"] = None
    df.loc[15, "salary"] = None
    df.loc[25, "score"] = None
    
    return df


def create_sample_csv() -> tuple[bytes, str]:
    """创建示例 CSV 数据"""
    df = create_sample_dataframe()
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode("utf-8"), "test_data.csv"


def create_sample_json() -> tuple[bytes, str]:
    """创建示例 JSON 数据"""
    df = create_sample_dataframe()
    json_str = df.to_json(orient="records", force_ascii=False)
    return json_str.encode("utf-8"), "test_data.json"


def create_sample_parquet() -> tuple[bytes, str]:
    """创建示例 Parquet 数据"""
    df = create_sample_dataframe()
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    return buffer.getvalue(), "test_data.parquet"


def create_sample_excel() -> tuple[bytes, str]:
    """创建示例 Excel 数据"""
    df = create_sample_dataframe()
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    return buffer.getvalue(), "test_data.xlsx"


def create_sample_sqlite() -> str:
    """创建示例 SQLite 数据库并返回文件路径"""
    df = create_sample_dataframe()
    
    # 创建临时 SQLite 文件
    temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = temp_file.name
    temp_file.close()
    
    # 写入数据
    conn = sqlite3.connect(db_path)
    df.to_sql("users", conn, index=False, if_exists="replace")
    conn.close()
    
    return db_path


async def test_upload_to_minio(csv_data: bytes, filename: str) -> str:
    """测试上传 CSV 到 MinIO"""
    print("\n" + "=" * 60)
    print("📤 测试 1: 上传 CSV 到 MinIO")
    print("=" * 60)
    
    object_key = f"test/{filename}"
    
    await minio_client.upload_file(
        object_name=object_key,
        data=csv_data,
        length=len(csv_data),
        content_type="text/csv",
    )
    
    print(f"✅ 文件上传成功")
    print(f"   - Bucket: {settings.MINIO_BUCKET}")
    print(f"   - Object Key: {object_key}")
    print(f"   - 文件大小: {len(csv_data):,} bytes")
    
    # 验证文件存在
    exists = await minio_client.file_exists(object_key)
    print(f"   - 文件存在检查: {'✅ 存在' if exists else '❌ 不存在'}")
    
    return object_key


def setup_duckdb_s3() -> duckdb.DuckDBPyConnection:
    """配置 DuckDB 以访问 MinIO (S3 兼容)"""
    conn = duckdb.connect(":memory:")
    
    # 安装并加载 httpfs 扩展
    conn.execute("INSTALL httpfs;")
    conn.execute("LOAD httpfs;")
    
    # 配置 S3 连接参数 (MinIO 兼容)
    conn.execute(f"SET s3_endpoint='{settings.MINIO_ENDPOINT}';")
    conn.execute(f"SET s3_access_key_id='{settings.MINIO_ACCESS_KEY}';")
    conn.execute(f"SET s3_secret_access_key='{settings.MINIO_SECRET_KEY}';")
    conn.execute("SET s3_url_style='path';")  # MinIO 使用 path style
    conn.execute(f"SET s3_use_ssl={'true' if settings.MINIO_SECURE else 'false'};")
    
    return conn


def test_duckdb_direct_s3_analysis(object_key: str) -> dict:
    """使用 DuckDB 直接从 S3/MinIO 分析文件"""
    print("\n" + "=" * 60)
    print("📊 测试 2: DuckDB 直接从 S3/MinIO 分析")
    print("=" * 60)
    
    # 构建 S3 URL
    s3_url = f"s3://{settings.MINIO_BUCKET}/{object_key}"
    print(f"\n📍 S3 URL: {s3_url}")
    
    # 配置 DuckDB S3 连接
    conn = setup_duckdb_s3()
    print("✅ DuckDB S3 连接配置完成")
    
    try:
        # 直接从 S3 读取 CSV 文件
        conn.execute(f"""
            CREATE TABLE data AS 
            SELECT * FROM read_csv_auto('{s3_url}', header=True)
        """)
        print("✅ 直接从 S3 读取数据成功")
        
        # 1. 基本信息
        print("\n📋 基本信息:")
        row_count = conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]
        columns_info = conn.execute("PRAGMA table_info('data')").fetchall()
        
        print(f"   - 总行数: {row_count:,}")
        print(f"   - 总列数: {len(columns_info)}")
        print(f"   - 列名: {[col[1] for col in columns_info]}")
        
        # 2. 数据类型
        print("\n📝 列信息:")
        for col in columns_info:
            col_name, col_type = col[1], col[2]
            null_count = conn.execute(
                f'SELECT COUNT(*) FROM data WHERE "{col_name}" IS NULL'
            ).fetchone()[0]
            print(f"   - {col_name}: {col_type} (空值: {null_count})")
        
        # 3. 数值列统计
        print("\n📈 数值列统计:")
        numeric_cols = ["age", "salary", "score"]
        
        for col in numeric_cols:
            stats = conn.execute(f"""
                SELECT 
                    AVG("{col}") as mean,
                    STDDEV_POP("{col}") as std,
                    MIN("{col}") as min,
                    MAX("{col}") as max,
                    MEDIAN("{col}") as median,
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY "{col}") as q1,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY "{col}") as q3
                FROM data
                WHERE "{col}" IS NOT NULL
            """).fetchone()
            
            print(f"\n   {col}:")
            print(f"      均值: {stats[0]:.2f}")
            print(f"      标准差: {stats[1]:.2f}")
            print(f"      最小值: {stats[2]:.2f}")
            print(f"      最大值: {stats[3]:.2f}")
            print(f"      中位数: {stats[4]:.2f}")
            print(f"      Q1(25%): {stats[5]:.2f}")
            print(f"      Q3(75%): {stats[6]:.2f}")
        
        # 4. 分类统计
        print("\n📊 分类统计:")
        
        # 部门分布
        dept_stats = conn.execute("""
            SELECT department, COUNT(*) as count, AVG(salary) as avg_salary
            FROM data
            GROUP BY department
            ORDER BY count DESC
        """).fetchall()
        
        print("\n   部门分布:")
        for dept, count, avg_salary in dept_stats:
            print(f"      {dept}: {count} 人, 平均薪资 {avg_salary:,.0f}")
        
        # 城市分布
        city_stats = conn.execute("""
            SELECT city, COUNT(*) as count, AVG(age) as avg_age
            FROM data
            GROUP BY city
            ORDER BY count DESC
        """).fetchall()
        
        print("\n   城市分布:")
        for city, count, avg_age in city_stats:
            print(f"      {city}: {count} 人, 平均年龄 {avg_age:.1f}")
        
        # 5. 相关性分析
        print("\n🔗 相关性分析 (age vs salary):")
        corr = conn.execute("""
            SELECT CORR(age, salary) as correlation
            FROM data
            WHERE age IS NOT NULL AND salary IS NOT NULL
        """).fetchone()[0]
        print(f"   相关系数: {corr:.4f}")
        
        # 6. 数据预览
        print("\n👀 数据预览 (前 5 行):")
        preview = conn.execute("SELECT * FROM data LIMIT 5").fetchall()
        columns = [col[1] for col in columns_info]
        
        # 打印表头
        header = " | ".join(f"{col:>10}" for col in columns)
        print(f"   {header}")
        print(f"   {'-' * len(header)}")
        
        # 打印数据
        for row in preview:
            row_str = " | ".join(f"{str(val):>10}" for val in row)
            print(f"   {row_str}")
        
        conn.close()
        
        return {
            "row_count": row_count,
            "column_count": len(columns_info),
            "columns": columns,
        }
        
    except Exception as e:
        conn.close()
        raise e


async def test_sandbox_quick_analysis(object_key: str, file_type: str = "csv") -> dict | None:
    """测试 Sandbox Runtime 的 quick_analysis 接口（文件类型）"""
    print(f"\n📍 Sandbox URL: {settings.SANDBOX_URL}")
    
    # 构建请求数据
    request_data = {
        "data_source": {
            "source_type": "file",
            "file_type": file_type,
            "object_key": object_key,
            "bucket_name": settings.MINIO_BUCKET,
        }
    }
    
    print(f"📤 请求数据: {request_data}")
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{settings.SANDBOX_URL}/quick_analysis",
                params={"user_id": 1, "thread_id": 1},
                json=request_data,
            )
            
            result = response.json()
            
            if result.get("success"):
                print("✅ Sandbox API 调用成功")
                analysis = result.get("analysis", {})
                print(f"   - 行数: {analysis.get('row_count')}, 列数: {analysis.get('column_count')}")
                return result
            else:
                print(f"❌ Sandbox API 调用失败: {result.get('error')}")
                return None
                
    except httpx.ConnectError:
        print(f"⚠️ 无法连接到 Sandbox Runtime")
        return None
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None


async def create_sqlite_in_sandbox() -> str | None:
    """在 Sandbox 容器内创建 SQLite 数据库"""
    # 创建 DataFrame 数据的 Python 代码
    code = '''
import sqlite3
import pandas as pd

# 创建示例数据
data = {
    "id": list(range(1, 101)),
    "name": [f"用户_{i}" for i in range(1, 101)],
    "age": [20 + (i % 50) for i in range(100)],
    "salary": [5000 + (i * 100) + (i % 7) * 500 for i in range(100)],
    "department": ["技术", "销售", "运营", "财务", "人事"] * 20,
    "city": ["北京", "上海", "广州", "深圳", "杭州"] * 20,
}
df = pd.DataFrame(data)

# 创建 SQLite 数据库
db_path = str(WORK_DIR / "test.db")
conn = sqlite3.connect(db_path)
df.to_sql("users", conn, index=False, if_exists="replace")
conn.close()

print(f"SQLite 数据库已创建: {db_path}")
'''
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.SANDBOX_URL}/execute_python",
                params={"user_id": 1, "thread_id": 1},
                json={"code": code},
            )
            result = response.json()
            if result.get("success"):
                # 返回容器内的数据库路径
                return "/app/sessions/1/1/test.db"
            else:
                print(f"❌ 创建 SQLite 失败: {result.get('error')}")
                return None
    except Exception as e:
        print(f"❌ 创建 SQLite 失败: {e}")
        return None


async def test_sandbox_sqlite_analysis(db_path: str) -> dict | None:
    """测试 Sandbox Runtime 的 quick_analysis 接口（SQLite）"""
    print(f"\n📍 Sandbox URL: {settings.SANDBOX_URL}")
    print(f"📁 SQLite 路径 (容器内): {db_path}")
    
    # 构建请求数据
    request_data = {
        "data_source": {
            "source_type": "database",
            "db_type": "sqlite",
            "database": db_path,
        }
    }
    
    print(f"📤 请求数据: {request_data}")
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{settings.SANDBOX_URL}/quick_analysis",
                params={"user_id": 1, "thread_id": 1},
                json=request_data,
            )
            
            result = response.json()
            
            if result.get("success"):
                print("✅ Sandbox API 调用成功")
                analysis = result.get("analysis", {})
                print(f"   - 数据库类型: {analysis.get('db_type')}")
                print(f"   - 表数量: {analysis.get('table_count')}")
                if analysis.get("tables"):
                    for table in analysis["tables"]:
                        print(f"   - 表 {table['table_name']}: {table.get('row_count', 'N/A')} 行")
                return result
            else:
                print(f"❌ Sandbox API 调用失败: {result.get('error')}")
                return None
                
    except httpx.ConnectError:
        print(f"⚠️ 无法连接到 Sandbox Runtime")
        return None
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None


async def test_file_format(file_type: str, create_func, mime_type: str):
    """测试单个文件格式"""
    print("\n" + "=" * 60)
    print(f"📦 测试文件格式: {file_type.upper()}")
    print("=" * 60)
    
    try:
        # 创建文件
        file_data, filename = create_func()
        print(f"✅ 创建 {file_type} 文件: {len(file_data):,} bytes")
        
        # 上传到 MinIO
        object_key = f"test/{filename}"
        await minio_client.upload_file(
            object_name=object_key,
            data=file_data,
            length=len(file_data),
            content_type=mime_type,
        )
        print(f"✅ 上传成功: {object_key}")
        
        # 调用 Sandbox API
        result = await test_sandbox_quick_analysis(object_key, file_type)
        
        # 清理
        await minio_client.delete_file(object_key)
        print(f"✅ 清理完成")
        
        return result is not None
        
    except Exception as e:
        print(f"❌ 测试 {file_type} 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_sqlite():
    """测试 SQLite 数据库"""
    print("\n" + "=" * 60)
    print("📦 测试数据库类型: SQLite")
    print("=" * 60)
    
    try:
        # 在 Sandbox 容器内创建 SQLite 数据库
        print("📝 在 Sandbox 容器内创建 SQLite 数据库...")
        db_path = await create_sqlite_in_sandbox()
        
        if not db_path:
            print("❌ 无法创建 SQLite 数据库")
            return False
        
        print(f"✅ SQLite 数据库已创建: {db_path}")
        
        # 调用 Sandbox API 分析
        result = await test_sandbox_sqlite_analysis(db_path)
        
        return result is not None
        
    except Exception as e:
        print(f"❌ 测试 SQLite 失败: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_cleanup(object_key: str):
    """清理测试数据"""
    print("\n" + "=" * 60)
    print("🧹 测试 4: 清理测试数据")
    print("=" * 60)
    
    await minio_client.delete_file(object_key)
    
    exists = await minio_client.file_exists(object_key)
    print(f"✅ 文件删除成功")
    print(f"   - 文件存在检查: {'❌ 仍存在' if exists else '✅ 已删除'}")


async def main():
    """主测试流程"""
    print("\n" + "🚀" * 20)
    print("  多格式文件 + 数据库 测试")
    print("🚀" * 20)
    
    print(f"\n📍 MinIO 配置:")
    print(f"   - Endpoint: {settings.MINIO_ENDPOINT}")
    print(f"   - Bucket: {settings.MINIO_BUCKET}")
    print(f"   - Secure: {settings.MINIO_SECURE}")
    print(f"   - Sandbox URL: {settings.SANDBOX_URL}")
    
    results = {}
    
    # 测试各种文件格式
    file_tests = [
        ("csv", create_sample_csv, "text/csv"),
        ("json", create_sample_json, "application/json"),
        ("parquet", create_sample_parquet, "application/octet-stream"),
        ("excel", create_sample_excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ]
    
    for file_type, create_func, mime_type in file_tests:
        results[file_type] = await test_file_format(file_type, create_func, mime_type)
    
    # 测试 SQLite
    results["sqlite"] = await test_sqlite()
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果总结")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"   {test_name.upper():>10}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有测试通过!")
    else:
        print("⚠️ 部分测试失败，请检查日志")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

