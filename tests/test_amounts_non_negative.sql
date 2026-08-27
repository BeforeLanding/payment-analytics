-- 单测：金额必须非负（退款按独立 status='refunded' 行建模，金额恒正）
select payment_id
from {{ ref('fct_payments') }}
where amount < 0 or amount_usd < 0
