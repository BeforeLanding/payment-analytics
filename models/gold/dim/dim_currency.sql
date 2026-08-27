-- Gold 维度表：币种
-- 粒度：每币种一行；代理键 currency_key
-- 汇率口径：本期使用固定汇率（近 3 个月最新快照），见 README「指标口径」。
--   「按日汇率」对照分析见 marts.currency_rate_impact。
select
    row_number() over (order by currency_code) as currency_key,
    currency_code,
    currency_name,
    to_usd_rate
from {{ ref('silver_currencies') }}
