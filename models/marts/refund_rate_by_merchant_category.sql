-- Marts 退款分析：按商户类别的退款率
-- 口径：退款率 = 退款单数 / 成功单数（分子分母写死在 README 指标字典）
select
    m.category,
    count_if(f.status = 'refunded') as refund_payments,
    count_if(f.status = 'success')  as success_payments,
    round(count_if(f.status = 'refunded') * 1.0
          / nullif(count_if(f.status = 'success'), 0), 4) as refund_rate,
    round(sum(case when f.status = 'refunded' then f.amount_usd else 0 end), 2) as refund_amount_usd
from {{ ref('fct_payments') }} f
left join {{ ref('dim_merchant') }} m on f.merchant_key = m.merchant_key
group by m.category
order by refund_rate desc
