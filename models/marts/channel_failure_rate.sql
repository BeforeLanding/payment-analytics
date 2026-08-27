-- Marts 渠道质量：按支付方式统计失败率（定位渠道质量问题）
-- failure_rate = failed 单数 / 该渠道全部单数
select
    payment_method,
    count(*)                                   as total_payments,
    count_if(status = 'failed')                as failed_payments,
    round(count_if(status = 'failed') * 1.0 / nullif(count(*), 0), 4) as failure_rate
from {{ ref('fct_payments') }}
group by payment_method
order by failure_rate desc
