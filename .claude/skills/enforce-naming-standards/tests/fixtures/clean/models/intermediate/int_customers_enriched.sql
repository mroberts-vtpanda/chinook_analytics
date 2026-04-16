select
    c.customer_id,
    c.first_name
from {{ ref('stg_chinook__customers') }} c
