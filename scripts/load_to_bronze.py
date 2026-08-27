#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
load_to_bronze.py — 把 scripts/gen_data.py 产出的 CSV 原样导入 DuckDB bronze 层

职责（对应 03 文档 §5.1 Bronze = ODS，原样贴源）：
  data/payments.csv        → bronze.raw_payments     （表）
  data/users.csv           → bronze.raw_users
  data/merchants.csv       → bronze.raw_merchants
  data/currencies.csv      → bronze.raw_currencies
  data/currency_rates.csv  → bronze.raw_currency_rates

说明：
  - 使用 DuckDB 原生 read_csv（auto_detect），不走 pandas，速度快。
  - 保留原样（不做任何清洗），清洗交给 dbt Silver 层。
  - 幂等：每次执行先 DROP 再重建表。
"""
import argparse
import duckdb
import sys
from pathlib import Path

# 强制 stdout 用 UTF-8（Windows 中文控制台默认 GBK 会乱码）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

TABLES = {
    "payments": "raw_payments",
    "users": "raw_users",
    "merchants": "raw_merchants",
    "currencies": "raw_currencies",
    "currency_rates": "raw_currency_rates",
}


def main():
    ap = argparse.ArgumentParser(description="CSV → DuckDB bronze 层")
    ap.add_argument("--db", type=str, default="analytics.duckdb",
                    help="DuckDB 文件路径（注意用正斜杠）")
    ap.add_argument("--data-dir", type=str, default="data")
    args = ap.parse_args()

    db_path = Path(args.db)
    data_dir = Path(args.data_dir)

    con = duckdb.connect(str(db_path))
    con.execute("CREATE SCHEMA IF NOT EXISTS bronze;")

    print(f"连接 DuckDB: {db_path}（schema=bronze）")
    for csv_name, table in TABLES.items():
        csv_file = data_dir / f"{csv_name}.csv"
        if not csv_file.exists():
            print(f"  [跳过] 缺少 {csv_file}，请先运行 gen_data.py")
            continue
        con.execute(f"DROP TABLE IF EXISTS bronze.{table};")
        con.execute(f"""
            CREATE TABLE bronze.{table} AS
            SELECT * FROM read_csv('{csv_file.as_posix()}', auto_detect=true, header=true)
        """)
        cnt = con.execute(f"SELECT count(*) FROM bronze.{table}").fetchone()[0]
        print(f"  [OK] {csv_file.name} -> bronze.{table}  ({cnt:,} rows)")

    print("\n===== bronze 层验证 =====")
    for table in TABLES.values():
        try:
            cnt = con.execute(f"SELECT count(*) FROM bronze.{table}").fetchone()[0]
            print(f"  bronze.{table:<24}: {cnt:>8,} 行")
        except Exception as e:  # noqa: BLE001
            print(f"  bronze.{table:<24}: 读取失败 → {e}")
    con.close()
    print("\nBronze layer imported. Next: run `dbt run`")


if __name__ == "__main__":
    main()
