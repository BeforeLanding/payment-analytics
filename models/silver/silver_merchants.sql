-- Silver = DWD：商户维度清洗
select
    merchant_id,
    merchant_name,
    coalesce(nullif(trim(lower(category)), ''), 'unknown') as category,
    coalesce(nullif(trim(upper(country_code)), ''), 'ZZ')  as country_code,
    try_cast(created_at as timestamp)                      as created_at,
    coalesce(try_cast(is_active as boolean), false)        as is_active
from {{ ref('bronze_merchants') }}
