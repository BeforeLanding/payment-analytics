select * from {{ source('bronze', 'raw_users') }}
