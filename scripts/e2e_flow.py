#!/usr/bin/env python3
"""
端到端用户流程测试脚本

步骤：
1. 注册 & 登录
2. 上传 CSV / JSON / Parquet 文件
3. 基于文件创建 RawData
4. 创建 DataSource（使用其中一个 RawData 做字段映射）
5. 创建 Analysis Session
6. 生成任务推荐（初始）
7. Chat 对话（流式 SSE），验证可读数据并总结

运行：
    python scripts/e2e_flow.py --base-url http://localhost:8000/api/v1
"""

import argparse
import asyncio
import json
import uuid
from io import BytesIO
from typing import Any

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

        # 3. 上传文件（CSV/JSON/Parquet）
        uploads: list[tuple[str, bytes, str]] = [
            ("sample.csv", b"id,name,value\n1,Alice,100\n2,Bob,200\n", "text/csv"),
            ("sample.json", json.dumps([{"id": 1, "name": "Foo"}, {"id": 2, "name": "Bar"}]).encode(), "application/json"),
            ("sample.parquet", _make_parquet_bytes(), "application/octet-stream"),
        ]
        file_ids: list[int] = []
        for name, content, mime in uploads:
            files = {"file": (name, content, mime)}
            r = await client.post("/files/upload", headers=headers, files=files)
            ok = r.status_code in (200, 201) and r.json().get("success")
            _log(f"上传 {name}", ok, r.text if not ok else "")
            if ok:
                file_ids.append(r.json()["data"]["id"])

        if not file_ids:
            _log("文件上传", False, "没有成功的文件，停止")
            return

        # 4. 创建 RawData（分别对应三个文件）
        raw_ids: list[int] = []
        for idx, fid in enumerate(file_ids):
            r = await client.post(
                "/raw-data",
                headers=headers,
                json={
                    "name": f"raw_file_{idx}_{uid}",
                    "description": "e2e raw data",
                    "raw_type": "file",
                    "file_config": {"file_id": fid},
                },
            )
            ok = r.status_code in (200, 201) and r.json().get("success")
            _log(f"创建 RawData {idx}", ok, r.text if not ok else "")
            if ok:
                raw_ids.append(r.json()["data"]["id"])

        if not raw_ids:
            _log("创建 RawData", False, "没有成功的 RawData，停止")
            return

        # 5. 创建 DataSource（使用第一个 RawData 作为字段映射）
        ds_payload = {
            "name": f"ds_e2e_{uid}",
            "description": "e2e data source",
            "category": "fact",
            "target_fields": [
                {"name": "id", "data_type": "integer", "description": "ID"},
                {"name": "name", "data_type": "string", "description": "Name"},
                {"name": "value", "data_type": "integer", "description": "Value"},
            ],
            "raw_mappings": [
                {
                    "raw_data_id": raw_ids[0],
                    "mappings": {"id": "id", "name": "name", "value": "value"},
                    "priority": 0,
                    "is_enabled": True,
                }
            ],
        }
        r = await client.post("/data-sources", headers=headers, json=ds_payload)
        if not (r.status_code in (200, 201) and r.json().get("success")):
            _log("创建 DataSource", False, r.text)
            return
        data_source_id = r.json()["data"]["id"]
        _log("创建 DataSource", True, f"id={data_source_id}")

        # 6. 创建 Session
        r = await client.post(
            "/sessions",
            headers=headers,
            json={
                "name": f"session_e2e_{uid}",
                "description": "e2e session",
                "data_source_id": data_source_id,
            },
        )
        if not (r.status_code in (200, 201) and r.json().get("success")):
            _log("创建 Session", False, r.text)
            return
        session_id = r.json()["data"]["id"]
        _log("创建 Session", True, f"id={session_id}")

        # 6.1 校验会话详情，确保绑定数据源
        r = await client.get(f"/sessions/{session_id}", headers=headers)
        if not (r.status_code == 200 and r.json().get("success")):
            _log("校验 Session 详情", False, r.text)
            return
        ds_ids = r.json().get("data", {}).get("data_source_ids") or []
        if not ds_ids:
            _log("校验 Session 详情", False, "data_source_ids 为空")
            return
        _log("校验 Session 详情", True, f"data_source_ids={ds_ids}")

        # 7. 生成初始推荐
        r = await client.post(f"/sessions/{session_id}/recommendations", headers=headers, json={"max_count": 5})
        ok = r.status_code in (200, 201) and r.json().get("success")
        _log("生成任务推荐", ok, r.text if not ok else "")

        # 8. 查询推荐列表
        r = await client.get(f"/sessions/{session_id}/recommendations", headers=headers)
        ok = r.status_code == 200 and r.json().get("success")
        items = r.json().get("data", {}).get("items", []) if ok else []
        _log("查询推荐列表", ok, f"count={len(items)}" if ok else r.text)

        # 9. Chat 对话（流式）- 测试 quick_analysis 工具
        chat_prompt = "请快速分析当前数据源，告诉我有哪些列和基本统计信息。"
        print(f"\n{'='*60}")
        print(f"📝 用户输入: {chat_prompt}")
        print(f"{'='*60}\n")

        try:
            got_text = False
            got_tool = False
            answer_parts: list[str] = []
            current_text_id: str | None = None

            async with client.stream(
                "POST",
                f"/sessions/{session_id}/chat",
                headers={**headers, "Accept": "text/event-stream"},
                json={"content": chat_prompt},
                timeout=120.0,  # 增加超时时间
            ) as resp:
                if resp.status_code != 200:
                    _log("Chat 对话", False, f"status={resp.status_code}, body={await resp.aread()}")
                else:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        payload = line[len("data: ") :]
                        if payload.strip() == "[DONE]":
                            print("\n📍 [DONE] 流结束")
                            break
                        try:
                            obj = json.loads(payload)
                        except Exception:
                            continue

                        evt_type = obj.get("type")

                        # 消息开始
                        if evt_type == "start":
                            msg_id = obj.get("messageId", "")
                            print(f"📍 [start] 消息开始: {msg_id}")

                        # 步骤控制
                        elif evt_type == "start-step":
                            print(f"\n📍 [start-step] 新步骤开始")

                        elif evt_type == "finish-step":
                            print(f"📍 [finish-step] 步骤结束")

                        elif evt_type == "finish":
                            print(f"📍 [finish] 消息完成")

                        # 文本流
                        elif evt_type == "text-start":
                            text_id = obj.get("id", "")
                            current_text_id = text_id
                            print(f"\n📍 [text-start] 文本开始: {text_id}")
                            print("💬 AI 回复: ", end="", flush=True)

                        elif evt_type == "text-delta":
                            delta = obj.get("delta", "")
                            if delta:
                                got_text = True
                                answer_parts.append(delta)
                                print(delta, end="", flush=True)

                        elif evt_type == "text-end":
                            text_id = obj.get("id", "")
                            print(f"\n📍 [text-end] 文本结束: {text_id}")
                            current_text_id = None

                        # 工具调用
                        elif evt_type == "tool-input-start":
                            tool_call_id = obj.get("toolCallId", "")
                            tool_name = obj.get("toolName", "")
                            print(f"\n🔧 [tool-input-start] 工具调用开始")
                            print(f"   工具: {tool_name}")
                            print(f"   ID: {tool_call_id}")

                        elif evt_type == "tool-input-available":
                            tool_call_id = obj.get("toolCallId", "")
                            tool_name = obj.get("toolName", "")
                            tool_input = obj.get("input", {})
                            print(f"\n🔧 [tool-input-available] 工具参数就绪")
                            print(f"   工具: {tool_name}")
                            print(f"   ID: {tool_call_id}")
                            input_str = json.dumps(tool_input, ensure_ascii=False, indent=2)
                            if len(input_str) > 500:
                                input_str = input_str[:500] + "...(截断)"
                            print(f"   参数: {input_str}")

                        elif evt_type == "tool-output-available":
                            tool_call_id = obj.get("toolCallId", "")
                            tool_name = obj.get("toolName", "")
                            output = obj.get("output", {})
                            artifact = obj.get("artifact", {})
                            got_tool = True

                            print(f"\n✅ [tool-output-available] 工具执行完成")
                            print(f"   工具: {tool_name}")
                            print(f"   ID: {tool_call_id}")

                            # 显示 output (给 LLM 的内容)
                            if output:
                                output_str = json.dumps(output, ensure_ascii=False, indent=2) if isinstance(output, dict) else str(output)
                                if len(output_str) > 800:
                                    output_str = output_str[:800] + "...(截断)"
                                print(f"   输出 (LLM): {output_str}")

                            # 显示 artifact 类型 (给前端的数据)
                            if artifact:
                                artifact_type = artifact.get("type", "unknown") if isinstance(artifact, dict) else "raw"
                                print(f"   Artifact 类型: {artifact_type}")

                        # 流式状态
                        elif evt_type == "stream-status":
                            status = obj.get("status", "")
                            print(f"📍 [stream-status] {status}")

                        # 错误
                        elif evt_type == "error":
                            error_text = obj.get("errorText", obj.get("error", "未知错误"))
                            print(f"\n❌ [error] 错误: {error_text}")
                            _log("Chat 对话", False, f"error={error_text}")
                            return

                        # 其他事件
                        else:
                            if evt_type:
                                print(f"📍 [{evt_type}] {json.dumps(obj, ensure_ascii=False)[:200]}")

                    # 最终结果
                    print(f"\n{'='*60}")
                    answer = "".join(answer_parts).strip()
                    if got_text:
                        if "没有可用的数据源" in answer:
                            _log("Chat 对话", False, "返回提示无数据源，预期应可用")
                            return
                        preview = (answer[:200] + "...") if len(answer) > 200 else answer
                        _log("Chat 对话", True, f"\n{preview}")
                    elif got_tool:
                        _log("Chat 对话", True, "收到工具输出事件（无文本增量）")
                    else:
                        _log("Chat 对话", False, "空响应")

        except Exception as e:
            import traceback
            print(f"\n❌ 异常: {e}")
            traceback.print_exc()
            _log("Chat 对话", False, str(e))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fast Data Agent E2E Flow")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1", help="后端 API 基础地址")
    args = parser.parse_args()
    asyncio.run(main(args.base_url))

