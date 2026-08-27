select * from {{ source('bronze', 'raw_currency_rates') }}
