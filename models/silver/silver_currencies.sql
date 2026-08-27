-- Silver = DWD：币种主数据清洗
select
    upper(trim(currency_code))            as currency_code,
    currency_name,
    try_cast(to_usd_rate as decimal(18, 6)) as to_usd_rate,
    rate_strategy
from {{ ref('bronze_currencies') }}
