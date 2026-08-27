-- Gold 维度表：用户
-- 粒度：每用户一行；代理键 user_key（按自然键排序保证确定性）
-- SCD 说明：本期采用 SCD1（当前状态）；vip 变化历史（SCD2）见 README「未来工作」。
select
    row_number() over (order by user_id) as user_key,
    user_id,
    country_code,
    vip_level,
    registered_at,
    is_active
from {{ ref('silver_users') }}
