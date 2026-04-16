with albums as (
    select * from {{ ref('stg_chinook__albums') }}
),

artists as (
    select * from {{ ref('stg_chinook__artists') }}
)

select
    albums.album_id,
    albums.album_title,
    albums.artist_id,
    artists.artist_name
from albums
left join artists using (artist_id)
