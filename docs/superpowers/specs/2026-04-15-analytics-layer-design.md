# Chinook Analytics Layer Design

**Date:** 2026-04-15
**Project:** chinook_analytics
**Target platform:** Snowflake

---

## Overview

A full 3-layer dbt analytics layer (staging → intermediate → marts) on top of the Chinook music store database. The layer is designed for two consumers: a BI tool and ad-hoc SQL queries by analysts.

The mart layer follows a pure star schema pattern with fact tables and dimension tables organized by business domain.

---

## Naming Standards

### Models

| Layer | Pattern | Example |
|---|---|---|
| Staging | `stg_<source>__<entity>` | `stg_chinook__invoices` |
| Intermediate | `int_<entities>_<transformation>` | `int_tracks_enriched` |
| Facts | `fact_<plural_event>` | `fact_invoice_lines` |
| Dimensions | `dim_<plural_entity>` | `dim_customers` |

### Columns

| Type | Pattern | Example |
|---|---|---|
| Primary key | `<entity>_id` | `customer_id` |
| Surrogate key | `<model>_key` | `invoice_line_key` |
| Boolean | `is_*` / `has_*` | `is_active` |
| Timestamp | `*_timestamp` | `invoiced_timestamp` |
| Date | `*_date` | `hire_date` |
| Monetary | `*_amount` | `unit_price_amount` |
| Count | `*_count` | `invoice_line_count` |

### Files

- Every `.sql` model gets its own `.yml` file with the same name.
- Source definitions are consolidated in `_chinook__sources.yml` (leading underscore sorts it to the top in file explorers).
- All names use `snake_case`.

### Materializations

| Layer | Materialization |
|---|---|
| Staging | `view` |
| Intermediate | `view` |
| Marts | `table` |

---

## Layer Structure

```
models/
├── staging/
│   └── chinook/
│       ├── _chinook__sources.yml
│       ├── stg_chinook__albums.sql + .yml
│       ├── stg_chinook__artists.sql + .yml
│       ├── stg_chinook__customers.sql + .yml
│       ├── stg_chinook__employees.sql + .yml
│       ├── stg_chinook__genres.sql + .yml
│       ├── stg_chinook__invoice_lines.sql + .yml
│       ├── stg_chinook__invoices.sql + .yml
│       ├── stg_chinook__media_types.sql + .yml
│       ├── stg_chinook__playlists.sql + .yml
│       ├── stg_chinook__playlist_tracks.sql + .yml
│       └── stg_chinook__tracks.sql + .yml
├── intermediate/
│   ├── int_tracks_enriched.sql + .yml
│   ├── int_invoice_lines_enriched.sql + .yml
│   └── int_customers_with_reps.sql + .yml
└── marts/
    ├── sales/
    │   ├── fact_invoices.sql + .yml
    │   └── fact_invoice_lines.sql + .yml
    ├── customers/
    │   └── dim_customers.sql + .yml
    ├── music/
    │   ├── dim_artists.sql + .yml
    │   ├── dim_albums.sql + .yml
    │   └── dim_tracks.sql + .yml
    └── employees/
        └── dim_employees.sql + .yml
```

---

## Staging Layer

**Purpose:** 1:1 with source tables. Light cleaning only — rename columns to snake_case, cast data types, apply column naming conventions. No business logic.

**Source:** All 11 Chinook source tables defined in `_chinook__sources.yml`.

| Model | Source table | Notes |
|---|---|---|
| `stg_chinook__albums` | `Album` | Rename `AlbumId`, `Title`, `ArtistId` |
| `stg_chinook__artists` | `Artist` | Rename `ArtistId`, `Name` |
| `stg_chinook__customers` | `Customer` | Rename all columns; `SupportRepId` → `support_rep_id` |
| `stg_chinook__employees` | `Employee` | Rename all columns; cast `BirthDate`/`HireDate` to timestamp |
| `stg_chinook__genres` | `Genre` | Rename `GenreId`, `Name` |
| `stg_chinook__invoice_lines` | `InvoiceLine` | Rename all columns; `UnitPrice` → `unit_price_amount` |
| `stg_chinook__invoices` | `Invoice` | Rename all columns; `InvoiceDate` → `invoice_timestamp`; `Total` → `total_amount` |
| `stg_chinook__media_types` | `MediaType` | Rename `MediaTypeId`, `Name` |
| `stg_chinook__playlists` | `Playlist` | Rename `PlaylistId`, `Name` |
| `stg_chinook__playlist_tracks` | `PlaylistTrack` | Rename `PlaylistId`, `TrackId` — composite PK |
| `stg_chinook__tracks` | `Track` | Rename all columns; `UnitPrice` → `unit_price_amount` |

---

## Intermediate Layer

**Purpose:** Complex joins and transformations that are reused across multiple marts. Not exposed directly to BI tools or analysts.

### `int_tracks_enriched`
**Grain:** One row per track.
Joins `stg_chinook__tracks` → `stg_chinook__albums` → `stg_chinook__artists` → `stg_chinook__genres` → `stg_chinook__media_types`.
Produces a single wide record per track with artist name, album title, genre name, and media type name resolved.

### `int_invoice_lines_enriched`
**Grain:** One row per invoice line.
Joins `stg_chinook__invoice_lines` → `stg_chinook__invoices` → `int_tracks_enriched`.
Produces the full sales event: what was purchased, on which invoice, when, for how much, with full track/album/artist/genre context.

### `int_customers_with_reps`
**Grain:** One row per customer.
Joins `stg_chinook__customers` → `stg_chinook__employees` (aliased as support rep).
Resolves the support rep's name and contact details onto the customer record.

---

## Marts Layer

### Sales domain

#### `fact_invoice_lines`
**Grain:** One row per invoice line (most granular sales event).
**Source:** `int_invoice_lines_enriched`.
**Key columns:** `invoice_line_id`, `invoice_id`, `track_id`, `customer_id`, `invoice_timestamp`, `unit_price_amount`, `quantity`, `line_total_amount`.

#### `fact_invoices`
**Grain:** One row per invoice (header-level).
**Source:** `int_invoice_lines_enriched` aggregated to invoice grain, joined with `int_customers_with_reps`.
**Key columns:** `invoice_id`, `customer_id`, `invoice_timestamp`, `billing_country`, `total_amount`, `invoice_line_count`.

### Customers domain

#### `dim_customers`
**Grain:** One row per customer.
**Source:** `int_customers_with_reps`.
**Key columns:** `customer_id`, `first_name`, `last_name`, `email`, `company`, `city`, `state`, `country`, `support_rep_id`, `support_rep_name`.

### Music domain

#### `dim_artists`
**Grain:** One row per artist.
**Source:** `stg_chinook__artists`.
**Key columns:** `artist_id`, `artist_name`.

#### `dim_albums`
**Grain:** One row per album.
**Source:** `stg_chinook__albums` joined to `stg_chinook__artists`.
**Key columns:** `album_id`, `album_title`, `artist_id`, `artist_name`.

#### `dim_tracks`
**Grain:** One row per track.
**Source:** `int_tracks_enriched`.
**Key columns:** `track_id`, `track_name`, `album_id`, `album_title`, `artist_id`, `artist_name`, `genre_id`, `genre_name`, `media_type_id`, `media_type_name`, `composer`, `duration_milliseconds`, `unit_price_amount`.

### Employees domain

#### `dim_employees`
**Grain:** One row per employee.
**Source:** `stg_chinook__employees` self-joined on `reports_to_id`.
**Key columns:** `employee_id`, `first_name`, `last_name`, `title`, `hire_date`, `birth_date`, `city`, `state`, `country`, `email`, `reports_to_id`, `reports_to_name`.

---

## Tests & Documentation

### Test strategy

| Layer | Test | Applied to |
|---|---|---|
| Staging | `unique` + `not_null` | Every primary key column |
| Staging | `not_null` | Required business columns (e.g. `invoice_timestamp`, `total_amount`) |
| Staging | `relationships` | Every foreign key column |
| Intermediate | `unique` + `not_null` | Grain key of each model |
| Marts | `unique` + `not_null` | Every primary/surrogate key |
| Marts | `not_null` | All non-nullable business columns |
| Marts | `relationships` | Foreign keys between facts and dims |

### Documentation strategy

Every `.yml` file includes:
- A model-level `description` stating the grain and purpose
- A column-level `description` for every column

Source freshness tests are not applicable — Chinook is a static dataset with no ongoing loads.
