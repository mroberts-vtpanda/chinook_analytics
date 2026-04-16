select
    customer_id,
    first_name,
    last_name,
    company,
    address,
    city,
    state,
    country,
    postal_code,
    phone,
    fax,
    email,
    support_rep_id,
    support_rep_name,
    support_rep_email,
    support_rep_title
from {{ ref('int_customers_with_reps') }}
