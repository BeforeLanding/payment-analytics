-- Silver = DWD：汇率历史（按周快照，用于演示"固定 vs 按日汇率"两种口径）
select
    upper(trim(currency_code))            as currency_code,
    try_cast(rate_date as date)           as rate_date,
    try_cast(to_usd_rate as decimal(18, 6)) as to_usd_rate
from {{ ref('bronze_currency_rates') }}
