with source as (
    select * from {{ source('chinook', 'invoices') }}
),

renamed as (
    select
        InvoiceId         as invoice_id,
        CustomerId        as customer_id,
        InvoiceDate       as invoice_timestamp,
        BillingAddress    as billing_address,
        BillingCity       as billing_city,
        BillingState      as billing_state,
        BillingCountry    as billing_country,
        BillingPostalCode as billing_postal_code,
        Total             as total_amount
    from source
)

select * from renamed
