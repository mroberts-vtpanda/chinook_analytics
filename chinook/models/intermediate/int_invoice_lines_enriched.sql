with invoice_lines as (
    select * from {{ ref('stg_chinook__invoice_lines') }}
),

invoices as (
    select * from {{ ref('stg_chinook__invoices') }}
),

tracks as (
    select * from {{ ref('int_tracks_enriched') }}
),

enriched as (
    select
        invoice_lines.invoice_line_id,
        invoice_lines.invoice_id,
        invoice_lines.track_id,
        invoice_lines.unit_price_amount,
        invoice_lines.quantity,
        invoice_lines.unit_price_amount * invoice_lines.quantity as line_total_amount,
        invoices.customer_id,
        invoices.invoice_timestamp,
        invoices.billing_address,
        invoices.billing_city,
        invoices.billing_state,
        invoices.billing_country,
        invoices.billing_postal_code,
        invoices.total_amount                                    as invoice_total_amount,
        tracks.track_name,
        tracks.album_id,
        tracks.album_title,
        tracks.artist_id,
        tracks.artist_name,
        tracks.genre_id,
        tracks.genre_name,
        tracks.media_type_id,
        tracks.media_type_name
    from invoice_lines
    left join invoices using (invoice_id)
    left join tracks using (track_id)
)

select * from enriched
