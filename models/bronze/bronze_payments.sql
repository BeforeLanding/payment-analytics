-- Bronze = ODS：原样贴源，不做任何清洗（清洗交给 Silver）
select * from {{ source('bronze', 'raw_payments') }}
