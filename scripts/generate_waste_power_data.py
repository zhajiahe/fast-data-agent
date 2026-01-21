"""
垃圾发电行业模拟数据生成脚本

数据表设计：
1. waste_collection_daily - 垃圾收集日报
2. power_generation_daily - 发电日报
3. equipment_operation - 设备运行记录
4. environmental_monitoring - 环保监测数据
5. inventory_status - 库存状态

生成 1 年的历史数据，3 个发电厂
"""

import random
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# 设置随机种子以保证可重复性
np.random.seed(42)
random.seed(42)

# 配置
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "waste_power"
START_DATE = date(2024, 1, 1)
END_DATE = date(2024, 12, 31)

# 发电厂信息
PLANTS = [
    {"id": "WTP001", "name": "华东环保能源厂", "region": "华东", "capacity_mw": 50, "furnaces": 3},
    {"id": "WTP002", "name": "华南绿能发电厂", "region": "华南", "capacity_mw": 40, "furnaces": 2},
    {"id": "WTP003", "name": "华北循环经济厂", "region": "华北", "capacity_mw": 60, "furnaces": 4},
]

# 垃圾来源区域
COLLECTION_AREAS = {
    "华东": ["上海市区", "苏州", "无锡", "常州", "南京"],
    "华南": ["广州", "深圳", "东莞", "佛山"],
    "华北": ["北京市区", "天津", "石家庄", "保定", "唐山"],
}

# 垃圾类型
WASTE_TYPES = ["生活垃圾", "工业固废", "医疗废物", "餐厨垃圾"]

# 设备类型
EQUIPMENT_TYPES = [
    {"type": "焚烧炉", "prefix": "FRN"},
    {"type": "汽轮发电机组", "prefix": "TBG"},
    {"type": "烟气处理系统", "prefix": "FGT"},
    {"type": "渗滤液处理", "prefix": "LCT"},
]


def generate_dates():
    """生成日期序列"""
    dates = []
    current = START_DATE
    while current <= END_DATE:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def generate_waste_collection_daily():
    """
    生成垃圾收集日报数据

    字段：
    - date: 日期
    - plant_id: 发电厂ID
    - plant_name: 发电厂名称
    - region: 区域
    - collection_area: 收集区域
    - waste_type: 垃圾类型
    - weight_ton: 收集重量（吨）
    - moisture_pct: 含水率（%）
    - calorific_value: 热值（MJ/kg）
    - transport_cost_yuan: 运输成本（元）
    """
    records = []
    dates = generate_dates()

    for d in dates:
        for plant in PLANTS:
            areas = COLLECTION_AREAS[plant["region"]]
            for area in areas:
                for waste_type in WASTE_TYPES:
                    # 基础收集量（根据工厂容量调整）
                    base_weight = plant["capacity_mw"] * 8 / len(areas) / len(WASTE_TYPES)

                    # 添加季节性波动（夏季垃圾量更大）
                    month = d.month
                    seasonal_factor = 1 + 0.2 * np.sin((month - 4) * np.pi / 6)

                    # 添加周末波动（周末稍少）
                    weekday_factor = 0.9 if d.weekday() >= 5 else 1.0

                    # 不同垃圾类型的比例
                    type_factor = {
                        "生活垃圾": 0.65,
                        "工业固废": 0.20,
                        "医疗废物": 0.05,
                        "餐厨垃圾": 0.10,
                    }[waste_type]

                    weight = (
                        base_weight
                        * seasonal_factor
                        * weekday_factor
                        * type_factor
                        * np.random.uniform(0.85, 1.15)
                    )

                    # 含水率（餐厨垃圾最高）
                    moisture_base = {"生活垃圾": 45, "工业固废": 25, "医疗废物": 35, "餐厨垃圾": 70}[waste_type]
                    moisture = moisture_base + np.random.uniform(-5, 5)

                    # 热值（与含水率负相关）
                    calorific_base = 8 - moisture / 20
                    calorific = calorific_base + np.random.uniform(-0.5, 0.5)

                    # 运输成本
                    transport_cost = weight * np.random.uniform(50, 80)

                    records.append(
                        {
                            "date": d,
                            "plant_id": plant["id"],
                            "plant_name": plant["name"],
                            "region": plant["region"],
                            "collection_area": area,
                            "waste_type": waste_type,
                            "weight_ton": round(weight, 2),
                            "moisture_pct": round(moisture, 1),
                            "calorific_value_mj_kg": round(calorific, 2),
                            "transport_cost_yuan": round(transport_cost, 2),
                        }
                    )

    return pd.DataFrame(records)


def generate_power_generation_daily():
    """
    生成发电日报数据

    字段：
    - date: 日期
    - plant_id: 发电厂ID
    - plant_name: 发电厂名称
    - region: 区域
    - waste_processed_ton: 处理垃圾量（吨）
    - power_generated_mwh: 发电量（MWh）
    - steam_output_ton: 蒸汽产出（吨）
    - thermal_efficiency_pct: 热效率（%）
    - grid_export_mwh: 上网电量（MWh）
    - self_consumption_mwh: 厂用电量（MWh）
    - revenue_yuan: 售电收入（元）
    - operating_hours: 运行小时数
    """
    records = []
    dates = generate_dates()

    for d in dates:
        for plant in PLANTS:
            # 基础日处理量（吨/天）
            base_waste = plant["capacity_mw"] * 8  # 约 8 吨/MW/天

            # 季节性调整（冬季供暖需求，发电量增加）
            month = d.month
            if month in [11, 12, 1, 2]:
                demand_factor = 1.15
            elif month in [6, 7, 8]:
                demand_factor = 0.95
            else:
                demand_factor = 1.0

            # 模拟偶尔的设备检修（随机 5% 的天数有计划检修）
            if np.random.random() < 0.05:
                maintenance_factor = np.random.uniform(0.5, 0.8)
            else:
                maintenance_factor = 1.0

            # 最终处理量
            waste_processed = base_waste * demand_factor * maintenance_factor * np.random.uniform(0.9, 1.05)

            # 发电量（吨垃圾约产 0.3-0.4 MWh）
            efficiency_factor = np.random.uniform(0.32, 0.38)
            power_generated = waste_processed * efficiency_factor

            # 蒸汽产出（发电副产品）
            steam_output = waste_processed * np.random.uniform(2.5, 3.0)

            # 热效率
            thermal_efficiency = 75 + np.random.uniform(-3, 5)

            # 上网电量（扣除厂用电）
            self_consumption = power_generated * np.random.uniform(0.12, 0.18)
            grid_export = power_generated - self_consumption

            # 运行小时数
            operating_hours = 24 * maintenance_factor * np.random.uniform(0.92, 1.0)

            # 售电收入（上网电价约 0.65 元/kWh）
            revenue = grid_export * 1000 * np.random.uniform(0.62, 0.68)

            records.append(
                {
                    "date": d,
                    "plant_id": plant["id"],
                    "plant_name": plant["name"],
                    "region": plant["region"],
                    "waste_processed_ton": round(waste_processed, 2),
                    "power_generated_mwh": round(power_generated, 2),
                    "steam_output_ton": round(steam_output, 2),
                    "thermal_efficiency_pct": round(thermal_efficiency, 1),
                    "grid_export_mwh": round(grid_export, 2),
                    "self_consumption_mwh": round(self_consumption, 2),
                    "operating_hours": round(operating_hours, 1),
                    "revenue_yuan": round(revenue, 2),
                }
            )

    return pd.DataFrame(records)


def generate_equipment_operation():
    """
    生成设备运行记录

    字段：
    - date: 日期
    - plant_id: 发电厂ID
    - equipment_id: 设备ID
    - equipment_type: 设备类型
    - equipment_name: 设备名称
    - status: 运行状态（正常/检修/故障）
    - running_hours: 运行小时数
    - temperature_celsius: 运行温度（摄氏度）
    - pressure_mpa: 压力（MPa）
    - maintenance_flag: 是否需要维护
    """
    records = []
    dates = generate_dates()

    # 为每个工厂生成设备列表
    plant_equipment = {}
    for plant in PLANTS:
        equipment_list = []
        for eq_type in EQUIPMENT_TYPES:
            # 焚烧炉数量根据工厂配置
            count = plant["furnaces"] if eq_type["type"] == "焚烧炉" else 1
            for i in range(count):
                eq_id = f"{eq_type['prefix']}-{plant['id'][-3:]}-{i + 1:02d}"
                equipment_list.append(
                    {"id": eq_id, "type": eq_type["type"], "name": f"{plant['name']}{eq_type['type']}{i + 1}号"}
                )
        plant_equipment[plant["id"]] = equipment_list

    for d in dates:
        for plant in PLANTS:
            for equipment in plant_equipment[plant["id"]]:
                # 状态（95% 正常，3% 检修，2% 故障）
                status_rand = np.random.random()
                if status_rand < 0.95:
                    status = "正常"
                    running_hours = np.random.uniform(22, 24)
                elif status_rand < 0.98:
                    status = "检修"
                    running_hours = np.random.uniform(0, 8)
                else:
                    status = "故障"
                    running_hours = np.random.uniform(0, 4)

                # 温度和压力根据设备类型
                if equipment["type"] == "焚烧炉":
                    temperature = 850 + np.random.uniform(-30, 50)
                    pressure = 0.1 + np.random.uniform(-0.02, 0.02)
                elif equipment["type"] == "汽轮发电机组":
                    temperature = 450 + np.random.uniform(-20, 20)
                    pressure = 4.0 + np.random.uniform(-0.3, 0.3)
                else:
                    temperature = 60 + np.random.uniform(-10, 20)
                    pressure = 0.5 + np.random.uniform(-0.1, 0.1)

                # 维护标志（根据运行时间累计）
                day_of_year = d.timetuple().tm_yday
                maintenance_flag = day_of_year % 30 == 0  # 每月检查

                records.append(
                    {
                        "date": d,
                        "plant_id": plant["id"],
                        "equipment_id": equipment["id"],
                        "equipment_type": equipment["type"],
                        "equipment_name": equipment["name"],
                        "status": status,
                        "running_hours": round(running_hours, 1),
                        "temperature_celsius": round(temperature, 1),
                        "pressure_mpa": round(pressure, 2),
                        "maintenance_flag": 1 if maintenance_flag else 0,
                    }
                )

    return pd.DataFrame(records)


def generate_environmental_monitoring():
    """
    生成环保监测数据

    字段：
    - date: 日期
    - hour: 小时
    - plant_id: 发电厂ID
    - plant_name: 发电厂名称
    - so2_mg_m3: 二氧化硫（mg/m³）
    - nox_mg_m3: 氮氧化物（mg/m³）
    - dust_mg_m3: 烟尘（mg/m³）
    - hcl_mg_m3: 氯化氢（mg/m³）
    - co_mg_m3: 一氧化碳（mg/m³）
    - dioxin_ng_m3: 二噁英（ng/m³）
    - compliant: 是否达标
    """
    records = []
    dates = generate_dates()

    # 国家排放标准限值
    LIMITS = {
        "so2": 80,  # mg/m³
        "nox": 250,  # mg/m³
        "dust": 20,  # mg/m³
        "hcl": 50,  # mg/m³
        "co": 80,  # mg/m³
        "dioxin": 0.1,  # ng/m³
    }

    for d in dates:
        for plant in PLANTS:
            # 每天生成 24 小时数据（简化为每天一条汇总）
            for hour in range(24):
                # 基础排放值（达标范围内）
                so2 = LIMITS["so2"] * np.random.uniform(0.3, 0.7)
                nox = LIMITS["nox"] * np.random.uniform(0.4, 0.8)
                dust = LIMITS["dust"] * np.random.uniform(0.2, 0.6)
                hcl = LIMITS["hcl"] * np.random.uniform(0.2, 0.5)
                co = LIMITS["co"] * np.random.uniform(0.3, 0.6)
                dioxin = LIMITS["dioxin"] * np.random.uniform(0.1, 0.5)

                # 偶尔超标（2% 概率）
                if np.random.random() < 0.02:
                    # 随机选一项轻微超标
                    exceed_item = np.random.choice(["so2", "nox", "dust"])
                    if exceed_item == "so2":
                        so2 = LIMITS["so2"] * np.random.uniform(1.0, 1.2)
                    elif exceed_item == "nox":
                        nox = LIMITS["nox"] * np.random.uniform(1.0, 1.15)
                    else:
                        dust = LIMITS["dust"] * np.random.uniform(1.0, 1.3)

                # 判断是否达标
                compliant = (
                    so2 <= LIMITS["so2"]
                    and nox <= LIMITS["nox"]
                    and dust <= LIMITS["dust"]
                    and hcl <= LIMITS["hcl"]
                    and co <= LIMITS["co"]
                    and dioxin <= LIMITS["dioxin"]
                )

                records.append(
                    {
                        "date": d,
                        "hour": hour,
                        "plant_id": plant["id"],
                        "plant_name": plant["name"],
                        "so2_mg_m3": round(so2, 2),
                        "nox_mg_m3": round(nox, 2),
                        "dust_mg_m3": round(dust, 2),
                        "hcl_mg_m3": round(hcl, 2),
                        "co_mg_m3": round(co, 2),
                        "dioxin_ng_m3": round(dioxin, 4),
                        "compliant": 1 if compliant else 0,
                    }
                )

    return pd.DataFrame(records)


def generate_inventory_status():
    """
    生成库存状态数据

    字段：
    - date: 日期
    - plant_id: 发电厂ID
    - plant_name: 发电厂名称
    - waste_stock_ton: 待处理垃圾库存（吨）
    - slag_stock_ton: 炉渣库存（吨）
    - fly_ash_stock_ton: 飞灰库存（吨）
    - lime_stock_ton: 石灰库存（吨）
    - activated_carbon_kg: 活性炭库存（kg）
    - caustic_soda_ton: 烧碱库存（吨）
    """
    records = []
    dates = generate_dates()

    for plant in PLANTS:
        # 初始库存
        waste_stock = plant["capacity_mw"] * 50
        slag_stock = 500
        fly_ash_stock = 100
        lime_stock = 200
        activated_carbon = 5000
        caustic_soda = 50

        for d in dates:
            # 垃圾入库（收集）和出库（焚烧）
            daily_in = plant["capacity_mw"] * 8 * np.random.uniform(0.9, 1.1)
            daily_out = plant["capacity_mw"] * 8 * np.random.uniform(0.85, 1.05)
            waste_stock = max(0, waste_stock + daily_in - daily_out)

            # 炉渣产出（垃圾量的 15-20%）
            slag_produced = daily_out * np.random.uniform(0.15, 0.20)
            # 炉渣外运（每周集中外运）
            slag_out = slag_stock * 0.3 if d.weekday() == 0 else 0
            slag_stock = slag_stock + slag_produced - slag_out

            # 飞灰产出（垃圾量的 3-5%）
            fly_ash_produced = daily_out * np.random.uniform(0.03, 0.05)
            fly_ash_out = fly_ash_stock * 0.4 if d.weekday() == 2 else 0
            fly_ash_stock = fly_ash_stock + fly_ash_produced - fly_ash_out

            # 辅材消耗和补充
            lime_consumed = daily_out * np.random.uniform(0.01, 0.015)
            lime_restock = 100 if lime_stock < 100 and d.day in [1, 15] else 0
            lime_stock = max(0, lime_stock - lime_consumed + lime_restock)

            ac_consumed = daily_out * np.random.uniform(0.5, 1.0)
            ac_restock = 3000 if activated_carbon < 2000 and d.day in [1, 10, 20] else 0
            activated_carbon = max(0, activated_carbon - ac_consumed + ac_restock)

            cs_consumed = daily_out * np.random.uniform(0.002, 0.004)
            cs_restock = 30 if caustic_soda < 30 and d.day in [5, 20] else 0
            caustic_soda = max(0, caustic_soda - cs_consumed + cs_restock)

            records.append(
                {
                    "date": d,
                    "plant_id": plant["id"],
                    "plant_name": plant["name"],
                    "waste_stock_ton": round(waste_stock, 2),
                    "slag_stock_ton": round(slag_stock, 2),
                    "fly_ash_stock_ton": round(fly_ash_stock, 2),
                    "lime_stock_ton": round(lime_stock, 2),
                    "activated_carbon_kg": round(activated_carbon, 2),
                    "caustic_soda_ton": round(caustic_soda, 2),
                }
            )

    return pd.DataFrame(records)


def main():
    """生成所有数据并保存为 Parquet 文件"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("🚀 开始生成垃圾发电行业模拟数据...")
    print(f"📅 数据时间范围: {START_DATE} 至 {END_DATE}")
    print(f"🏭 发电厂数量: {len(PLANTS)}")
    print()

    # 生成各表数据
    tables = {
        "waste_collection_daily": generate_waste_collection_daily,
        "power_generation_daily": generate_power_generation_daily,
        "equipment_operation": generate_equipment_operation,
        "environmental_monitoring": generate_environmental_monitoring,
        "inventory_status": generate_inventory_status,
    }

    for name, generator in tables.items():
        print(f"📊 生成 {name}...", end=" ")
        df = generator()
        output_path = OUTPUT_DIR / f"{name}.parquet"
        df.to_parquet(output_path, index=False)
        print(f"✅ {len(df):,} 行 -> {output_path}")

    print()
    print("✅ 所有数据生成完成！")
    print(f"📁 输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
