-- Marts 报表：按 日 × 国家 × 币种 的支付汇总
-- 指标口径（见 README「指标字典」）：
--   success_rate = 成功单数 / 全部单数（按 created_at 归属日期）
--   gmv_usd       = Σ amount_usd（仅 success），按 created_at 归属
--   refund_amount = Σ amount_usd（refunded），作为独立负向事实统计
--   net_gmv_usd   = gmv_usd - refund_amount
select
    cast(created_at as date) as date_day,
    country_code,
    currency,
    count(*)                                   as total_payments,
    count_if(status = 'success')               as success_payments,
    count_if(status = 'failed')                as failed_payments,
    count_if(status = 'refunded')              as refund_payments,
    round(count_if(status = 'success') * 1.0 / nullif(count(*), 0), 4) as success_rate,
    round(sum(case when status = 'success'  then amount_usd else 0 end), 2) as gmv_usd,
    round(sum(case when status = 'refunded' then amount_usd else 0 end), 2) as refund_amount_usd,
    round(sum(case when status = 'success'  then amount_usd else 0 end)
        - sum(case when status = 'refunded' then amount_usd else 0 end), 2) as net_gmv_usd
from {{ ref('fct_payments') }}
group by 1, 2, 3
