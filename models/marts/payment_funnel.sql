-- Marts 漏斗：支付生命周期（按状态统计笔数与金额）
-- 笔数 = 全部支付单；金额 = Σ amount_usd（各状态均为正向金额，退款独立列示）
select
    status,
    count(*)                as payments,
    round(sum(amount_usd), 2) as amount_usd
from {{ ref('fct_payments') }}
group by status
order by payments desc
