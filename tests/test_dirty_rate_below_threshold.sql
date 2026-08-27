-- 单测：Bronze 脏数据率必须低于 5%（防止上游数据源大幅劣化而不知）
select *
from {{ ref('data_quality_audit') }}
where dirty_rows_pct > 5
