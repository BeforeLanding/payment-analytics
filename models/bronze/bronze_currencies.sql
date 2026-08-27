select * from {{ source('bronze', 'raw_currencies') }}
