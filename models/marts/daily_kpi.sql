-- Marts KPI：日粒度核心指标 + 环比（窗口函数 lag()）
--   gmv_wow_pct  = 与 7 天前的 GMV 环比（周日更平滑）；gmv_dod_pct = 日环比
--   说明：lag() 前 7 天无值 → NULL，环比率也 NULL（不参与告警）
with daily as (
    select
        cast(created_at as date) as date_day,
        count(*)                                   as total_payments,
        count_if(status = 'success')               as success_payments,
        count_if(status = 'failed')                as failed_payments,
        count_if(status = 'refunded')              as refund_payments,
        round(sum(case when status = 'success' then amount_usd else 0 end), 2) as gmv_usd,
        round(count_if(status = 'success') * 1.0 / nullif(count(*), 0), 4)      as success_rate
    from {{ ref('fct_payments') }}
    group by 1
)
select
    date_day,
    total_payments,
    success_payments,
    failed_payments,
    refund_payments,
    gmv_usd,
    success_rate,
    round(sum(gmv_usd) over (order by date_day rows between 6 preceding and current row) / 7.0, 2) as gmv_7d_avg,
    round(lag(gmv_usd, 1) over (order by date_day), 2) as gmv_prev_day,
    round((gmv_usd - lag(gmv_usd, 1) over (order by date_day))
          / nullif(lag(gmv_usd, 1) over (order by date_day), 0), 4) as gmv_dod_pct,
    round(lag(gmv_usd, 7) over (order by date_day), 2) as gmv_prev_week,
    round((gmv_usd - lag(gmv_usd, 7) over (order by date_day))
          / nullif(lag(gmv_usd, 7) over (order by date_day), 0), 4) as gmv_wow_pct
from daily
