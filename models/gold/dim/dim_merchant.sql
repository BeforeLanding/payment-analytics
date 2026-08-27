-- Gold 维度表：商户
-- 粒度：每商户一行；代理键 merchant_key
select
    row_number() over (order by merchant_id) as merchant_key,
    merchant_id,
    merchant_name,
    category,
    country_code,
    created_at,
    is_active
from {{ ref('silver_merchants') }}
