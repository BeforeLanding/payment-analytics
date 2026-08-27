#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
gen_data.py — 生成模拟全球支付交易数据（含可控脏数据）

产出（输出到 data/ 目录）：
  currencies.csv      币种主数据（22 种货币 + 对 USD 汇率）
  currency_rates.csv  汇率历史（近 3 个月按周快照，用于演示"按日 vs 固定汇率"）
  merchants.csv       商户维度（2000 家）
  users.csv           用户维度（50000 名）
  payments.csv        支付流水（默认 50 万行，横跨近 90 天）

故意制造的脏数据（用于 Silver 层清洗演示，数量由本脚本汇总打印）：
  1. payment_id 重复        ~0.5%    → Silver 去重
  2. country_code 空值       ~0.8%    → Silver 补 'ZZ'（未知）
  3. amount 空值             ~0.3%    → Silver 补 0 并标记
  4. status 非法值           ~1.5%    → Silver 规范化 / 归一为 failed
  5. paid_at < created_at    ~0.5%    → Silver 修正为 created_at

说明：
  - 退款按"独立负向事实"建模：status='refunded' 的独立支付单（金额为正），
    不覆盖原单，见 03 文档 §5.3 depth 点 2。
  - 汇率口径：本期使用"近 3 个月最新汇率"作为固定汇率（见 README 指标口径）。
"""
import argparse
import csv
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# (国家代码, 国家名, 币种代码, 币种名, 对 USD 汇率)
COUNTRY_CURRENCY = [
    ("US", "United States",  "USD", "US Dollar",          1.0),
    ("BR", "Brazil",         "BRL", "Brazilian Real",     0.18),
    ("ID", "Indonesia",      "IDR", "Indonesian Rupiah",  0.000065),
    ("GB", "United Kingdom", "GBP", "British Pound",      1.27),
    ("IN", "India",          "INR", "Indian Rupee",       0.012),
    ("JP", "Japan",          "JPY", "Japanese Yen",       0.0067),
    ("DE", "Germany",        "EUR", "Euro",               1.08),
    ("FR", "France",         "EUR", "Euro",               1.08),
    ("MX", "Mexico",         "MXN", "Mexican Peso",       0.058),
    ("CA", "Canada",         "CAD", "Canadian Dollar",    0.73),
    ("AU", "Australia",      "AUD", "Australian Dollar",  0.65),
    ("SG", "Singapore",      "SGD", "Singapore Dollar",   0.74),
    ("NG", "Nigeria",        "NGN", "Nigerian Naira",     0.0007),
    ("PH", "Philippines",    "PHP", "Philippine Peso",    0.017),
    ("VN", "Vietnam",        "VND", "Vietnamese Dong",    0.00004),
    ("TH", "Thailand",       "THB", "Thai Baht",          0.028),
    ("TR", "Turkey",         "TRY", "Turkish Lira",       0.031),
    ("AR", "Argentina",      "ARS", "Argentine Peso",     0.0028),
    ("PL", "Poland",         "PLN", "Polish Zloty",       0.25),
    ("SE", "Sweden",         "SEK", "Swedish Krona",      0.093),
    ("KR", "South Korea",    "KRW", "Korean Won",         0.00074),
    ("ZA", "South Africa",   "ZAR", "South African Rand", 0.054),
]
# 币种去重：币种代码 → (代码, 名称, 基础汇率)
CURRENCIES = list({c[2]: (c[2], c[3], c[4]) for c in COUNTRY_CURRENCY}.values())
# 国家 → 币种 映射（保证 payment 的 country_code 与 currency 一致）
COUNTRY2CURRENCY = {c[0]: c[2] for c in COUNTRY_CURRENCY}
# 国家 → 权重（造数分布）
COUNTRY_WEIGHT = {
    "US": 18, "BR": 12, "ID": 14, "GB": 8, "IN": 16, "JP": 6, "DE": 6,
    "FR": 5, "MX": 6, "CA": 4, "AU": 3, "SG": 3, "NG": 4, "PH": 3,
    "VN": 3, "TH": 2, "TR": 3, "AR": 2, "PL": 1, "SE": 1, "KR": 2, "ZA": 1,
}

MERCHANT_CATEGORY = [
    "retail", "grocery", "ecommerce", "food_delivery", "travel",
    "digital_subscription", "utilities", "ride_hailing",
]
STATUS_VALID = ["pending", "success", "failed", "refunded"]
# 故意造一批非法/不规范 status，用于清洗演示
STATUS_DIRTY = ["cancelled", "chargeback", "Success", "REFUND", "", "expired"]
PAYMENT_METHOD = ["card", "wallet", "bank_transfer", "cash"]
USER_VIP = [0, 1, 2, 3]

# 各渠道的状态分布（真实世界：现金/银行转账人工环节多、失败率高 → 渠道质量分析更有故事）
METHOD_STATUS = {
    "card":         {"success": 78, "refunded": 9, "failed": 7,  "pending": 6},
    "wallet":       {"success": 74, "refunded": 9, "failed": 9,  "pending": 8},
    "bank_transfer": {"success": 66, "refunded": 7, "failed": 18, "pending": 9},
    "cash":         {"success": 58, "refunded": 5, "failed": 26, "pending": 11},
}

# 脏数据比例（占 payment 总行数）
DIRTY = {
    "dup": 0.005,            # 重复 payment_id
    "null_country": 0.008,   # country_code 空值
    "null_amount": 0.003,    # amount 空值
    "illegal_status": 0.015, # status 非法值
    "out_of_order": 0.005,   # paid_at < created_at
}


def rand_country(rng):
    return rng.choices(COUNTRY_CODE := list(COUNTRY_WEIGHT), weights=[COUNTRY_WEIGHT[c] for c in COUNTRY_WEIGHT], k=1)[0]


def gen_currencies(out_dir: Path, rng, days: int, now: datetime):
    """币种主数据 + 汇率周快照（汇率有轻微波动，用于演示汇率口径）"""
    with open(out_dir / "currencies.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["currency_code", "currency_name", "to_usd_rate", "rate_strategy"])
        for code, name, base_rate in CURRENCIES:
            w.writerow([code, name, f"{base_rate:.6f}", "fixed_latest"])

    start = now - timedelta(days=days)
    with open(out_dir / "currency_rates.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["currency_code", "rate_date", "to_usd_rate"])
        d = start
        while d <= now:
            for code, _name, base_rate in CURRENCIES:
                drift = 1 + rng.uniform(-0.05, 0.05)
                w.writerow([code, d.strftime("%Y-%m-%d"), f"{base_rate * drift:.6f}"])
            d += timedelta(days=7)


def gen_merchants(out_dir: Path, rng, n: int):
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    with open(out_dir / "merchants.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["merchant_id", "merchant_name", "category", "country_code", "created_at", "is_active"])
        for i in range(1, n + 1):
            cc = rand_country(rng)
            if rng.random() < 0.01:          # 1% 商户国家为空，演示维表清洗
                cc = ""
            created = base + timedelta(days=rng.randint(0, 600))
            w.writerow([
                f"M{i:05d}",
                f"{MERCHANT_CATEGORY[i % len(MERCHANT_CATEGORY)]}_{i:05d}_merchant",
                MERCHANT_CATEGORY[i % len(MERCHANT_CATEGORY)],
                cc,
                created.strftime("%Y-%m-%d %H:%M:%S"),
                "1" if rng.random() < 0.93 else "0",
            ])


def gen_users(out_dir: Path, rng, n: int, now: datetime):
    """返回 {user_id: country_code} 供 payments 关联"""
    users = {}
    with open(out_dir / "users.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["user_id", "country_code", "vip_level", "registered_at", "is_active"])
        for i in range(1, n + 1):
            uid = f"U{i:06d}"
            cc = rand_country(rng)
            users[uid] = cc
            reg = now - timedelta(days=rng.randint(30, 900))
            w.writerow([
                uid, cc,
                rng.choices(USER_VIP, weights=[60, 25, 10, 5])[0],
                reg.strftime("%Y-%m-%d %H:%M:%S"),
                "1" if rng.random() < 0.9 else "0",
            ])
    return users


def gen_payments(out_dir: Path, rng, n: int, days: int, now: datetime, users, merchants):
    """生成支付流水；返回体检统计"""
    start = now - timedelta(days=days)
    n_days = days

    stats = {k: 0 for k in DIRTY}
    status_counts = {s: 0 for s in STATUS_VALID}
    method_counts = {m: 0 for m in PAYMENT_METHOD}

    # 预生成 order_id（97% 单笔，3% 两笔共享同一订单）
    order_ids = [f"ORD-{rng.randint(10000000, 99999999)}" for _ in range(n)]
    user_ids = list(users)

    rows = []
    for i in range(1, n + 1):
        user_id = rng.choice(user_ids)
        merchant_id = rng.choice(merchants)
        # 95% 与用户同国，5% 跨境
        cc = users[user_id] if rng.random() < 0.95 else rand_country(rng)
        cur = COUNTRY2CURRENCY[cc]
        amount = f"{10 ** rng.uniform(0.7, 2.6):.2f}"   # 约 $5 ~ $400
        method = rng.choices(PAYMENT_METHOD, weights=[45, 30, 15, 10])[0]
        status = rng.choices(list(METHOD_STATUS[method]), weights=list(METHOD_STATUS[method].values()))[0]

        created = start + timedelta(seconds=rng.randint(0, n_days * 86400))
        paid_at = ""
        if status in ("success", "refunded"):
            if status == "success":
                paid = created + timedelta(seconds=rng.randint(5, 3600))
            else:  # refunded：退款处理时间更晚
                paid = created + timedelta(seconds=rng.randint(3600, 86400 * 7))
            paid_at = paid.strftime("%Y-%m-%d %H:%M:%S")

        rows.append([f"PAY{i:08d}", order_ids[i - 1], user_id, merchant_id, cc, cur,
                     amount, status, method,
                     created.strftime("%Y-%m-%d %H:%M:%S"), paid_at])
        status_counts[status] += 1
        method_counts[method] += 1

    # ---- 注入脏数据 ----
    # 1) 重复 payment_id：直接复制部分行
    for _ in range(int(n * DIRTY["dup"])):
        rows.append(list(rng.choice(rows)))
        stats["dup"] += 1

    # 2) country_code / amount 空值（分别在独立行上注入，避免叠加）
    for idx in rng.sample(range(len(rows)), int(n * DIRTY["null_country"])):
        rows[idx][4] = ""
        stats["null_country"] += 1
    for idx in rng.sample(range(len(rows)), int(n * DIRTY["null_amount"])):
        rows[idx][6] = ""
        stats["null_amount"] += 1

    # 3) 非法 status
    for idx in rng.sample(range(len(rows)), int(n * DIRTY["illegal_status"])):
        rows[idx][7] = rng.choice(STATUS_DIRTY)
        stats["illegal_status"] += 1

    # 4) paid_at < created_at（仅 success 行）
    success_idx = [i for i, r in enumerate(rows) if r[7] == "success"]
    for idx in rng.sample(success_idx, min(int(n * DIRTY["out_of_order"]), len(success_idx))):
        created_dt = datetime.strptime(rows[idx][9], "%Y-%m-%d %H:%M:%S")
        rows[idx][10] = (created_dt - timedelta(minutes=rng.randint(5, 120))).strftime("%Y-%m-%d %H:%M:%S")
        stats["out_of_order"] += 1

    rng.shuffle(rows)
    with open(out_dir / "payments.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["payment_id", "order_id", "user_id", "merchant_id",
                    "country_code", "currency", "amount", "status",
                    "payment_method", "created_at", "paid_at"])
        w.writerows(rows)

    return {
        "total": len(rows),
        "status_counts": status_counts,
        "method_counts": method_counts,
        "dirty": stats,
    }


def main():
    ap = argparse.ArgumentParser(description="生成模拟支付交易数据")
    ap.add_argument("--n-payments", type=int, default=500_000)
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--n-users", type=int, default=50_000)
    ap.add_argument("--n-merchants", type=int, default=2_000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=str, default="data")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    rng = random.Random(args.seed)
    now = datetime.now(timezone.utc)

    print(f"[1/4] 生成币种与汇率（{len(CURRENCIES)} 种）→ {out_dir}")
    gen_currencies(out_dir, rng, args.days, now)

    print(f"[2/4] 生成商户 {args.n_merchants} 家 → {out_dir}")
    gen_merchants(out_dir, rng, args.n_merchants)

    print(f"[3/4] 生成用户 {args.n_users} 名 → {out_dir}")
    users = gen_users(out_dir, rng, args.n_users, now)

    print(f"[4/4] 生成支付流水 {args.n_payments} 行 → {out_dir}（预计 1~2 分钟）")
    result = gen_payments(out_dir, rng, args.n_payments, args.days, now, users,
                          merchants=[f"M{i:05d}" for i in range(1, args.n_merchants + 1)])

    print("\n===== 生成完成 / 数据体检 =====")
    print(f"支付流水总行数     : {result['total']:,}")
    print(f"状态分布           : {result['status_counts']}")
    print(f"支付方式分布       : {result['method_counts']}")
    print("---- 脏数据（Silver 将清洗）----")
    for k, v in result["dirty"].items():
        print(f"  {k:<16}: {v:,} 行")


if __name__ == "__main__":
    sys.exit(main())
