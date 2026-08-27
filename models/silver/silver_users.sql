-- Silver = DWD：用户维度清洗
--   空 country_code → 'ZZ'；vip_level 空 → 0；is_active 统一布尔；类型统一
select
    user_id,
    coalesce(nullif(trim(upper(country_code)), ''), 'ZZ') as country_code,
    coalesce(try_cast(vip_level as integer), 0)          as vip_level,
    try_cast(registered_at as timestamp)                 as registered_at,
    coalesce(try_cast(is_active as boolean), false)      as is_active
from {{ ref('bronze_users') }}
