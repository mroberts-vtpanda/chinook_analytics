with tracks as (
    select * from {{ ref('stg_chinook__tracks') }}
),

albums as (
    select * from {{ ref('stg_chinook__albums') }}
),

artists as (
    select * from {{ ref('stg_chinook__artists') }}
),

genres as (
    select * from {{ ref('stg_chinook__genres') }}
),

media_types as (
    select * from {{ ref('stg_chinook__media_types') }}
),

enriched as (
    select
        tracks.track_id,
        tracks.track_name,
        tracks.album_id,
        albums.album_title,
        albums.artist_id,
        artists.artist_name,
        tracks.genre_id,
        genres.genre_name,
        tracks.media_type_id,
        media_types.media_type_name,
        tracks.composer,
        tracks.duration_milliseconds,
        tracks.size_bytes,
        tracks.unit_price_amount
    from tracks
    left join albums using (album_id)
    left join artists on albums.artist_id = artists.artist_id
    left join genres using (genre_id)
    left join media_types using (media_type_id)
)

select * from enriched
