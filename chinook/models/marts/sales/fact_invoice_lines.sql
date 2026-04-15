select
    invoice_line_id,
    invoice_id,
    track_id,
    customer_id,
    invoice_timestamp,
    unit_price_amount,
    quantity,
    line_total_amount,
    billing_country,
    artist_id,
    genre_id
from {{ ref('int_invoice_lines_enriched') }}
