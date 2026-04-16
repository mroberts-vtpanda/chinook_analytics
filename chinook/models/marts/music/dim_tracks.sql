select
    track_id,
    track_name,
    album_id,
    album_title,
    artist_id,
    artist_name,
    genre_id,
    genre_name,
    media_type_id,
    media_type_name,
    composer,
    duration_milliseconds,
    size_bytes,
    unit_price_amount
from {{ ref('int_tracks_enriched') }}
