-- Marts 汇率口径影响分析（03 文档 §5.3 depth 点 1 的量化演示）
-- 对比两种口径的 GMV：
--   fixed_latest：用 dim_currency 的"期末固定汇率"（本期默认）
--   daily_rate  ：用 currency_rates 周快照按支付日匹配的"当日汇率"
-- 目的：说明口径差异对报表数字的影响 → 生产上须把口径写死并文档化。
with rate_lookup as (
    select
        r.currency_code,
        r.rate_date,
        r.to_usd_rate,
        lead(r.rate_date) over (partition by r.currency_code order by r.rate_date) as next_rate_date
    from {{ ref('silver_currency_rates') }} r
),
gmv as (
    select currency, amount, cast(paid_at as date) as paid_day
    from {{ ref('silver_payments') }}
    where status = 'success'
),
daily_joined as (
    select g.currency, g.amount, r.to_usd_rate as daily_rate
    from gmv g
    left join rate_lookup r
        on g.currency = r.currency_code
        and g.paid_day >= r.rate_date
        and (g.paid_day < r.next_rate_date or r.next_rate_date is null)
)
select
    'fixed_latest' as rate_strategy,
    round(sum(g.amount * c.to_usd_rate), 2) as gmv_usd,
    count(*) as success_payments
from gmv g
join {{ ref('silver_currencies') }} c on g.currency = c.currency_code
group by 1
union all
select
    'daily_rate',
    round(sum(g.amount * g.daily_rate), 2),
    count(*)
from daily_joined g
group by 1
