-- Marts 国家维度 GMV 排行
select
    country_code,
    count(*)  as payments,
    round(sum(case when status = 'success'  then amount_usd else 0 end), 2) as gmv_usd,
    round(sum(case when status = 'refunded' then amount_usd else 0 end), 2) as refund_amount_usd,
    round(sum(case when status = 'success'  then amount_usd else 0 end)
        - sum(case when status = 'refunded' then amount_usd else 0 end), 2) as net_gmv_usd
from {{ ref('fct_payments') }}
group by country_code
order by net_gmv_usd desc
