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
import random
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import numpy as np
import pandas as pd

# API 基础地址
BASE_URL = "http://localhost:8000/api/v1"

# 随机种子确保可重复性
random.seed(42)
np.random.seed(42)


# ==================== 真实模拟数据生成 ====================


def generate_dates(n: int, start_date: str = "2024-01-01") -> list[str]:
    """生成日期序列"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    return [(start + timedelta(days=random.randint(0, 365))).strftime("%Y-%m-%d") for _ in range(n)]


def generate_timestamps(n: int) -> list[str]:
    """生成时间戳序列"""
    base = datetime(2024, 1, 1)
    return [(base + timedelta(seconds=random.randint(0, 365*24*3600))).isoformat() for _ in range(n)]


def create_csv_data() -> tuple[bytes, str]:
    """
    创建电商订单数据 (CSV)
    包含：订单ID、客户ID、商品名称、类别、单价、数量、折扣、总金额、支付方式、订单状态、下单日期
    """
    n = 500  # 500条订单记录
    
    products = [
        ("iPhone 15 Pro", "电子产品", 7999),
        ("MacBook Air M3", "电子产品", 8999),
        ("AirPods Pro", "电子产品", 1899),
        ("Nike Air Max", "运动鞋服", 899),
        ("Adidas 运动裤", "运动鞋服", 399),
        ("优衣库 T恤", "服装", 99),
        ("星巴克咖啡豆", "食品饮料", 128),
        ("三只松鼠坚果", "食品饮料", 68),
        ("科沃斯扫地机", "家电", 2999),
        ("小米空气净化器", "家电", 899),
        ("《深度学习》书籍", "图书", 108),
        ("机械键盘", "电子产品", 599),
        ("显示器支架", "办公用品", 199),
        ("人体工学椅", "办公用品", 1299),
        ("瑜伽垫", "运动鞋服", 89),
    ]
    
    payment_methods = ["支付宝", "微信支付", "银行卡", "信用卡", "花呗"]
    statuses = ["已完成", "已完成", "已完成", "待发货", "运输中", "已取消"]  # 大多数已完成
    
    data = []
    for i in range(n):
        product = random.choice(products)
        quantity = random.randint(1, 5)
        discount = random.choice([0, 0, 0, 0.05, 0.1, 0.15, 0.2])  # 大多数无折扣
        total = round(product[2] * quantity * (1 - discount), 2)
        
        data.append({
            "order_id": f"ORD{2024001000 + i}",
            "customer_id": f"C{random.randint(10001, 10500)}",
            "product_name": product[0],
            "category": product[1],
            "unit_price": product[2],
            "quantity": quantity,
            "discount_rate": discount,
            "total_amount": total,
            "payment_method": random.choice(payment_methods),
            "order_status": random.choice(statuses),
            "order_date": generate_dates(1)[0],
        })
    
    df = pd.DataFrame(data)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8"), "ecommerce_orders.csv"


def create_json_data() -> tuple[bytes, str]:
    """
    创建用户行为日志 (JSON)
    嵌套结构：用户属性、行为事件、设备信息、地理位置
    """
    n = 300  # 300条用户行为记录
    
    event_types = ["page_view", "click", "add_to_cart", "purchase", "search", "login", "logout"]
    pages = ["/home", "/product/123", "/category/electronics", "/cart", "/checkout", "/search", "/user/profile"]
    devices = ["iPhone", "Android", "iPad", "Windows PC", "MacBook"]
    browsers = ["Safari", "Chrome", "Firefox", "Edge"]
    cities = ["北京", "上海", "广州", "深圳", "杭州", "成都", "武汉", "南京", "西安", "重庆"]
    
    records = []
    for i in range(n):
        event = random.choice(event_types)
        
        record = {
            "event_id": f"EVT{1000000 + i}",
            "timestamp": generate_timestamps(1)[0],
            "user": {
                "user_id": f"U{random.randint(1001, 1200)}",
                "is_vip": random.choice([True, False, False, False]),  # 25% VIP
                "registration_days": random.randint(1, 1000),
            },
            "event": {
                "type": event,
                "page": random.choice(pages),
                "duration_seconds": random.randint(1, 300) if event == "page_view" else None,
                "search_query": f"关键词{random.randint(1,100)}" if event == "search" else None,
            },
            "device": {
                "type": random.choice(devices),
                "browser": random.choice(browsers),
                "os_version": f"{random.randint(10, 17)}.{random.randint(0, 5)}",
            },
            "location": {
                "city": random.choice(cities),
                "ip": f"192.168.{random.randint(1,255)}.{random.randint(1,255)}",
            },
        }
        records.append(record)
    
    return json.dumps(records, ensure_ascii=False, indent=2).encode("utf-8"), "user_behavior_logs.json"


def create_parquet_data() -> tuple[bytes, str]:
    """
    创建金融交易数据 (Parquet)
    包含：交易ID、账户、交易类型、金额、余额、汇率、手续费等数值密集型数据
    """
    n = 1000  # 1000条交易记录
    
    transaction_types = ["转账", "消费", "充值", "提现", "理财申购", "理财赎回"]
    currencies = ["CNY", "USD", "EUR", "JPY", "GBP"]
    channels = ["APP", "网银", "ATM", "柜台", "API"]
    
    # 生成数据
    data = {
        "transaction_id": [f"TXN{2024000000 + i}" for i in range(n)],
        "account_id": [f"ACC{random.randint(100001, 100500)}" for _ in range(n)],
        "transaction_type": [random.choice(transaction_types) for _ in range(n)],
        "amount": np.round(np.random.exponential(1000, n), 2),  # 指数分布金额
        "currency": [random.choice(currencies) for _ in range(n)],
        "exchange_rate": np.round(np.where(
            np.random.choice(currencies, n) == "CNY", 
            1.0, 
            np.random.uniform(0.1, 10, n)
        ), 4),
        "fee": np.round(np.random.uniform(0, 50, n), 2),
        "balance_before": np.round(np.random.uniform(1000, 100000, n), 2),
        "channel": [random.choice(channels) for _ in range(n)],
        "is_successful": np.random.choice([True, True, True, True, False], n),  # 80% 成功
        "risk_score": np.round(np.random.uniform(0, 100, n), 1),
        "transaction_time": generate_timestamps(n),
    }
    
    # 计算交易后余额
    data["balance_after"] = np.round(
        data["balance_before"] + np.where(
            np.isin(data["transaction_type"], ["充值", "理财赎回"]),
            data["amount"],
            -data["amount"]
        ) - data["fee"],
        2
    )
    
    df = pd.DataFrame(data)
    
    # 写入 Parquet
    buffer = io.BytesIO()
    df.to_parquet(buffer, index=False, engine="pyarrow")
    return buffer.getvalue(), "financial_transactions.parquet"


def create_sqlite_data() -> tuple[bytes, str]:
    """
    创建关系型数据库 (SQLite)
    多表结构：用户表、商品表、订单表、订单明细表
    """
    temp_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = temp_file.name
    temp_file.close()
    
    conn = sqlite3.connect(db_path)
    
    # 1. 用户表
    users = pd.DataFrame({
        "user_id": range(1, 201),
        "username": [f"user_{i}" for i in range(1, 201)],
        "email": [f"user_{i}@example.com" for i in range(1, 201)],
        "gender": [random.choice(["M", "F"]) for _ in range(200)],
        "age": [random.randint(18, 65) for _ in range(200)],
        "city": [random.choice(["北京", "上海", "广州", "深圳", "杭州"]) for _ in range(200)],
        "vip_level": [random.choice([0, 0, 0, 1, 1, 2, 3]) for _ in range(200)],
        "created_at": generate_dates(200, "2020-01-01"),
    })
    users.to_sql("users", conn, index=False, if_exists="replace")
    
    # 2. 商品表
    products = pd.DataFrame({
        "product_id": range(1, 51),
        "product_name": [
            "智能手机", "笔记本电脑", "无线耳机", "智能手表", "平板电脑",
            "机械键盘", "游戏鼠标", "显示器", "摄像头", "麦克风",
            "运动鞋", "休闲裤", "T恤", "连衣裙", "外套",
            "咖啡", "茶叶", "零食", "水果", "牛奶",
            "书籍", "文具", "背包", "水杯", "雨伞",
            "面膜", "洗面奶", "口红", "香水", "护手霜",
            "床品", "枕头", "毛巾", "拖鞋", "收纳盒",
            "锅具", "餐具", "刀具", "保温杯", "饭盒",
            "玩具", "积木", "拼图", "娃娃", "遥控车",
            "健身器材", "瑜伽垫", "跳绳", "哑铃", "护具",
        ],
        "category": [
            "电子", "电子", "电子", "电子", "电子",
            "电子", "电子", "电子", "电子", "电子",
            "服装", "服装", "服装", "服装", "服装",
            "食品", "食品", "食品", "食品", "食品",
            "文具", "文具", "文具", "文具", "文具",
            "美妆", "美妆", "美妆", "美妆", "美妆",
            "家居", "家居", "家居", "家居", "家居",
            "厨具", "厨具", "厨具", "厨具", "厨具",
            "玩具", "玩具", "玩具", "玩具", "玩具",
            "运动", "运动", "运动", "运动", "运动",
        ],
        "price": [
            4999, 6999, 999, 1999, 3999,
            599, 299, 1999, 399, 599,
            599, 199, 99, 299, 499,
            68, 128, 39, 59, 29,
            49, 19, 199, 49, 39,
            89, 69, 199, 399, 49,
            299, 99, 39, 29, 49,
            199, 89, 129, 69, 39,
            99, 149, 79, 59, 199,
            299, 89, 29, 99, 59,
        ],
        "stock": [random.randint(10, 500) for _ in range(50)],
        "rating": [round(random.uniform(3.5, 5.0), 1) for _ in range(50)],
    })
    products.to_sql("products", conn, index=False, if_exists="replace")
    
    # 3. 订单表
    n_orders = 800
    orders = pd.DataFrame({
        "order_id": range(1, n_orders + 1),
        "user_id": [random.randint(1, 200) for _ in range(n_orders)],
        "order_status": [random.choice(["completed", "completed", "completed", "pending", "cancelled"]) for _ in range(n_orders)],
        "total_amount": [0.0] * n_orders,  # 稍后计算
        "order_date": generate_dates(n_orders),
        "payment_method": [random.choice(["alipay", "wechat", "card"]) for _ in range(n_orders)],
    })
    
    # 4. 订单明细表
    order_items = []
    for order_id in range(1, n_orders + 1):
        n_items = random.randint(1, 5)
        product_ids = random.sample(range(1, 51), n_items)
        order_total = 0
        for product_id in product_ids:
            quantity = random.randint(1, 3)
            price = products.loc[products["product_id"] == product_id, "price"].values[0]
            subtotal = price * quantity
            order_total += subtotal
            order_items.append({
                "order_id": order_id,
                "product_id": product_id,
                "quantity": quantity,
                "unit_price": price,
                "subtotal": subtotal,
            })
        orders.loc[orders["order_id"] == order_id, "total_amount"] = order_total
    
    order_items_df = pd.DataFrame(order_items)
    
    orders.to_sql("orders", conn, index=False, if_exists="replace")
    order_items_df.to_sql("order_items", conn, index=False, if_exists="replace")
    
    conn.close()
    
    with open(db_path, "rb") as f:
        content = f.read()
    
    Path(db_path).unlink(missing_ok=True)
    return content, "ecommerce_database.db"


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
            ("CSV (电商订单)", *create_csv_data(), "text/csv"),
            ("JSON (用户行为)", *create_json_data(), "application/json"),
            ("Parquet (金融交易)", *create_parquet_data(), "application/octet-stream"),
            ("SQLite (电商数据库)", *create_sqlite_data(), "application/x-sqlite3"),
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
            ("电商订单数据", "500条电商订单记录，包含商品、金额、支付方式、订单状态等"),
            ("用户行为日志", "300条用户行为数据，嵌套结构包含用户属性、事件、设备、位置"),
            ("金融交易数据", "1000条金融交易记录，数值密集型数据，适合统计分析"),
            ("电商数据库", "SQLite关系数据库，包含用户表(200)、商品表(50)、订单表(800)、订单明细表"),
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
        
        # 设计多样化的分析问题，覆盖不同场景
        messages = [
            # 测试 SQL 查询功能
            # "电商订单数据中，各类别的销售额排名如何？",
            
            # 更多测试用例（可按需启用）：
            "请分析一下这四个数据源的数据概况，有哪些有趣的发现？",
            # "用金融交易数据生成一个图表，展示交易金额的分布情况",
            # "在电商数据库中，分析VIP用户（vip_level >= 2）的订单情况",
            # "分析用户行为日志，哪些城市的用户最活跃？",
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
                    current_tool = ""
                    text_started = False
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                event_type = data.get("type", "")
                                
                                # Vercel AI SDK Data Stream Protocol 事件处理
                                if event_type == "text-start":
                                    text_started = True
                                    if not ai_response:
                                        print("🤖 AI: ", end="", flush=True)
                                
                                elif event_type == "text-delta":
                                    delta = data.get("delta", "")
                                    if delta:
                                        if not text_started and not ai_response:
                                            print("🤖 AI: ", end="", flush=True)
                                            text_started = True
                                        print(delta, end="", flush=True)
                                        ai_response += delta
                                
                                elif event_type == "text-end":
                                    text_started = False
                                    if ai_response:
                                        print()  # 换行
                                
                                elif event_type == "tool-input-start":
                                    tool_name = data.get("toolName", "unknown")
                                    current_tool = tool_name
                                    print(f"\n   🔧 调用工具: {tool_name}", end="", flush=True)
                                
                                elif event_type == "tool-input-available":
                                    tool_input = data.get("input", {})
                                    input_str = json.dumps(tool_input, ensure_ascii=False)
                                    if len(input_str) > 80:
                                        input_str = input_str[:80] + "..."
                                    print(f" ({input_str})", flush=True)
                                
                                elif event_type == "tool-output-available":
                                    tool_name = data.get("toolName", current_tool)
                                    output = data.get("output", {})
                                    artifact = data.get("artifact")
                                    
                                    # 简化输出显示
                                    output_str = json.dumps(output, ensure_ascii=False)
                                    if len(output_str) > 100:
                                        output_str = output_str[:100] + "..."
                                    
                                    artifact_info = ""
                                    if artifact:
                                        artifact_type = artifact.get("type", "")
                                        artifact_info = f" [artifact: {artifact_type}]"
                                    
                                    print(f"   ✅ {tool_name} 返回: {output_str}{artifact_info}", flush=True)
                                
                                elif event_type == "error":
                                    error_text = data.get("errorText", "Unknown error")
                                    print(f"\n⚠️ Error: {error_text}")
                                    
                            except json.JSONDecodeError:
                                pass
                    
                    if ai_response and not ai_response.endswith("\n"):
                        print()  # 确保换行
                    
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

