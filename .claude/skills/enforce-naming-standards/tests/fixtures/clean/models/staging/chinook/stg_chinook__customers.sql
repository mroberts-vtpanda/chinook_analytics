select
    customerid as customer_id,
    firstname as first_name
from {{ source('chinook', 'customer') }}
