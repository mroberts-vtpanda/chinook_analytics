select
    artist_id,
    artist_name
from {{ ref('stg_chinook__artists') }}
