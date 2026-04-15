with source as (
    select * from {{ source('chinook', 'tracks') }}
),

renamed as (
    select
        TrackId      as track_id,
        Name         as track_name,
        AlbumId      as album_id,
        MediaTypeId  as media_type_id,
        GenreId      as genre_id,
        Composer     as composer,
        Milliseconds as duration_milliseconds,
        Bytes        as size_bytes,
        UnitPrice    as unit_price_amount
    from source
)

select * from renamed
