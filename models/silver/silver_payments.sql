-- Silver = DWD：支付流水清洗层
-- 清洗动作（数量可在 marts.data_quality_audit 核对）：
--   1. 去重        payment_id 保留最早一条（Bronze 有 ~0.5% 重复）
--   2. 类型统一     amount → DECIMAL(18,2)，时间 → TIMESTAMP
--   3. 空值处理    country_code 空 → 'ZZ'（未知）；amount 空 → 0 并打标 amount_filled
--   4. 枚举标准化  status 归一为 pending/success/failed/refunded 四值，
--                  别名（refund/chargeback）与非法值（cancelled/expired/空）映射，
--                  原始值保留在 status_raw 供审计
--   5. 时间修复    paid_at < created_at（乱序）→ 修正为 created_at，打标 paid_at_corrected

with bronze as (
    select * from {{ ref('bronze_payments') }}
),

-- 1) 去重：按 payment_id 保留最早一条
deduped as (
    select *
    from (
        select *,
               row_number() over (partition by payment_id order by created_at, payment_id) as _rn
        from bronze
    )
    where _rn = 1
),

-- 2) 字段标准化
standardized as (
    select
        payment_id,
        order_id,
        user_id,
        merchant_id,
        coalesce(nullif(trim(upper(country_code)), ''), 'ZZ') as country_code,
        upper(trim(currency))                                as currency,
        try_cast(amount as decimal(18, 2))                   as amount,
        -- 清洗打标列（供审计）
        (country_code is null or trim(country_code) = '')    as country_filled,
        (amount is null)                                     as amount_filled,
        lower(trim(payment_method))                          as payment_method,
        try_cast(created_at as timestamp)                    as created_at,
        try_cast(paid_at   as timestamp)                     as paid_at,
        -- 状态归一化
        case lower(trim(status))
            when 'success'    then 'success'
            when 'refunded'   then 'refunded'
            when 'pending'    then 'pending'
            when 'failed'     then 'failed'
            when 'refund'     then 'refunded'   -- 别名
            when 'chargeback' then 'refunded'   -- 退单视为退款
            when 'cancelled'  then 'failed'
            when 'expired'    then 'failed'
            else 'failed'                       -- NULL / 空 / 其它非法值
        end                                        as status,
        status                                   as status_raw
    from deduped
),

-- 3) 时间修复
repaired as (
    select *,
           case when paid_at is not null and paid_at < created_at
                then created_at else paid_at end as paid_at_fixed
    from standardized
)

select
    payment_id,
    order_id,
    user_id,
    merchant_id,
    country_code,
    currency,
    coalesce(amount, 0.00) as amount,
    coalesce(payment_method, 'unknown') as payment_method,
    status,
    status_raw,
    (status is distinct from status_raw) as status_normalized,
    created_at,
    paid_at_fixed as paid_at,
    (paid_at is not null and paid_at < created_at) as paid_at_corrected,
    -- 清洗打标（供 marts.data_quality_audit 汇总）
    country_filled,
    amount_filled
from repaired
