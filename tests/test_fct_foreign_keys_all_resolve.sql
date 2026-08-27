-- 单测：fct_payments 的所有外键必须能在对应维度表找到（关系完整性）
-- 出现孤儿外键 => 测试失败（说明 join 掉了行，事实表不完整）
select f.payment_id
from {{ ref('fct_payments') }} f
left join {{ ref('dim_user') }}     u on f.user_key = u.user_key
left join {{ ref('dim_merchant') }} m on f.merchant_key = m.merchant_key
left join {{ ref('dim_date') }}     d on f.date_key = d.date_key
left join {{ ref('dim_currency') }} c on f.currency_key = c.currency_key
where u.user_key is null
   or m.merchant_key is null
   or d.date_key is null
   or c.currency_key is null
