-- 单测（监控思维）：日 GMV 周环比（wow）骤降超过 30% 时告警
-- 排除最近一天：当天数据未完成，会造成"部分日"伪告警（真实监控里同样要处理）
select date_day, gmv_wow_pct
from {{ ref('daily_kpi') }}
where date_day <> (select max(date_day) from {{ ref('daily_kpi') }})
  and gmv_wow_pct is not null
  and gmv_wow_pct < -0.30
