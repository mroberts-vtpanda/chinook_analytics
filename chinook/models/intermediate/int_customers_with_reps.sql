with customers as (
    select * from {{ ref('stg_chinook__customers') }}
),

employees as (
    select * from {{ ref('stg_chinook__employees') }}
),

joined as (
    select
        customers.customer_id,
        customers.first_name,
        customers.last_name,
        customers.company,
        customers.address,
        customers.city,
        customers.state,
        customers.country,
        customers.postal_code,
        customers.phone,
        customers.fax,
        customers.email,
        customers.support_rep_id,
        employees.first_name || ' ' || employees.last_name as support_rep_name,
        employees.email                                    as support_rep_email,
        employees.title                                    as support_rep_title
    from customers
    left join employees
        on customers.support_rep_id = employees.employee_id
)

select * from joined
