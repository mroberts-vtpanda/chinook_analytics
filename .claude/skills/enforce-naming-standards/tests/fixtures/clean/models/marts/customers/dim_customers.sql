select
    customer_id,
    first_name
from {{ ref('int_customers_enriched') }}
