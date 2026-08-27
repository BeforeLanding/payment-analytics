-- Marts 用户分层：VIP 等级 × GMV（体现维表 join 价值）
-- gmv_per_user = 成功支付 GMV / 有成功支付的用户数
select
    u.vip_level,
    count(distinct u.user_id) as paying_users,
    count(*)                  as payments,
    round(sum(case when f.status = 'success' then f.amount_usd else 0 end), 2) as gmv_usd,
    round(sum(case when f.status = 'success' then f.amount_usd else 0 end)
          / nullif(count(distinct u.user_id), 0), 2) as gmv_per_user
from {{ ref('fct_payments') }} f
left join {{ ref('dim_user') }} u on f.user_key = u.user_key
group by u.vip_level
order by u.vip_level
