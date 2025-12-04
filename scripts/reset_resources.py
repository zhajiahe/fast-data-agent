#!/usr/bin/env python
"""
资源重置脚本

清理以下资源：
1. 数据库中的用户数据（保留管理员账户）
2. MinIO 中的所有文件
3. 沙盒中的所有用户文件
"""

import asyncio
import sys
from pathlib import Path

import httpx
from loguru import logger
from miniopy_async import Minio
from sqlalchemy import text

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.config import settings
from app.core.database import engine as async_engine


async def reset_database():
    """清理数据库中的数据"""
    logger.info("🗃️ 开始清理数据库...")

    async with async_engine.begin() as conn:
        # 按依赖顺序删除数据（先删外键依赖的表）
        tables_to_clear = [
            "task_recommendations",
            "chat_messages",
            "analysis_sessions",
            "data_sources",
            "uploaded_files",
            "users",  # 最后删除用户
        ]

        for table in tables_to_clear:
            try:
                result = await conn.execute(text(f"DELETE FROM {table}"))
                logger.info(f"  ✅ 清理表 {table}: 删除 {result.rowcount} 条记录")
            except Exception as e:
                logger.warning(f"  ⚠️ 清理表 {table} 失败: {e}")

    logger.info("✅ 数据库清理完成")


async def reset_minio():
    """清理 MinIO 中的所有文件"""
    logger.info("📦 开始清理 MinIO...")

    client = Minio(
        settings.MINIO_ENDPOINT,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=settings.MINIO_SECURE,
    )

    bucket = settings.MINIO_BUCKET

    # 检查 bucket 是否存在
    try:
        if not await client.bucket_exists(bucket):
            logger.info(f"  ℹ️ Bucket {bucket} 不存在，无需清理")
            return
    except Exception as e:
        logger.error(f"  ❌ 连接 MinIO 失败: {e}")
        return

    # 列出并删除所有对象
    try:
        objects = []
        async for obj in client.list_objects(bucket, recursive=True):
            objects.append(obj.object_name)

        if objects:
            for obj_name in objects:
                await client.remove_object(bucket, obj_name)
            logger.info(f"  ✅ 删除 {len(objects)} 个文件")
        else:
            logger.info("  ℹ️ MinIO 中没有文件")

    except Exception as e:
        logger.error(f"  ❌ 清理 MinIO 失败: {e}")

    logger.info("✅ MinIO 清理完成")


async def reset_sandbox():
    """清理沙盒中的所有用户文件"""
    logger.info("🧪 开始清理沙盒...")

    sandbox_url = settings.SANDBOX_URL

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            # 通过执行命令清理 sessions 目录
            response = await client.post(
                f"{sandbox_url}/execute",
                params={"user_id": 0, "thread_id": 0},
                json={"command": "rm -rf /app/sessions/* 2>/dev/null; echo 'cleaned'"},
            )
            if response.status_code == 200:
                result = response.json()
                if result.get("exit_code", 0) == 0:
                    logger.info("  ✅ 沙盒 sessions 目录已清理")
                else:
                    logger.warning(f"  ⚠️ 清理命令执行失败: {result.get('stderr', '')}")
            else:
                logger.warning(f"  ⚠️ 沙盒响应: {response.status_code}")
    except httpx.ConnectError:
        logger.warning("  ⚠️ 沙盒服务未运行，跳过清理")
    except Exception as e:
        logger.warning(f"  ⚠️ 清理沙盒失败: {e}")

    logger.info("✅ 沙盒清理完成")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("🔄 资源重置脚本")
    print("=" * 60 + "\n")

    # 确认操作
    print("⚠️  警告: 此操作将删除以下数据:")
    print("  - 数据库中的所有用户数据")
    print("  - MinIO 中的所有上传文件")
    print("  - 沙盒中的所有临时文件")
    print()

    confirm = input("确认执行? (输入 'yes' 继续): ")
    if confirm.lower() != "yes":
        print("❌ 操作已取消")
        return

    print()

    # 执行清理
    await reset_database()
    print()

    await reset_minio()
    print()

    await reset_sandbox()

    print("\n" + "=" * 60)
    print("✅ 所有资源已重置!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())

