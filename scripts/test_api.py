#!/usr/bin/env python3
"""
API 手动测试脚本

使用方法:
1. 先启动服务器: make dev
2. 运行测试: uv run python scripts/test_api.py
"""

import httpx
from loguru import logger

BASE_URL = "http://localhost:8000/api/v1"


def test_auth():
    """测试认证流程"""
    logger.info("=" * 50)
    logger.info("测试认证流程")
    logger.info("=" * 50)

    # 注册
    response = httpx.post(
        f"{BASE_URL}/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "nickname": "Test User",
            "password": "test123456",
        },
    )
    if response.status_code == 201:
        logger.success("✅ 注册成功")
    elif response.status_code == 400 and "已存在" in response.text:
        logger.info("用户已存在，跳过注册")
    else:
        logger.error(f"❌ 注册失败: {response.text}")
        return None

    # 登录
    response = httpx.post(
        f"{BASE_URL}/auth/login",
        json={"username": "testuser", "password": "test123456"},
    )
    if response.status_code == 200:
        token = response.json()["data"]["access_token"]
        logger.success("✅ 登录成功")
        return token
    else:
        logger.error(f"❌ 登录失败: {response.text}")
        return None


def test_data_sources(token: str) -> int | None:
    """测试数据源 API"""
    logger.info("=" * 50)
    logger.info("测试数据源 API")
    logger.info("=" * 50)

    headers = {"Authorization": f"Bearer {token}"}

    # 创建数据源
    response = httpx.post(
        f"{BASE_URL}/data-sources",
        json={
            "name": "测试 PostgreSQL",
            "description": "测试用数据源",
            "source_type": "database",
            "db_config": {
                "db_type": "postgresql",
                "host": "localhost",
                "port": 5432,
                "database": "data_agent",
                "username": "postgres",
                "password": "postgres123",
            },
        },
        headers=headers,
    )
    if response.status_code == 201:
        ds_id = response.json()["data"]["id"]
        logger.success(f"✅ 创建数据源成功, ID: {ds_id}")
    else:
        logger.error(f"❌ 创建数据源失败: {response.text}")
        return None

    # 获取列表
    response = httpx.get(f"{BASE_URL}/data-sources", headers=headers)
    if response.status_code == 200:
        total = response.json()["data"]["total"]
        logger.success(f"✅ 获取数据源列表成功, 总数: {total}")
    else:
        logger.error(f"❌ 获取数据源列表失败: {response.text}")

    # 测试连接
    response = httpx.post(f"{BASE_URL}/data-sources/{ds_id}/test", headers=headers)
    if response.status_code == 200:
        result = response.json()["data"]
        if result["success"]:
            logger.success(f"✅ 连接测试成功, 延迟: {result['latency_ms']}ms")
        else:
            logger.warning(f"⚠️ 连接测试失败: {result['message']}")
    else:
        logger.error(f"❌ 连接测试请求失败: {response.text}")

    # 同步 Schema
    response = httpx.post(f"{BASE_URL}/data-sources/{ds_id}/sync-schema", headers=headers)
    if response.status_code == 200:
        tables = response.json()["data"]["tables"]
        logger.success(f"✅ Schema 同步成功, 表数量: {len(tables)}")
    else:
        logger.warning(f"⚠️ Schema 同步失败: {response.text}")

    return ds_id


def test_sessions(token: str, ds_id: int) -> int | None:
    """测试会话 API"""
    logger.info("=" * 50)
    logger.info("测试会话 API")
    logger.info("=" * 50)

    headers = {"Authorization": f"Bearer {token}"}

    # 创建会话
    response = httpx.post(
        f"{BASE_URL}/sessions",
        json={
            "name": "测试分析会话",
            "description": "用于测试的分析会话",
            "data_source_ids": [ds_id],
        },
        headers=headers,
    )
    if response.status_code == 201:
        session_id = response.json()["data"]["id"]
        logger.success(f"✅ 创建会话成功, ID: {session_id}")
    else:
        logger.error(f"❌ 创建会话失败: {response.text}")
        return None

    # 获取会话详情
    response = httpx.get(f"{BASE_URL}/sessions/{session_id}", headers=headers)
    if response.status_code == 200:
        data = response.json()["data"]
        ds_count = len(data.get("data_sources", []))
        logger.success(f"✅ 获取会话详情成功, 数据源数量: {ds_count}")
    else:
        logger.error(f"❌ 获取会话详情失败: {response.text}")

    return session_id


def test_chat(token: str, session_id: int):
    """测试对话 API"""
    logger.info("=" * 50)
    logger.info("测试对话 API (Mock)")
    logger.info("=" * 50)

    headers = {"Authorization": f"Bearer {token}"}

    # 获取推荐
    response = httpx.get(f"{BASE_URL}/sessions/{session_id}/recommendations", headers=headers)
    if response.status_code == 200:
        recommendations = response.json()["data"]
        logger.success(f"✅ 获取推荐成功, 数量: {len(recommendations)}")
        for r in recommendations[:3]:
            logger.info(f"   - {r['title']} ({r['category']})")
    else:
        logger.error(f"❌ 获取推荐失败: {response.text}")

    # 发送消息 (SSE)
    logger.info("发送消息 (SSE 流式响应)...")
    with httpx.stream(
        "POST",
        f"{BASE_URL}/sessions/{session_id}/chat",
        json={"content": "帮我分析用户数据"},
        headers=headers,
        timeout=30.0,
    ) as response:
        if response.status_code == 200:
            events = []
            for line in response.iter_lines():
                if line.startswith("data:"):
                    events.append(line)
                    if len(events) <= 5:
                        logger.info(f"   收到事件: {line[:80]}...")
            logger.success(f"✅ 对话流式响应成功, 事件数: {len(events)}")
        else:
            logger.error(f"❌ 对话失败: {response.status_code}")


def main():
    """主函数"""
    logger.info("🚀 开始 API 测试")
    logger.info("")

    # 测试认证
    token = test_auth()
    if not token:
        logger.error("认证失败，停止测试")
        return

    # 测试数据源
    ds_id = test_data_sources(token)
    if not ds_id:
        logger.error("数据源测试失败，停止测试")
        return

    # 测试会话
    session_id = test_sessions(token, ds_id)
    if not session_id:
        logger.error("会话测试失败，停止测试")
        return

    # 测试对话
    test_chat(token, session_id)

    logger.info("")
    logger.info("=" * 50)
    logger.success("🎉 所有测试完成！")
    logger.info("=" * 50)


if __name__ == "__main__":
    main()

