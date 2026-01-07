#!/usr/bin/env python3
"""
端到端用户流程测试脚本

步骤：
1. 注册 & 登录
2. 上传 CSV / JSON / Parquet 文件 → 自动创建 RawData
3. 创建 Analysis Session（关联 RawData）
4. 生成任务推荐（初始）
5. Chat 对话（流式 SSE），验证可读数据并总结

运行：
    python scripts/e2e_flow.py --base-url http://localhost:8000/api/v1
"""

import argparse
import asyncio
import json
import uuid
from io import BytesIO

import httpx
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq


def _make_parquet_bytes() -> bytes:
    """构造示例 parquet 数据字节流。"""
    table = pa.Table.from_pandas(
        pd.DataFrame(
            [
                {"id": 1, "name": "Alice", "value": 100},
                {"id": 2, "name": "Bob", "value": 200},
            ]
        )
    )
    sink = BytesIO()
    pq.write_table(table, sink)
    return sink.getvalue()


async def main(base_url: str) -> None:
    uid = uuid.uuid4().hex[:8]
    user = {
        "username": f"e2e_user_{uid}",
        "email": f"e2e_user_{uid}@example.com",
        "nickname": f"E2E {uid}",
        "password": "testpass123",
    }

    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        def _log(step: str, ok: bool, msg: str = "") -> None:
            status = "✅" if ok else "❌"
            print(f"{status} {step}{': ' + msg if msg else ''}")

        # 1. 注册
        r = await client.post("/auth/register", json=user)
        _log("注册", r.status_code == 201, r.text)

        # 2. 登录获取 token
        r = await client.post("/auth/login", json={"username": user["username"], "password": user["password"]})
        data = r.json()
        token = data.get("data", {}).get("access_token", "")
        if not token:
            _log("登录", False, r.text)
            return
        headers = {"Authorization": f"Bearer {token}"}
        _log("登录", r.status_code == 200, "")

        # 3. 上传文件（CSV/JSON/Parquet）→ 自动创建 RawData
        uploads: list[tuple[str, bytes, str]] = [
            ("sample.csv", b"id,name,value\n1,Alice,100\n2,Bob,200\n", "text/csv"),
            ("sample.json", json.dumps([{"id": 1, "name": "Foo"}, {"id": 2, "name": "Bar"}]).encode(), "application/json"),
            ("sample.parquet", _make_parquet_bytes(), "application/octet-stream"),
        ]
        raw_ids: list[str] = []
        for name, content, mime in uploads:
            files = {"file": (name, content, mime)}
            r = await client.post("/files/upload", headers=headers, files=files)
            resp_data = r.json()
            ok = r.status_code in (200, 201) and resp_data.get("success")

            # 检查自动创建的 RawData
            auto_raw_data = resp_data.get("data", {}).get("auto_raw_data")
            if ok and auto_raw_data:
                raw_ids.append(auto_raw_data["id"])
                _log(f"上传 {name}", True, f"auto_raw_data_id={auto_raw_data['id']}")
            else:
                _log(f"上传 {name}", ok, r.text if not ok else "auto_raw_data 未创建")

        if not raw_ids:
            _log("文件上传", False, "没有自动创建的 RawData，停止")
            return

        # 4. 创建 Session（直接关联 RawData，无需创建 DataSource）
        r = await client.post(
            "/sessions",
            headers=headers,
            json={
                "name": f"session_e2e_{uid}",
                "description": "e2e session",
                "raw_data_ids": raw_ids,  # 直接使用 RawData IDs
            },
        )
        if not (r.status_code in (200, 201) and r.json().get("success")):
            _log("创建 Session", False, r.text)
            return
        session_id = r.json()["data"]["id"]
        _log("创建 Session", True, f"id={session_id}")

        # 4.1 校验会话详情
        r = await client.get(f"/sessions/{session_id}", headers=headers)
        if not (r.status_code == 200 and r.json().get("success")):
            _log("校验 Session 详情", False, r.text)
            return
        session_data = r.json().get("data", {})
        raw_data_list = session_data.get("raw_data_list", [])
        if not raw_data_list:
            _log("校验 Session 详情", False, "raw_data_list 为空")
            return
        _log("校验 Session 详情", True, f"raw_data_count={len(raw_data_list)}")

        # 5. 生成初始推荐
        r = await client.post(f"/sessions/{session_id}/recommendations", headers=headers, json={"max_count": 5})
        ok = r.status_code in (200, 201) and r.json().get("success")
        _log("生成任务推荐", ok, r.text if not ok else "")

        # 6. 查询推荐列表
        r = await client.get(f"/sessions/{session_id}/recommendations", headers=headers)
        ok = r.status_code == 200 and r.json().get("success")
        items = r.json().get("data", {}).get("items", []) if ok else []
        _log("查询推荐列表", ok, f"count={len(items)}" if ok else r.text)

        # 7. Chat 对话（流式）- 测试 quick_analysis 工具
        chat_prompt = "分析当前数据的概况, 查看前10行，可视化图表"
        print(f"\n{'='*60}")
        print(f"📝 用户输入: {chat_prompt}")
        print(f"{'='*60}\n")

        try:
            got_text = False
            got_tool = False
            answer_parts: list[str] = []

            async with client.stream(
                "POST",
                f"/sessions/{session_id}/chat",
                headers={**headers, "Accept": "text/event-stream"},
                json={"content": chat_prompt},
                timeout=120.0,
            ) as resp:
                if resp.status_code != 200:
                    _log("Chat 对话", False, f"status={resp.status_code}, body={await resp.aread()}")
                else:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = line[len("data: "):]
                        if payload.strip() == "[DONE]":
                            print("\n📍 [DONE] 流结束")
                            break
                        try:
                            obj = json.loads(payload)
                        except Exception:
                            continue

                        evt_type = obj.get("type")

                        if evt_type == "start":
                            msg_id = obj.get("messageId", "")
                            print(f"📍 [start] 消息开始: {msg_id}")

                        elif evt_type == "text-start":
                            print(f"\n📍 [text-start] 文本开始")
                            print("💬 AI 回复: ", end="", flush=True)

                        elif evt_type == "text-delta":
                            delta = obj.get("delta", "")
                            if delta:
                                got_text = True
                                answer_parts.append(delta)
                                print(delta, end="", flush=True)

                        elif evt_type == "text-end":
                            print(f"\n📍 [text-end] 文本结束")

                        elif evt_type == "tool-input-start":
                            tool_name = obj.get("toolName", "")
                            print(f"\n🔧 [tool-input-start] 工具: {tool_name}")

                        elif evt_type == "tool-output-available":
                            tool_name = obj.get("toolName", "")
                            got_tool = True
                            print(f"\n✅ [tool-output-available] 工具完成: {tool_name}")

                        elif evt_type == "error":
                            error_text = obj.get("errorText", obj.get("error", "未知错误"))
                            print(f"\n❌ [error] 错误: {error_text}")
                            _log("Chat 对话", False, f"error={error_text}")
                            return

                    print(f"\n{'='*60}")
                    answer = "".join(answer_parts).strip()
                    if got_text:
                        preview = (answer[:200] + "...") if len(answer) > 200 else answer
                        _log("Chat 对话", True, f"\n{preview}")
                    elif got_tool:
                        _log("Chat 对话", True, "收到工具输出事件")
                    else:
                        _log("Chat 对话", False, "空响应")

        except Exception as e:
            import traceback
            print(f"\n❌ 异常: {e}")
            traceback.print_exc()
            _log("Chat 对话", False, str(e))

        # 8. 验证消息顺序
        print(f"\n{'='*60}")
        print("📋 验证消息顺序")
        print(f"{'='*60}\n")

        r = await client.get(
            f"/sessions/{session_id}/messages",
            headers=headers,
            params={"page_size": 100},
        )
        if r.status_code == 200 and r.json().get("success"):
            messages = r.json().get("data", {}).get("items", [])
            print(f"共 {len(messages)} 条消息:\n")

            for i, msg in enumerate(messages):
                msg_type = msg.get("message_type", "?")
                seq = msg.get("seq", "?")
                content = msg.get("content", "")[:60].replace("\n", " ")
                type_emoji = {"human": "👤", "ai": "🤖", "tool": "🔧", "system": "⚙️"}.get(msg_type, "❓")
                print(f"{i+1:2}. {type_emoji} [{msg_type:6}] seq={seq}: {content}...")

            seqs = [m.get("seq", 0) for m in messages]
            is_ordered = all(seqs[i] < seqs[i + 1] for i in range(len(seqs) - 1))
            print(f"\n{'='*60}")
            if is_ordered:
                print("✅ seq 序号递增，消息顺序正确！")
            else:
                print("❌ seq 序号未递增")
        else:
            _log("获取消息列表", False, r.text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fast Data Agent E2E Flow")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1", help="后端 API 基础地址")
    args = parser.parse_args()
    asyncio.run(main(args.base_url))
