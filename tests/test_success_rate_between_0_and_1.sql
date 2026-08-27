-- 单测：成功率必须落在 [0,1] 区间（指标口径一致性）
-- 成功行 => 测试失败
select *
from {{ ref('daily_payment_summary') }}
where success_rate < 0 or success_rate > 1
