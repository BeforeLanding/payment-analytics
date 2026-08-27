select * from {{ source('bronze', 'raw_merchants') }}
