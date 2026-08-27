#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
query_demo.py — 跑几个示例分析查询，直观看到数仓产出

用法：
    python scripts/query_demo.py
"""
import duckdb
import sys
from pathlib import Path

# 强制 stdout 用 UTF-8（Windows 中文控制台默认 GBK 会乱码）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

DB = Path(__file__).resolve().parent.parent / "analytics.duckdb"


def show(con, title, sql, fmt=None):
    print(f"\n=== {title} ===")
    rows = con.execute(sql).fetchall()
    if fmt:
        for r in rows:
            print("   " + fmt.format(*r))
    else:
        for r in rows:
            print("   ", r)


def main():
    con = duckdb.connect(str(DB))
    print("===== Payment Analytics 数仓示例查询 =====")

    show(con, "1. 各层模型行数",
         "SELECT 'bronze.raw_payments' t, count(*) c FROM bronze.raw_payments"
         " UNION ALL SELECT 'gold.fct_payments', count(*) FROM main_gold.fct_payments",
         "{0:<24} {1:>10,} 行")

    show(con, "2. 最新一天 KPI（含周环比）",
         "SELECT date_day, gmv_usd, success_rate, gmv_wow_pct"
         " FROM main_marts.daily_kpi ORDER BY date_day DESC LIMIT 3",
         "{0}  GMV=${1:>12,}  成功率={2}  周环比={3}")

    show(con, "3. 渠道失败率（定位渠道质量）",
         "SELECT payment_method, total_payments, failure_rate"
         " FROM main_marts.channel_failure_rate ORDER BY failure_rate DESC",
         "{0:<16} 单量={1:>8,}  失败率={2}")

    show(con, "4. GMV 国家 Top5",
         "SELECT country_code, gmv_usd, net_gmv_usd"
         " FROM main_marts.gmv_by_country LIMIT 5",
         "{0:<4}  GMV=${1:>12,.2f}  净GMV=${2:>12,.2f}")

    show(con, "5. 数据质量审计（清掉了多少脏数据）",
         "SELECT bronze_rows, duplicate_rows_removed, dirty_rows_pct"
         " FROM main_marts.data_quality_audit",
         "Bronze {0:,} 行 | 去重移除 {1:,} 行 | 脏数据率 {2}%")

    show(con, "6. 汇率口径影响（固定 vs 按日）",
         "SELECT rate_strategy, gmv_usd FROM main_marts.currency_rate_impact ORDER BY 1",
         "{0:<14}  GMV=${1:>14,.2f}")

    con.close()
    print("\n查询完成。更多指标见 README §8 指标字典。")


if __name__ == "__main__":
    main()
