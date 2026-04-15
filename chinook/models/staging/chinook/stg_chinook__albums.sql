with source as (
    select * from {{ source('chinook', 'albums') }}
),

renamed as (
    select
        AlbumId  as album_id,
        Title    as album_title,
        ArtistId as artist_id
    from source
)

select * from renamed
