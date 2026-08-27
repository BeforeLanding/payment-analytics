-- Gold 维度表：日期
-- 粒度：每天一行；date_key 为 YYYYMMDD 整数
-- 用 generate_series 按 silver_payments 的实际日期范围补齐
with date_spine as (
    select generate_series::date as date_day
    from generate_series(
        (select min(cast(created_at as date)) from {{ ref('silver_payments') }}),
        (select max(cast(created_at as date)) from {{ ref('silver_payments') }}),
        interval '1 day'
    )
)
select
    cast(strftime(date_day, '%Y%m%d') as integer) as date_key,
    date_day,
    year(date_day)                    as year,
    month(date_day)                   as month,
    monthname(date_day)               as month_name,
    quarter(date_day)                 as quarter,
    day(date_day)                     as day_of_month,
    dayofweek(date_day)               as day_of_week,        -- 0=Sunday
    dayname(date_day)                 as day_name,
    (dayofweek(date_day) in (0, 6))   as is_weekend,
    (date_day = date_trunc('month', date_day)::date) as is_month_start,
    (date_day = (date_trunc('month', date_day) + interval '1 month' - interval '1 day')::date) as is_month_end
from date_spine
