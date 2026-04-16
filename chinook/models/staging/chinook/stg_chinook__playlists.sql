with source as (
    select * from {{ source('chinook', 'playlists') }}
),

renamed as (
    select
        PlaylistId as playlist_id,
        Name       as playlist_name
    from source
)

select * from renamed
