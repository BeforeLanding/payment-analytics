-- Gold 事实表：支付
-- 粒度：一笔支付单一行（不是订单行项）；退款为独立 status='refunded' 的负向事实。
-- 金额双存：amount（原币）+ amount_usd（按固定汇率换算），见 README「指标口径」。
select
    row_number() over (order by p.payment_id) as payment_key,
    p.payment_id,
    u.user_key,
    m.merchant_key,
    d.date_key,
    c.currency_key,
    p.order_id,
    p.country_code,
    p.currency,
    p.amount,
    round(p.amount * c.to_usd_rate, 2) as amount_usd,
    p.status,
    p.payment_method,
    p.created_at,
    p.paid_at
from {{ ref('silver_payments') }} p
left join {{ ref('dim_user') }}     u on p.user_id = u.user_id
left join {{ ref('dim_merchant') }} m on p.merchant_id = m.merchant_id
left join {{ ref('dim_date') }}     d on d.date_key = cast(strftime(cast(p.created_at as date), '%Y%m%d') as integer)
left join {{ ref('dim_currency') }} c on p.currency = c.currency_code
