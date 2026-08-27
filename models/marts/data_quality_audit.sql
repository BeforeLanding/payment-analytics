-- Marts 数据质量审计：量化 Bronze → Silver 清掉了多少脏数据（面试"数字产出"）
-- 注意：illegal_status 统计用 "status IS NULL OR ... NOT IN"，
--       因为 SQL 里 NULL NOT IN (...) 返回 unknown，会漏掉 NULL 状态（经典坑，见 README）
with bronze_stats as (
    select
        count(*)                                      as bronze_rows,
        count(distinct payment_id)                    as distinct_payment_ids,
        count(*) - count(distinct payment_id)         as duplicate_rows,
        count(*) filter (where country_code is null or country_code = '') as null_country_rows,
        count(*) filter (where amount is null)        as null_amount_rows,
        count(*) filter (where status is null or lower(trim(status)) not in ('pending', 'success', 'failed', 'refunded')) as illegal_status_rows,
        count(*) filter (where paid_at is not null and paid_at < created_at) as out_of_order_rows
    from {{ ref('bronze_payments') }}
),
silver_stats as (
    select
        count(*) as silver_rows,
        count(*) filter (where country_filled)   as country_filled_rows,
        count(*) filter (where amount_filled)    as amount_filled_rows,
        count(*) filter (where status_normalized) as status_normalized_rows,
        count(*) filter (where paid_at_corrected) as paid_at_corrected_rows
    from {{ ref('silver_payments') }}
)
select
    b.bronze_rows,
    b.duplicate_rows                as duplicate_rows_removed,
    b.null_country_rows             as null_country_fixed,
    b.null_amount_rows              as null_amount_filled,
    b.illegal_status_rows           as illegal_status_normalized,
    b.out_of_order_rows             as out_of_order_fixed,
    s.silver_rows,
    round(100.0 * b.duplicate_rows / b.bronze_rows, 3)      as duplicate_rate_pct,
    round(100.0 * (b.null_country_rows + b.null_amount_rows + b.illegal_status_rows + b.out_of_order_rows) / b.bronze_rows, 3) as dirty_rows_pct
from bronze_stats b
cross join silver_stats s
