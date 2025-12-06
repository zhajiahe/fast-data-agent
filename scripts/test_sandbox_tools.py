#!/usr/bin/env python
"""
沙盒工具端到端测试

测试以下工具:
1. execute_sql - DuckDB SQL 查询
2. execute_python - Python 代码执行
3. generate_chart - Plotly 图表生成
"""

import asyncio
import sys
from pathlib import Path

import httpx

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings

SANDBOX_URL = settings.SANDBOX_URL
TEST_USER_ID = 999
TEST_THREAD_ID = 999


async def test_execute_sql():
    """测试 SQL 执行"""
    print("\n" + "=" * 60)
    print("🔍 测试 execute_sql")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30) as client:
        # 测试 1: 简单查询
        print("\n📌 测试 1: 简单 SELECT 查询")
        response = await client.post(
            f"{SANDBOX_URL}/execute_sql",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
            json={"sql": "SELECT 1 as id, 'hello' as message"},
        )
        result = response.json()
        if result.get("success"):
            print(f"   ✅ 成功: {result.get('columns')} -> {result.get('rows')}")
        else:
            print(f"   ❌ 失败: {result.get('error')}")

        # 测试 2: 创建表并查询
        print("\n📌 测试 2: 创建表并插入数据")
        await client.post(
            f"{SANDBOX_URL}/execute_sql",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
            json={
                "sql": """
                CREATE TABLE IF NOT EXISTS test_sales (
                    id INTEGER,
                    product VARCHAR,
                    price DOUBLE,
                    quantity INTEGER
                );
                INSERT INTO test_sales VALUES 
                    (1, 'Apple', 1.5, 100),
                    (2, 'Banana', 0.8, 150),
                    (3, 'Orange', 2.0, 80);
            """
            },
        )

        response = await client.post(
            f"{SANDBOX_URL}/execute_sql",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
            json={"sql": "SELECT * FROM test_sales ORDER BY id"},
        )
        result = response.json()
        if result.get("success"):
            print(f"   ✅ 成功: {result.get('row_count')} 行")
            for row in result.get("rows", []):
                print(f"      {row}")
        else:
            print(f"   ❌ 失败: {result.get('error')}")

        # 测试 3: 聚合查询
        print("\n📌 测试 3: 聚合查询")
        response = await client.post(
            f"{SANDBOX_URL}/execute_sql",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
            json={
                "sql": """
                SELECT 
                    SUM(price * quantity) as total_value,
                    AVG(price) as avg_price,
                    COUNT(*) as product_count
                FROM test_sales
            """
            },
        )
        result = response.json()
        if result.get("success"):
            print(f"   ✅ 成功: {result.get('columns')}")
            print(f"      {result.get('rows')[0]}")
        else:
            print(f"   ❌ 失败: {result.get('error')}")


async def test_execute_python():
    """测试 Python 代码执行"""
    print("\n" + "=" * 60)
    print("🐍 测试 execute_python")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30) as client:
        # 测试 1: 简单计算
        print("\n📌 测试 1: 简单计算")
        response = await client.post(
            f"{SANDBOX_URL}/execute_python",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
            json={
                "code": """
import math
result = math.sqrt(144)
print(f"sqrt(144) = {result}")
"""
            },
        )
        result = response.json()
        if result.get("success"):
            print(f"   ✅ 成功: {result.get('output').strip()}")
        else:
            print(f"   ❌ 失败: {result.get('error')}")

        # 测试 2: Pandas 数据处理
        print("\n📌 测试 2: Pandas 数据处理")
        response = await client.post(
            f"{SANDBOX_URL}/execute_python",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
            json={
                "code": """
import pandas as pd
import numpy as np

# 创建数据
data = {
    'name': ['Alice', 'Bob', 'Charlie', 'David'],
    'age': [25, 30, 35, 28],
    'salary': [50000, 60000, 75000, 55000]
}
df = pd.DataFrame(data)

print("数据概览:")
print(df.to_string())
print(f"\\n平均年龄: {df['age'].mean():.1f}")
print(f"平均薪资: {df['salary'].mean():.0f}")
"""
            },
        )
        result = response.json()
        if result.get("success"):
            print(f"   ✅ 成功:")
            for line in result.get("output", "").strip().split("\n"):
                print(f"      {line}")
        else:
            print(f"   ❌ 失败: {result.get('error')}")

        # 测试 3: 文件操作
        print("\n📌 测试 3: 文件操作")
        response = await client.post(
            f"{SANDBOX_URL}/execute_python",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
            json={
                "code": """
import pandas as pd
from pathlib import Path

# 创建数据并保存
df = pd.DataFrame({
    'x': [1, 2, 3, 4, 5],
    'y': [10, 20, 15, 30, 25]
})
df.to_csv('test_data.csv', index=False)
print("文件已保存: test_data.csv")

# 读取并显示
df2 = pd.read_csv('test_data.csv')
print(f"读取行数: {len(df2)}")
"""
            },
        )
        result = response.json()
        if result.get("success"):
            print(f"   ✅ 成功:")
            for line in result.get("output", "").strip().split("\n"):
                print(f"      {line}")
        else:
            print(f"   ❌ 失败: {result.get('error')}")


async def test_generate_chart():
    """测试图表生成"""
    print("\n" + "=" * 60)
    print("📊 测试 generate_chart")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=60) as client:
        # 测试 1: 柱状图
        print("\n📌 测试 1: 柱状图")
        response = await client.post(
            f"{SANDBOX_URL}/generate_chart",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
            json={
                "code": """
import plotly.express as px
import pandas as pd

df = pd.DataFrame({
    'product': ['Apple', 'Banana', 'Orange', 'Grape'],
    'sales': [150, 200, 120, 180]
})

fig = px.bar(df, x='product', y='sales', title='产品销售柱状图')
"""
            },
        )
        result = response.json()
        if result.get("success"):
            print(f"   ✅ 成功: 图表保存为 {result.get('chart_file')}")
        else:
            print(f"   ❌ 失败: {result.get('error')}")

        # 测试 2: 折线图
        print("\n📌 测试 2: 折线图")
        response = await client.post(
            f"{SANDBOX_URL}/generate_chart",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
            json={
                "code": """
import plotly.express as px
import pandas as pd

df = pd.DataFrame({
    'month': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
    'revenue': [1000, 1200, 1100, 1500, 1300, 1800]
})

fig = px.line(df, x='month', y='revenue', title='月度收入趋势', markers=True)
"""
            },
        )
        result = response.json()
        if result.get("success"):
            print(f"   ✅ 成功: 图表保存为 {result.get('chart_file')}")
        else:
            print(f"   ❌ 失败: {result.get('error')}")

        # 测试 3: 饼图
        print("\n📌 测试 3: 饼图")
        response = await client.post(
            f"{SANDBOX_URL}/generate_chart",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
            json={
                "code": """
import plotly.express as px
import pandas as pd

df = pd.DataFrame({
    'category': ['电子产品', '服装', '食品', '家居'],
    'percentage': [35, 25, 20, 20]
})

fig = px.pie(df, names='category', values='percentage', title='销售类别分布')
"""
            },
        )
        result = response.json()
        if result.get("success"):
            print(f"   ✅ 成功: 图表保存为 {result.get('chart_file')}")
        else:
            print(f"   ❌ 失败: {result.get('error')}")

        # 测试 4: 散点图
        print("\n📌 测试 4: 散点图")
        response = await client.post(
            f"{SANDBOX_URL}/generate_chart",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
            json={
                "code": """
import plotly.express as px
import pandas as pd
import numpy as np

np.random.seed(42)
df = pd.DataFrame({
    'price': np.random.uniform(10, 100, 50),
    'quantity': np.random.randint(1, 100, 50),
    'category': np.random.choice(['A', 'B', 'C'], 50)
})

fig = px.scatter(df, x='price', y='quantity', color='category', 
                 title='价格 vs 数量 散点图',
                 labels={'price': '价格', 'quantity': '数量'})
"""
            },
        )
        result = response.json()
        if result.get("success"):
            print(f"   ✅ 成功: 图表保存为 {result.get('chart_file')}")
        else:
            print(f"   ❌ 失败: {result.get('error')}")


async def test_list_files():
    """测试列出生成的文件"""
    print("\n" + "=" * 60)
    print("📁 测试生成的文件列表")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(
            f"{SANDBOX_URL}/files",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
        )
        result = response.json()
        if result.get("success"):
            files = result.get("files", [])
            print(f"\n   📂 共 {len(files)} 个文件:")
            for f in files:
                print(f"      - {f['name']} ({f['size']} bytes)")
        else:
            print(f"   ❌ 失败: {result.get('error')}")


async def cleanup():
    """清理测试数据"""
    print("\n" + "=" * 60)
    print("🧹 清理测试数据")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"{SANDBOX_URL}/reset/session",
            params={"user_id": TEST_USER_ID, "thread_id": TEST_THREAD_ID},
        )
        result = response.json()
        if result.get("success"):
            print(f"   ✅ 清理成功: 删除 {result.get('deleted_count', 0)} 个文件")
        else:
            print(f"   ❌ 清理失败: {result.get('error')}")


async def main():
    print("\n" + "🚀" * 30)
    print("  沙盒工具端到端测试")
    print("🚀" * 30)

    # 检查沙盒是否运行
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"{SANDBOX_URL}/")
            if response.status_code != 200:
                print(f"\n❌ 沙盒服务未响应: {response.status_code}")
                return
    except Exception as e:
        print(f"\n❌ 无法连接沙盒服务: {e}")
        print("   请先运行: make sandbox-start")
        return

    print(f"\n✅ 沙盒服务运行中: {SANDBOX_URL}")

    # 运行测试
    await test_execute_sql()
    await test_execute_python()
    await test_generate_chart()
    await test_list_files()
    await cleanup()

    print("\n" + "=" * 60)
    print("✅ 所有测试完成!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())




