with invoice_lines as (
    select * from {{ ref('int_invoice_lines_enriched') }}
)

select
    invoice_id,
    customer_id,
    invoice_timestamp,
    billing_address,
    billing_city,
    billing_state,
    billing_country,
    billing_postal_code,
    invoice_total_amount             as total_amount,
    count(invoice_line_id)           as invoice_line_count
from invoice_lines
group by
    invoice_id,
    customer_id,
    invoice_timestamp,
    billing_address,
    billing_city,
    billing_state,
    billing_country,
    billing_postal_code,
    invoice_total_amount
