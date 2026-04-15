with employees as (
    select * from {{ ref('stg_chinook__employees') }}
)

select
    emp.employee_id,
    emp.first_name,
    emp.last_name,
    emp.title,
    emp.hire_date,
    emp.birth_date,
    emp.address,
    emp.city,
    emp.state,
    emp.country,
    emp.postal_code,
    emp.phone,
    emp.fax,
    emp.email,
    emp.reports_to_id,
    mgr.first_name || ' ' || mgr.last_name as reports_to_name
from employees emp
left join employees mgr
    on emp.reports_to_id = mgr.employee_id
