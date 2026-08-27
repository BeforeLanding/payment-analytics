#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_pipeline.py — 一键启动 / 重建 Payment Analytics 全流程

用法（在 payment_analytics/ 根目录）：
    python scripts/run_pipeline.py              # 完整流程：造数→入库→建模→测试
    python scripts/run_pipeline.py --skip-gen   # 数据已存在时跳过造数（更快）
    python scripts/run_pipeline.py --skip-test  # 跳过数据质量测试
    python scripts/run_pipeline.py --docs       # 额外生成血缘文档

流程对应 03_方案A开发与进度文档 的 P1~P7：
  1) 造数      scripts/gen_data.py       → data/*.csv（50 万行支付 + 维表，含脏数据）
  2) 入库      scripts/load_to_bronze.py → analytics.duckdb 的 bronze 层
  3) 建模      dbt run                   → bronze→silver→gold→marts（24 个模型）
  4) 测试      dbt test                  → 52 个数据质量测试
  5) 血缘(可选) dbt docs generate         → 浏览器查看血缘图
"""
import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

# 强制 stdout 用 UTF-8（Windows 中文控制台默认 GBK 会乱码）
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent.parent


def find_dbt():
    """找到 dbt 可执行文件（Windows 上常不在 PATH，回退到 Python Scripts 目录）"""
    exe = shutil.which("dbt")
    if exe:
        return exe
    for candidate in [
        Path(sys.executable).parent / "Scripts" / "dbt.exe",
        Path(sys.executable).parent / "Scripts" / "dbt",
        Path(sys.executable).parent / "dbt",
    ]:
        if candidate.exists():
            return str(candidate)
    raise SystemExit("[x] 未找到 dbt，请先: pip install dbt-core dbt-duckdb")


def run_step(step, argv):
    """执行一步，失败即中止"""
    cmd = argv[0]
    label = f"[{step}] {cmd}"
    print(f"\n===== {label} =====")
    t0 = time.time()
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")  # Windows 中文控制台必需
    result = subprocess.run(argv, cwd=ROOT, env=env)
    dt = time.time() - t0
    if result.returncode != 0:
        print(f"!!! {label} 失败 (exit={result.returncode})，请见上方报错。")
        sys.exit(result.returncode)
    print(f"    {label} 完成，耗时 {dt:.1f}s")


def main():
    ap = argparse.ArgumentParser(description="一键启动 Payment Analytics 全流程")
    ap.add_argument("--skip-gen", action="store_true", help="跳过造数（数据已存在时）")
    ap.add_argument("--skip-test", action="store_true", help="跳过 dbt test")
    ap.add_argument("--docs", action="store_true", help="额外生成血缘文档 (dbt docs generate)")
    args = ap.parse_args()

    dbt = find_dbt()
    py = sys.executable

    print("===== Payment Analytics 一键启动 =====")
    print(f"  项目目录: {ROOT}")
    print(f"  Python  : {py}")
    print(f"  dbt     : {dbt}\n")

    if not args.skip_gen:
        run_step("1/5 造数", [py, "scripts/gen_data.py"])
    else:
        print("    跳过造数（--skip-gen）")

    run_step("2/5 入库", [py, "scripts/load_to_bronze.py"])
    run_step("3/5 建模", [dbt, "run"])
    if not args.skip_test:
        run_step("4/5 测试", [dbt, "test"])
    else:
        print("    跳过测试（--skip-test）")
    if args.docs:
        run_step("5/5 血缘文档", [dbt, "docs", "generate"])

    print("\n===== 启动完成 =====")
    print("  下一步：")
    print("    dbt docs serve        # 浏览器查看血缘图 (localhost:8080)")
    print("    python scripts/query_demo.py  # 跑几个示例分析查询（可选）")


if __name__ == "__main__":
    main()
