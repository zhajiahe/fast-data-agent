#!/usr/bin/env python3
"""
测试脚本：CSV 上传到 MinIO + DuckDB 直接从 S3 分析

测试内容：
1. MinIO 文件上传/下载
2. DuckDB 直接从 S3 分析（本地调用）
3. Sandbox API quick_analysis 接口（需要 sandbox_runtime 运行）

运行方式：
    cd /data/zhanghuaao/project/fast-data-agent
    source .venv/bin/activate
    python scripts/test_minio_duckdb.py
"""

import asyncio
import io
from pathlib import Path

import duckdb
import httpx
import pandas as pd

# 添加项目根目录到 Python 路径
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.minio import minio_client
from app.core.config import settings


def create_sample_csv() -> tuple[bytes, str]:
    """创建示例 CSV 数据"""
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
    
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    return csv_buffer.getvalue().encode("utf-8"), "test_data.csv"


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


async def test_sandbox_quick_analysis(object_key: str) -> dict | None:
    """测试 Sandbox Runtime 的 quick_analysis 接口"""
    print("\n" + "=" * 60)
    print("🔧 测试 3: Sandbox Runtime quick_analysis 接口")
    print("=" * 60)
    
    sandbox_url = settings.SANDBOX_URL
    print(f"\n📍 Sandbox URL: {sandbox_url}")
    
    # 构建请求数据
    request_data = {
        "data_source": {
            "source_type": "file",
            "file_type": "csv",
            "object_key": object_key,
            "bucket_name": settings.MINIO_BUCKET,
        }
    }
    
    print(f"📤 请求数据: {request_data}")
    
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{sandbox_url}/quick_analysis",
                params={"user_id": 1, "thread_id": 1},
                json=request_data,
            )
            
            result = response.json()
            
            if result.get("success"):
                print("✅ Sandbox API 调用成功")
                analysis = result.get("analysis", {})
                print(f"\n📊 分析结果:")
                print(f"   - 数据源类型: {analysis.get('source_type')}")
                print(f"   - 文件名: {analysis.get('file_name')}")
                print(f"   - 行数: {analysis.get('row_count')}")
                print(f"   - 列数: {analysis.get('column_count')}")
                
                if analysis.get("columns"):
                    print(f"\n   列信息:")
                    for col in analysis["columns"][:5]:  # 只显示前 5 列
                        print(f"      - {col['name']}: {col['dtype']} (空值: {col['null_count']})")
                        if col.get("stats"):
                            stats = col["stats"]
                            print(f"        均值: {stats.get('mean', 'N/A'):.2f}, "
                                  f"标准差: {stats.get('std', 'N/A'):.2f}")
                
                return result
            else:
                print(f"❌ Sandbox API 调用失败: {result.get('error')}")
                return None
                
    except httpx.ConnectError:
        print(f"⚠️ 无法连接到 Sandbox Runtime ({sandbox_url})")
        print("   请确保 sandbox_runtime 正在运行")
        return None
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return None


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
    print("  CSV 上传 MinIO + DuckDB 统计分析 测试")
    print("🚀" * 20)
    
    print(f"\n📍 MinIO 配置:")
    print(f"   - Endpoint: {settings.MINIO_ENDPOINT}")
    print(f"   - Bucket: {settings.MINIO_BUCKET}")
    print(f"   - Secure: {settings.MINIO_SECURE}")
    
    try:
        # Step 1: 创建示例数据
        csv_data, filename = create_sample_csv()
        print(f"\n✅ 示例 CSV 数据已创建 ({len(csv_data):,} bytes)")
        
        # Step 2: 上传到 MinIO
        object_key = await test_upload_to_minio(csv_data, filename)
        
        # Step 3: DuckDB 直接从 S3/MinIO 分析（本地调用）
        analysis_result = test_duckdb_direct_s3_analysis(object_key)
        
        # Step 4: 测试 Sandbox Runtime API（如果可用）
        sandbox_result = await test_sandbox_quick_analysis(object_key)
        
        # Step 5: 清理
        await test_cleanup(object_key)
        
        # 总结
        print("\n" + "=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)
        print(f"\n📊 分析结果摘要:")
        print(f"   - 数据行数: {analysis_result['row_count']}")
        print(f"   - 数据列数: {analysis_result['column_count']}")
        print(f"   - 列名: {', '.join(analysis_result['columns'])}")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)

