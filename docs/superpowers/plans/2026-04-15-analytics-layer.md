# Chinook Analytics Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete 3-layer dbt analytics layer (staging → intermediate → marts) on the Chinook music store database in Snowflake, following a pure star schema pattern with full tests and documentation.

**Architecture:** Staging models (views) clean and rename source columns 1:1; intermediate models (views) join related staging models to produce reusable building blocks; mart models (tables) expose `fact_*` and `dim_*` tables organized by business domain (sales, customers, music, employees).

**Tech Stack:** dbt-core 1.11.8, dbt-snowflake 1.11.4, Snowflake

**Prerequisites:**
- `~/.dbt/profiles.yml` must have a working `chinook` profile pointing to your Snowflake environment.
- All dbt commands are run from `chinook_analytics/chinook/` (the dbt project root).
- The Chinook source tables must already exist in Snowflake. Update `database` and `schema` in `_chinook__sources.yml` (Task 2) to match your actual Snowflake environment.

---

## File Map

**Modify:**
- `chinook/dbt_project.yml` — configure materialization per layer, remove example config

**Delete:**
- `chinook/models/example/my_first_dbt_model.sql`
- `chinook/models/example/my_second_dbt_model.sql`
- `chinook/models/example/schema.yml`

**Create (staging):**
- `chinook/models/staging/chinook/_chinook__sources.yml`
- `chinook/models/staging/chinook/stg_chinook__artists.sql` + `.yml`
- `chinook/models/staging/chinook/stg_chinook__genres.sql` + `.yml`
- `chinook/models/staging/chinook/stg_chinook__media_types.sql` + `.yml`
- `chinook/models/staging/chinook/stg_chinook__playlists.sql` + `.yml`
- `chinook/models/staging/chinook/stg_chinook__albums.sql` + `.yml`
- `chinook/models/staging/chinook/stg_chinook__tracks.sql` + `.yml`
- `chinook/models/staging/chinook/stg_chinook__employees.sql` + `.yml`
- `chinook/models/staging/chinook/stg_chinook__customers.sql` + `.yml`
- `chinook/models/staging/chinook/stg_chinook__invoices.sql` + `.yml`
- `chinook/models/staging/chinook/stg_chinook__invoice_lines.sql` + `.yml`
- `chinook/models/staging/chinook/stg_chinook__playlist_tracks.sql` + `.yml`

**Create (intermediate):**
- `chinook/models/intermediate/int_tracks_enriched.sql` + `.yml`
- `chinook/models/intermediate/int_invoice_lines_enriched.sql` + `.yml`
- `chinook/models/intermediate/int_customers_with_reps.sql` + `.yml`

**Create (marts):**
- `chinook/models/marts/music/dim_artists.sql` + `.yml`
- `chinook/models/marts/music/dim_albums.sql` + `.yml`
- `chinook/models/marts/music/dim_tracks.sql` + `.yml`
- `chinook/models/marts/employees/dim_employees.sql` + `.yml`
- `chinook/models/marts/customers/dim_customers.sql` + `.yml`
- `chinook/models/marts/sales/fact_invoices.sql` + `.yml`
- `chinook/models/marts/sales/fact_invoice_lines.sql` + `.yml`

---

### Task 1: Project Setup

**Files:**
- Modify: `chinook/dbt_project.yml`
- Delete: `chinook/models/example/` (3 files)

- [ ] **Step 1: Update dbt_project.yml**

Replace the entire file content with:

```yaml
name: 'chinook'
version: '1.0.0'

profile: 'chinook'

model-paths: ["models"]
analysis-paths: ["analyses"]
test-paths: ["tests"]
seed-paths: ["seeds"]
macro-paths: ["macros"]
snapshot-paths: ["snapshots"]

clean-targets:
  - "target"
  - "dbt_packages"

models:
  chinook:
    staging:
      +materialized: view
    intermediate:
      +materialized: view
    marts:
      +materialized: table
```

- [ ] **Step 2: Delete example models**

```bash
git rm chinook/models/example/my_first_dbt_model.sql \
       chinook/models/example/my_second_dbt_model.sql \
       chinook/models/example/schema.yml
```

- [ ] **Step 3: Verify dbt compiles cleanly**

```bash
cd chinook && dbt compile
```
Expected: `Done. PASS=0 WARN=0 ERROR=0 SKIP=0 TOTAL=0`

- [ ] **Step 4: Commit**

```bash
git add chinook/dbt_project.yml
git commit -m "chore: configure layer materializations, remove example models"
```

---

### Task 2: Source Definitions

**Files:**
- Create: `chinook/models/staging/chinook/_chinook__sources.yml`

- [ ] **Step 1: Create the sources file**

> Update `database` and `schema` to match your Snowflake environment before running `dbt build`.

```yaml
version: 2

sources:
  - name: chinook
    database: chinook
    schema: chinook
    tables:
      - name: artists
        identifier: artist
      - name: albums
        identifier: album
      - name: tracks
        identifier: track
      - name: genres
        identifier: genre
      - name: media_types
        identifier: mediatype
      - name: customers
        identifier: customer
      - name: employees
        identifier: employee
      - name: invoices
        identifier: invoice
      - name: invoice_lines
        identifier: invoiceline
      - name: playlists
        identifier: playlist
      - name: playlist_tracks
        identifier: playlisttrack
```

- [ ] **Step 2: Verify sources resolve**

```bash
cd chinook && dbt compile
```
Expected: `Done. PASS=0 WARN=0 ERROR=0 SKIP=0 TOTAL=0`

- [ ] **Step 3: Commit**

```bash
git add chinook/models/staging/chinook/_chinook__sources.yml
git commit -m "feat: add chinook source definitions"
```

---

### Task 3: stg_chinook__artists

**Files:**
- Create: `chinook/models/staging/chinook/stg_chinook__artists.sql`
- Create: `chinook/models/staging/chinook/stg_chinook__artists.yml`

- [ ] **Step 1: Write stg_chinook__artists.yml**

```yaml
version: 2

models:
  - name: stg_chinook__artists
    description: "One row per artist. Renames source columns from the Artist table to snake_case."
    columns:
      - name: artist_id
        description: "Primary key. Unique identifier for each artist."
        data_tests:
          - unique
          - not_null
      - name: artist_name
        description: "Name of the artist. Nullable in source."
```

- [ ] **Step 2: Write stg_chinook__artists.sql**

```sql
with source as (
    select * from {{ source('chinook', 'artists') }}
),

renamed as (
    select
        ArtistId as artist_id,
        Name     as artist_name
    from source
)

select * from renamed
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select stg_chinook__artists
```
Expected: `PASS=2 WARN=0 ERROR=0 SKIP=0 TOTAL=3`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/staging/chinook/stg_chinook__artists.sql \
        chinook/models/staging/chinook/stg_chinook__artists.yml
git commit -m "feat: add stg_chinook__artists"
```

---

### Task 4: stg_chinook__genres

**Files:**
- Create: `chinook/models/staging/chinook/stg_chinook__genres.sql`
- Create: `chinook/models/staging/chinook/stg_chinook__genres.yml`

- [ ] **Step 1: Write stg_chinook__genres.yml**

```yaml
version: 2

models:
  - name: stg_chinook__genres
    description: "One row per music genre. Renames source columns from the Genre table to snake_case."
    columns:
      - name: genre_id
        description: "Primary key. Unique identifier for each genre."
        data_tests:
          - unique
          - not_null
      - name: genre_name
        description: "Name of the genre (e.g., Rock, Jazz, Classical). Nullable in source."
```

- [ ] **Step 2: Write stg_chinook__genres.sql**

```sql
with source as (
    select * from {{ source('chinook', 'genres') }}
),

renamed as (
    select
        GenreId as genre_id,
        Name    as genre_name
    from source
)

select * from renamed
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select stg_chinook__genres
```
Expected: `PASS=2 WARN=0 ERROR=0 SKIP=0 TOTAL=3`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/staging/chinook/stg_chinook__genres.sql \
        chinook/models/staging/chinook/stg_chinook__genres.yml
git commit -m "feat: add stg_chinook__genres"
```

---

### Task 5: stg_chinook__media_types

**Files:**
- Create: `chinook/models/staging/chinook/stg_chinook__media_types.sql`
- Create: `chinook/models/staging/chinook/stg_chinook__media_types.yml`

- [ ] **Step 1: Write stg_chinook__media_types.yml**

```yaml
version: 2

models:
  - name: stg_chinook__media_types
    description: "One row per media type. Renames source columns from the MediaType table to snake_case."
    columns:
      - name: media_type_id
        description: "Primary key. Unique identifier for each media type."
        data_tests:
          - unique
          - not_null
      - name: media_type_name
        description: "Name of the media type (e.g., MPEG audio file, AAC audio file). Nullable in source."
```

- [ ] **Step 2: Write stg_chinook__media_types.sql**

```sql
with source as (
    select * from {{ source('chinook', 'media_types') }}
),

renamed as (
    select
        MediaTypeId as media_type_id,
        Name        as media_type_name
    from source
)

select * from renamed
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select stg_chinook__media_types
```
Expected: `PASS=2 WARN=0 ERROR=0 SKIP=0 TOTAL=3`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/staging/chinook/stg_chinook__media_types.sql \
        chinook/models/staging/chinook/stg_chinook__media_types.yml
git commit -m "feat: add stg_chinook__media_types"
```

---

### Task 6: stg_chinook__playlists

**Files:**
- Create: `chinook/models/staging/chinook/stg_chinook__playlists.sql`
- Create: `chinook/models/staging/chinook/stg_chinook__playlists.yml`

- [ ] **Step 1: Write stg_chinook__playlists.yml**

```yaml
version: 2

models:
  - name: stg_chinook__playlists
    description: "One row per playlist. Renames source columns from the Playlist table to snake_case."
    columns:
      - name: playlist_id
        description: "Primary key. Unique identifier for each playlist."
        data_tests:
          - unique
          - not_null
      - name: playlist_name
        description: "Name of the playlist. Nullable in source."
```

- [ ] **Step 2: Write stg_chinook__playlists.sql**

```sql
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
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select stg_chinook__playlists
```
Expected: `PASS=2 WARN=0 ERROR=0 SKIP=0 TOTAL=3`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/staging/chinook/stg_chinook__playlists.sql \
        chinook/models/staging/chinook/stg_chinook__playlists.yml
git commit -m "feat: add stg_chinook__playlists"
```

---

### Task 7: stg_chinook__albums

**Files:**
- Create: `chinook/models/staging/chinook/stg_chinook__albums.sql`
- Create: `chinook/models/staging/chinook/stg_chinook__albums.yml`

- [ ] **Step 1: Write stg_chinook__albums.yml**

```yaml
version: 2

models:
  - name: stg_chinook__albums
    description: "One row per album. Renames source columns from the Album table to snake_case."
    columns:
      - name: album_id
        description: "Primary key. Unique identifier for each album."
        data_tests:
          - unique
          - not_null
      - name: album_title
        description: "Title of the album."
        data_tests:
          - not_null
      - name: artist_id
        description: "Foreign key to stg_chinook__artists."
        data_tests:
          - not_null
          - relationships:
              to: ref('stg_chinook__artists')
              field: artist_id
```

- [ ] **Step 2: Write stg_chinook__albums.sql**

```sql
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
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select stg_chinook__albums
```
Expected: `PASS=4 WARN=0 ERROR=0 SKIP=0 TOTAL=5`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/staging/chinook/stg_chinook__albums.sql \
        chinook/models/staging/chinook/stg_chinook__albums.yml
git commit -m "feat: add stg_chinook__albums"
```

---

### Task 8: stg_chinook__tracks

**Files:**
- Create: `chinook/models/staging/chinook/stg_chinook__tracks.sql`
- Create: `chinook/models/staging/chinook/stg_chinook__tracks.yml`

- [ ] **Step 1: Write stg_chinook__tracks.yml**

```yaml
version: 2

models:
  - name: stg_chinook__tracks
    description: "One row per track. Renames source columns from the Track table to snake_case."
    columns:
      - name: track_id
        description: "Primary key. Unique identifier for each track."
        data_tests:
          - unique
          - not_null
      - name: track_name
        description: "Name of the track."
        data_tests:
          - not_null
      - name: album_id
        description: "Foreign key to stg_chinook__albums. Nullable — some tracks have no album."
        data_tests:
          - relationships:
              to: ref('stg_chinook__albums')
              field: album_id
      - name: media_type_id
        description: "Foreign key to stg_chinook__media_types."
        data_tests:
          - not_null
          - relationships:
              to: ref('stg_chinook__media_types')
              field: media_type_id
      - name: genre_id
        description: "Foreign key to stg_chinook__genres. Nullable."
        data_tests:
          - relationships:
              to: ref('stg_chinook__genres')
              field: genre_id
      - name: composer
        description: "Name of the composer. Nullable."
      - name: duration_milliseconds
        description: "Track duration in milliseconds."
        data_tests:
          - not_null
      - name: size_bytes
        description: "File size in bytes. Nullable."
      - name: unit_price_amount
        description: "Unit price of the track in USD."
        data_tests:
          - not_null
```

- [ ] **Step 2: Write stg_chinook__tracks.sql**

```sql
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
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select stg_chinook__tracks
```
Expected: `PASS=7 WARN=0 ERROR=0 SKIP=0 TOTAL=8`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/staging/chinook/stg_chinook__tracks.sql \
        chinook/models/staging/chinook/stg_chinook__tracks.yml
git commit -m "feat: add stg_chinook__tracks"
```

---

### Task 9: stg_chinook__employees

**Files:**
- Create: `chinook/models/staging/chinook/stg_chinook__employees.sql`
- Create: `chinook/models/staging/chinook/stg_chinook__employees.yml`

- [ ] **Step 1: Write stg_chinook__employees.yml**

```yaml
version: 2

models:
  - name: stg_chinook__employees
    description: "One row per employee. Renames source columns from the Employee table to snake_case. Casts BirthDate and HireDate from TIMESTAMP_NTZ to DATE."
    columns:
      - name: employee_id
        description: "Primary key. Unique identifier for each employee."
        data_tests:
          - unique
          - not_null
      - name: last_name
        description: "Employee last name."
        data_tests:
          - not_null
      - name: first_name
        description: "Employee first name."
        data_tests:
          - not_null
      - name: title
        description: "Job title. Nullable."
      - name: reports_to_id
        description: "Foreign key to stg_chinook__employees (self-referential). Nullable — the top-level employee has no manager."
        data_tests:
          - relationships:
              to: ref('stg_chinook__employees')
              field: employee_id
      - name: birth_date
        description: "Date of birth. Cast from TIMESTAMP_NTZ to DATE."
      - name: hire_date
        description: "Date the employee was hired. Cast from TIMESTAMP_NTZ to DATE."
      - name: address
        description: "Street address. Nullable."
      - name: city
        description: "City. Nullable."
      - name: state
        description: "State or province. Nullable."
      - name: country
        description: "Country. Nullable."
      - name: postal_code
        description: "Postal code. Nullable."
      - name: phone
        description: "Phone number. Nullable."
      - name: fax
        description: "Fax number. Nullable."
      - name: email
        description: "Email address. Nullable."
```

- [ ] **Step 2: Write stg_chinook__employees.sql**

```sql
with source as (
    select * from {{ source('chinook', 'employees') }}
),

renamed as (
    select
        EmployeeId      as employee_id,
        LastName        as last_name,
        FirstName       as first_name,
        Title           as title,
        ReportsTo       as reports_to_id,
        BirthDate::date as birth_date,
        HireDate::date  as hire_date,
        Address         as address,
        City            as city,
        State           as state,
        Country         as country,
        PostalCode      as postal_code,
        Phone           as phone,
        Fax             as fax,
        Email           as email
    from source
)

select * from renamed
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select stg_chinook__employees
```
Expected: `PASS=4 WARN=0 ERROR=0 SKIP=0 TOTAL=5`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/staging/chinook/stg_chinook__employees.sql \
        chinook/models/staging/chinook/stg_chinook__employees.yml
git commit -m "feat: add stg_chinook__employees"
```

---

### Task 10: stg_chinook__customers

**Files:**
- Create: `chinook/models/staging/chinook/stg_chinook__customers.sql`
- Create: `chinook/models/staging/chinook/stg_chinook__customers.yml`

- [ ] **Step 1: Write stg_chinook__customers.yml**

```yaml
version: 2

models:
  - name: stg_chinook__customers
    description: "One row per customer. Renames source columns from the Customer table to snake_case."
    columns:
      - name: customer_id
        description: "Primary key. Unique identifier for each customer."
        data_tests:
          - unique
          - not_null
      - name: first_name
        description: "Customer first name."
        data_tests:
          - not_null
      - name: last_name
        description: "Customer last name."
        data_tests:
          - not_null
      - name: company
        description: "Company name. Nullable."
      - name: address
        description: "Street address. Nullable."
      - name: city
        description: "City. Nullable."
      - name: state
        description: "State or province. Nullable."
      - name: country
        description: "Country. Nullable."
      - name: postal_code
        description: "Postal code. Nullable."
      - name: phone
        description: "Phone number. Nullable."
      - name: fax
        description: "Fax number. Nullable."
      - name: email
        description: "Email address."
        data_tests:
          - not_null
      - name: support_rep_id
        description: "Foreign key to stg_chinook__employees. Nullable."
        data_tests:
          - relationships:
              to: ref('stg_chinook__employees')
              field: employee_id
```

- [ ] **Step 2: Write stg_chinook__customers.sql**

```sql
with source as (
    select * from {{ source('chinook', 'customers') }}
),

renamed as (
    select
        CustomerId   as customer_id,
        FirstName    as first_name,
        LastName     as last_name,
        Company      as company,
        Address      as address,
        City         as city,
        State        as state,
        Country      as country,
        PostalCode   as postal_code,
        Phone        as phone,
        Fax          as fax,
        Email        as email,
        SupportRepId as support_rep_id
    from source
)

select * from renamed
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select stg_chinook__customers
```
Expected: `PASS=5 WARN=0 ERROR=0 SKIP=0 TOTAL=6`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/staging/chinook/stg_chinook__customers.sql \
        chinook/models/staging/chinook/stg_chinook__customers.yml
git commit -m "feat: add stg_chinook__customers"
```

---

### Task 11: stg_chinook__invoices

**Files:**
- Create: `chinook/models/staging/chinook/stg_chinook__invoices.sql`
- Create: `chinook/models/staging/chinook/stg_chinook__invoices.yml`

- [ ] **Step 1: Write stg_chinook__invoices.yml**

```yaml
version: 2

models:
  - name: stg_chinook__invoices
    description: "One row per invoice header. Renames source columns from the Invoice table to snake_case."
    columns:
      - name: invoice_id
        description: "Primary key. Unique identifier for each invoice."
        data_tests:
          - unique
          - not_null
      - name: customer_id
        description: "Foreign key to stg_chinook__customers."
        data_tests:
          - not_null
          - relationships:
              to: ref('stg_chinook__customers')
              field: customer_id
      - name: invoice_timestamp
        description: "Date and time the invoice was created."
        data_tests:
          - not_null
      - name: billing_address
        description: "Billing street address. Nullable."
      - name: billing_city
        description: "Billing city. Nullable."
      - name: billing_state
        description: "Billing state or province. Nullable."
      - name: billing_country
        description: "Billing country. Nullable."
      - name: billing_postal_code
        description: "Billing postal code. Nullable."
      - name: total_amount
        description: "Total invoice amount in USD."
        data_tests:
          - not_null
```

- [ ] **Step 2: Write stg_chinook__invoices.sql**

```sql
with source as (
    select * from {{ source('chinook', 'invoices') }}
),

renamed as (
    select
        InvoiceId         as invoice_id,
        CustomerId        as customer_id,
        InvoiceDate       as invoice_timestamp,
        BillingAddress    as billing_address,
        BillingCity       as billing_city,
        BillingState      as billing_state,
        BillingCountry    as billing_country,
        BillingPostalCode as billing_postal_code,
        Total             as total_amount
    from source
)

select * from renamed
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select stg_chinook__invoices
```
Expected: `PASS=4 WARN=0 ERROR=0 SKIP=0 TOTAL=5`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/staging/chinook/stg_chinook__invoices.sql \
        chinook/models/staging/chinook/stg_chinook__invoices.yml
git commit -m "feat: add stg_chinook__invoices"
```

---

### Task 12: stg_chinook__invoice_lines

**Files:**
- Create: `chinook/models/staging/chinook/stg_chinook__invoice_lines.sql`
- Create: `chinook/models/staging/chinook/stg_chinook__invoice_lines.yml`

- [ ] **Step 1: Write stg_chinook__invoice_lines.yml**

```yaml
version: 2

models:
  - name: stg_chinook__invoice_lines
    description: "One row per invoice line item. Renames source columns from the InvoiceLine table to snake_case."
    columns:
      - name: invoice_line_id
        description: "Primary key. Unique identifier for each invoice line."
        data_tests:
          - unique
          - not_null
      - name: invoice_id
        description: "Foreign key to stg_chinook__invoices."
        data_tests:
          - not_null
          - relationships:
              to: ref('stg_chinook__invoices')
              field: invoice_id
      - name: track_id
        description: "Foreign key to stg_chinook__tracks."
        data_tests:
          - not_null
          - relationships:
              to: ref('stg_chinook__tracks')
              field: track_id
      - name: unit_price_amount
        description: "Unit price of the track on this invoice line in USD."
        data_tests:
          - not_null
      - name: quantity
        description: "Number of units purchased on this line."
        data_tests:
          - not_null
```

- [ ] **Step 2: Write stg_chinook__invoice_lines.sql**

```sql
with source as (
    select * from {{ source('chinook', 'invoice_lines') }}
),

renamed as (
    select
        InvoiceLineId as invoice_line_id,
        InvoiceId     as invoice_id,
        TrackId       as track_id,
        UnitPrice     as unit_price_amount,
        Quantity      as quantity
    from source
)

select * from renamed
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select stg_chinook__invoice_lines
```
Expected: `PASS=7 WARN=0 ERROR=0 SKIP=0 TOTAL=8`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/staging/chinook/stg_chinook__invoice_lines.sql \
        chinook/models/staging/chinook/stg_chinook__invoice_lines.yml
git commit -m "feat: add stg_chinook__invoice_lines"
```

---

### Task 13: stg_chinook__playlist_tracks

**Files:**
- Create: `chinook/models/staging/chinook/stg_chinook__playlist_tracks.sql`
- Create: `chinook/models/staging/chinook/stg_chinook__playlist_tracks.yml`

- [ ] **Step 1: Write stg_chinook__playlist_tracks.yml**

```yaml
version: 2

models:
  - name: stg_chinook__playlist_tracks
    description: "One row per playlist-track association. Composite primary key of playlist_id + track_id. Renames source columns from the PlaylistTrack table to snake_case."
    columns:
      - name: playlist_id
        description: "Part of composite primary key. Foreign key to stg_chinook__playlists."
        data_tests:
          - not_null
          - relationships:
              to: ref('stg_chinook__playlists')
              field: playlist_id
      - name: track_id
        description: "Part of composite primary key. Foreign key to stg_chinook__tracks."
        data_tests:
          - not_null
          - relationships:
              to: ref('stg_chinook__tracks')
              field: track_id
```

- [ ] **Step 2: Write stg_chinook__playlist_tracks.sql**

```sql
with source as (
    select * from {{ source('chinook', 'playlist_tracks') }}
),

renamed as (
    select
        PlaylistId as playlist_id,
        TrackId    as track_id
    from source
)

select * from renamed
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select stg_chinook__playlist_tracks
```
Expected: `PASS=4 WARN=0 ERROR=0 SKIP=0 TOTAL=5`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/staging/chinook/stg_chinook__playlist_tracks.sql \
        chinook/models/staging/chinook/stg_chinook__playlist_tracks.yml
git commit -m "feat: add stg_chinook__playlist_tracks"
```

---

### Task 14: int_tracks_enriched

**Files:**
- Create: `chinook/models/intermediate/int_tracks_enriched.sql`
- Create: `chinook/models/intermediate/int_tracks_enriched.yml`

- [ ] **Step 1: Write int_tracks_enriched.yml**

```yaml
version: 2

models:
  - name: int_tracks_enriched
    description: "One row per track with artist, album, genre, and media type details resolved. Joins stg_chinook__tracks to albums, artists, genres, and media_types. Building block for dim_tracks and int_invoice_lines_enriched."
    columns:
      - name: track_id
        description: "Primary key. Unique identifier for each track."
        data_tests:
          - unique
          - not_null
      - name: track_name
        description: "Name of the track."
        data_tests:
          - not_null
      - name: album_id
        description: "Foreign key to the album. Nullable — some tracks have no album."
      - name: album_title
        description: "Title of the album. Nullable when album_id is null."
      - name: artist_id
        description: "Foreign key to the artist. Nullable when album_id is null."
      - name: artist_name
        description: "Name of the artist. Nullable when album_id is null."
      - name: genre_id
        description: "Foreign key to the genre. Nullable."
      - name: genre_name
        description: "Name of the genre. Nullable when genre_id is null."
      - name: media_type_id
        description: "Foreign key to the media type."
        data_tests:
          - not_null
      - name: media_type_name
        description: "Name of the media type."
      - name: composer
        description: "Composer of the track. Nullable."
      - name: duration_milliseconds
        description: "Track duration in milliseconds."
        data_tests:
          - not_null
      - name: size_bytes
        description: "File size in bytes. Nullable."
      - name: unit_price_amount
        description: "Unit price of the track in USD."
        data_tests:
          - not_null
```

- [ ] **Step 2: Write int_tracks_enriched.sql**

```sql
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
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select int_tracks_enriched
```
Expected: `PASS=4 WARN=0 ERROR=0 SKIP=0 TOTAL=5`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/intermediate/int_tracks_enriched.sql \
        chinook/models/intermediate/int_tracks_enriched.yml
git commit -m "feat: add int_tracks_enriched"
```

---

### Task 15: int_invoice_lines_enriched

**Files:**
- Create: `chinook/models/intermediate/int_invoice_lines_enriched.sql`
- Create: `chinook/models/intermediate/int_invoice_lines_enriched.yml`

- [ ] **Step 1: Write int_invoice_lines_enriched.yml**

```yaml
version: 2

models:
  - name: int_invoice_lines_enriched
    description: "One row per invoice line with invoice header details and full track/album/artist/genre context resolved. Joins stg_chinook__invoice_lines to stg_chinook__invoices and int_tracks_enriched. Building block for fact_invoice_lines and fact_invoices."
    columns:
      - name: invoice_line_id
        description: "Primary key. Unique identifier for each invoice line."
        data_tests:
          - unique
          - not_null
      - name: invoice_id
        description: "Foreign key to the invoice header."
        data_tests:
          - not_null
      - name: track_id
        description: "Foreign key to the track."
        data_tests:
          - not_null
      - name: customer_id
        description: "Foreign key to the customer, sourced from the invoice header."
        data_tests:
          - not_null
      - name: invoice_timestamp
        description: "Date and time the invoice was created."
        data_tests:
          - not_null
      - name: unit_price_amount
        description: "Unit price of the track on this line in USD."
        data_tests:
          - not_null
      - name: quantity
        description: "Number of units purchased on this line."
        data_tests:
          - not_null
      - name: line_total_amount
        description: "Total for this line (unit_price_amount * quantity) in USD."
        data_tests:
          - not_null
      - name: billing_address
        description: "Billing street address from the invoice header. Nullable."
      - name: billing_city
        description: "Billing city from the invoice header. Nullable."
      - name: billing_state
        description: "Billing state from the invoice header. Nullable."
      - name: billing_country
        description: "Billing country from the invoice header. Nullable."
      - name: billing_postal_code
        description: "Billing postal code from the invoice header. Nullable."
      - name: invoice_total_amount
        description: "Total amount of the invoice header in USD."
        data_tests:
          - not_null
      - name: track_name
        description: "Name of the track."
      - name: album_id
        description: "Album identifier. Nullable."
      - name: album_title
        description: "Album title. Nullable."
      - name: artist_id
        description: "Artist identifier. Nullable."
      - name: artist_name
        description: "Artist name. Nullable."
      - name: genre_id
        description: "Genre identifier. Nullable."
      - name: genre_name
        description: "Genre name. Nullable."
      - name: media_type_id
        description: "Media type identifier."
      - name: media_type_name
        description: "Media type name."
```

- [ ] **Step 2: Write int_invoice_lines_enriched.sql**

```sql
with invoice_lines as (
    select * from {{ ref('stg_chinook__invoice_lines') }}
),

invoices as (
    select * from {{ ref('stg_chinook__invoices') }}
),

tracks as (
    select * from {{ ref('int_tracks_enriched') }}
),

enriched as (
    select
        invoice_lines.invoice_line_id,
        invoice_lines.invoice_id,
        invoice_lines.track_id,
        invoice_lines.unit_price_amount,
        invoice_lines.quantity,
        invoice_lines.unit_price_amount * invoice_lines.quantity as line_total_amount,
        invoices.customer_id,
        invoices.invoice_timestamp,
        invoices.billing_address,
        invoices.billing_city,
        invoices.billing_state,
        invoices.billing_country,
        invoices.billing_postal_code,
        invoices.total_amount                                    as invoice_total_amount,
        tracks.track_name,
        tracks.album_id,
        tracks.album_title,
        tracks.artist_id,
        tracks.artist_name,
        tracks.genre_id,
        tracks.genre_name,
        tracks.media_type_id,
        tracks.media_type_name
    from invoice_lines
    left join invoices using (invoice_id)
    left join tracks using (track_id)
)

select * from enriched
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select int_invoice_lines_enriched
```
Expected: `PASS=5 WARN=0 ERROR=0 SKIP=0 TOTAL=6`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/intermediate/int_invoice_lines_enriched.sql \
        chinook/models/intermediate/int_invoice_lines_enriched.yml
git commit -m "feat: add int_invoice_lines_enriched"
```

---

### Task 16: int_customers_with_reps

**Files:**
- Create: `chinook/models/intermediate/int_customers_with_reps.sql`
- Create: `chinook/models/intermediate/int_customers_with_reps.yml`

- [ ] **Step 1: Write int_customers_with_reps.yml**

```yaml
version: 2

models:
  - name: int_customers_with_reps
    description: "One row per customer with their assigned support representative's details resolved. Joins stg_chinook__customers to stg_chinook__employees. Building block for dim_customers."
    columns:
      - name: customer_id
        description: "Primary key. Unique identifier for each customer."
        data_tests:
          - unique
          - not_null
      - name: first_name
        description: "Customer first name."
        data_tests:
          - not_null
      - name: last_name
        description: "Customer last name."
        data_tests:
          - not_null
      - name: company
        description: "Company name. Nullable."
      - name: address
        description: "Street address. Nullable."
      - name: city
        description: "City. Nullable."
      - name: state
        description: "State or province. Nullable."
      - name: country
        description: "Country. Nullable."
      - name: postal_code
        description: "Postal code. Nullable."
      - name: phone
        description: "Phone number. Nullable."
      - name: fax
        description: "Fax number. Nullable."
      - name: email
        description: "Email address."
        data_tests:
          - not_null
      - name: support_rep_id
        description: "Foreign key to stg_chinook__employees. Nullable."
      - name: support_rep_name
        description: "Full name of the support representative (first_name || ' ' || last_name). Nullable when support_rep_id is null."
      - name: support_rep_email
        description: "Email address of the support representative. Nullable."
      - name: support_rep_title
        description: "Job title of the support representative. Nullable."
```

- [ ] **Step 2: Write int_customers_with_reps.sql**

```sql
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
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select int_customers_with_reps
```
Expected: `PASS=3 WARN=0 ERROR=0 SKIP=0 TOTAL=4`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/intermediate/int_customers_with_reps.sql \
        chinook/models/intermediate/int_customers_with_reps.yml
git commit -m "feat: add int_customers_with_reps"
```

---

### Task 17: dim_artists

**Files:**
- Create: `chinook/models/marts/music/dim_artists.sql`
- Create: `chinook/models/marts/music/dim_artists.yml`

- [ ] **Step 1: Write dim_artists.yml**

```yaml
version: 2

models:
  - name: dim_artists
    description: "Dimension table. One row per artist. Grain: artist_id."
    columns:
      - name: artist_id
        description: "Primary key. Unique identifier for each artist."
        data_tests:
          - unique
          - not_null
      - name: artist_name
        description: "Name of the artist. Nullable in source."
```

- [ ] **Step 2: Write dim_artists.sql**

```sql
select
    artist_id,
    artist_name
from {{ ref('stg_chinook__artists') }}
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select dim_artists
```
Expected: `PASS=2 WARN=0 ERROR=0 SKIP=0 TOTAL=3`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/marts/music/dim_artists.sql \
        chinook/models/marts/music/dim_artists.yml
git commit -m "feat: add dim_artists"
```

---

### Task 18: dim_albums

**Files:**
- Create: `chinook/models/marts/music/dim_albums.sql`
- Create: `chinook/models/marts/music/dim_albums.yml`

- [ ] **Step 1: Write dim_albums.yml**

```yaml
version: 2

models:
  - name: dim_albums
    description: "Dimension table. One row per album with artist name resolved. Grain: album_id."
    columns:
      - name: album_id
        description: "Primary key. Unique identifier for each album."
        data_tests:
          - unique
          - not_null
      - name: album_title
        description: "Title of the album."
        data_tests:
          - not_null
      - name: artist_id
        description: "Foreign key to dim_artists."
        data_tests:
          - not_null
          - relationships:
              to: ref('dim_artists')
              field: artist_id
      - name: artist_name
        description: "Name of the artist. Nullable in source."
```

- [ ] **Step 2: Write dim_albums.sql**

```sql
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
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select dim_albums
```
Expected: `PASS=4 WARN=0 ERROR=0 SKIP=0 TOTAL=5`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/marts/music/dim_albums.sql \
        chinook/models/marts/music/dim_albums.yml
git commit -m "feat: add dim_albums"
```

---

### Task 19: dim_tracks

**Files:**
- Create: `chinook/models/marts/music/dim_tracks.sql`
- Create: `chinook/models/marts/music/dim_tracks.yml`

- [ ] **Step 1: Write dim_tracks.yml**

```yaml
version: 2

models:
  - name: dim_tracks
    description: "Dimension table. One row per track with album, artist, genre, and media type details resolved. Grain: track_id."
    columns:
      - name: track_id
        description: "Primary key. Unique identifier for each track."
        data_tests:
          - unique
          - not_null
      - name: track_name
        description: "Name of the track."
        data_tests:
          - not_null
      - name: album_id
        description: "Foreign key to dim_albums. Nullable — some tracks have no album."
        data_tests:
          - relationships:
              to: ref('dim_albums')
              field: album_id
      - name: album_title
        description: "Title of the album. Nullable when album_id is null."
      - name: artist_id
        description: "Foreign key to dim_artists. Nullable when album_id is null."
        data_tests:
          - relationships:
              to: ref('dim_artists')
              field: artist_id
      - name: artist_name
        description: "Name of the artist. Nullable when album_id is null."
      - name: genre_id
        description: "Genre identifier. Nullable."
      - name: genre_name
        description: "Name of the genre. Nullable."
      - name: media_type_id
        description: "Media type identifier."
        data_tests:
          - not_null
      - name: media_type_name
        description: "Name of the media type."
      - name: composer
        description: "Composer of the track. Nullable."
      - name: duration_milliseconds
        description: "Track duration in milliseconds."
        data_tests:
          - not_null
      - name: size_bytes
        description: "File size in bytes. Nullable."
      - name: unit_price_amount
        description: "Unit price of the track in USD."
        data_tests:
          - not_null
```

- [ ] **Step 2: Write dim_tracks.sql**

```sql
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
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select dim_tracks
```
Expected: `PASS=6 WARN=0 ERROR=0 SKIP=0 TOTAL=7`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/marts/music/dim_tracks.sql \
        chinook/models/marts/music/dim_tracks.yml
git commit -m "feat: add dim_tracks"
```

---

### Task 20: dim_employees

**Files:**
- Create: `chinook/models/marts/employees/dim_employees.sql`
- Create: `chinook/models/marts/employees/dim_employees.yml`

- [ ] **Step 1: Write dim_employees.yml**

```yaml
version: 2

models:
  - name: dim_employees
    description: "Dimension table. One row per employee with their manager's name resolved via self-join. Grain: employee_id."
    columns:
      - name: employee_id
        description: "Primary key. Unique identifier for each employee."
        data_tests:
          - unique
          - not_null
      - name: first_name
        description: "Employee first name."
        data_tests:
          - not_null
      - name: last_name
        description: "Employee last name."
        data_tests:
          - not_null
      - name: title
        description: "Job title. Nullable."
      - name: hire_date
        description: "Date the employee was hired."
      - name: birth_date
        description: "Date of birth."
      - name: address
        description: "Street address. Nullable."
      - name: city
        description: "City. Nullable."
      - name: state
        description: "State or province. Nullable."
      - name: country
        description: "Country. Nullable."
      - name: postal_code
        description: "Postal code. Nullable."
      - name: phone
        description: "Phone number. Nullable."
      - name: fax
        description: "Fax number. Nullable."
      - name: email
        description: "Email address. Nullable."
      - name: reports_to_id
        description: "Foreign key to dim_employees (self-referential). Nullable — the top-level employee has no manager."
      - name: reports_to_name
        description: "Full name of the manager (first_name || ' ' || last_name). Nullable when reports_to_id is null."
```

- [ ] **Step 2: Write dim_employees.sql**

```sql
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
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select dim_employees
```
Expected: `PASS=3 WARN=0 ERROR=0 SKIP=0 TOTAL=4`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/marts/employees/dim_employees.sql \
        chinook/models/marts/employees/dim_employees.yml
git commit -m "feat: add dim_employees"
```

---

### Task 21: dim_customers

**Files:**
- Create: `chinook/models/marts/customers/dim_customers.sql`
- Create: `chinook/models/marts/customers/dim_customers.yml`

> **Dependency:** Task 20 (dim_employees) must be completed before the `relationships` test on `support_rep_id` will pass.

- [ ] **Step 1: Write dim_customers.yml**

```yaml
version: 2

models:
  - name: dim_customers
    description: "Dimension table. One row per customer with support representative details resolved. Grain: customer_id."
    columns:
      - name: customer_id
        description: "Primary key. Unique identifier for each customer."
        data_tests:
          - unique
          - not_null
      - name: first_name
        description: "Customer first name."
        data_tests:
          - not_null
      - name: last_name
        description: "Customer last name."
        data_tests:
          - not_null
      - name: company
        description: "Company name. Nullable."
      - name: address
        description: "Street address. Nullable."
      - name: city
        description: "City. Nullable."
      - name: state
        description: "State or province. Nullable."
      - name: country
        description: "Country. Nullable."
      - name: postal_code
        description: "Postal code. Nullable."
      - name: phone
        description: "Phone number. Nullable."
      - name: fax
        description: "Fax number. Nullable."
      - name: email
        description: "Email address."
        data_tests:
          - not_null
      - name: support_rep_id
        description: "Foreign key to dim_employees. Nullable."
        data_tests:
          - relationships:
              to: ref('dim_employees')
              field: employee_id
      - name: support_rep_name
        description: "Full name of the support representative. Nullable when support_rep_id is null."
      - name: support_rep_email
        description: "Email of the support representative. Nullable."
      - name: support_rep_title
        description: "Job title of the support representative. Nullable."
```

- [ ] **Step 2: Write dim_customers.sql**

```sql
select
    customer_id,
    first_name,
    last_name,
    company,
    address,
    city,
    state,
    country,
    postal_code,
    phone,
    fax,
    email,
    support_rep_id,
    support_rep_name,
    support_rep_email,
    support_rep_title
from {{ ref('int_customers_with_reps') }}
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select dim_customers
```
Expected: `PASS=4 WARN=0 ERROR=0 SKIP=0 TOTAL=5`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/marts/customers/dim_customers.sql \
        chinook/models/marts/customers/dim_customers.yml
git commit -m "feat: add dim_customers"
```

---

### Task 22: fact_invoices

**Files:**
- Create: `chinook/models/marts/sales/fact_invoices.sql`
- Create: `chinook/models/marts/sales/fact_invoices.yml`

> **Dependency:** Task 21 (dim_customers) must be completed before the `relationships` test on `customer_id` will pass.

- [ ] **Step 1: Write fact_invoices.yml**

```yaml
version: 2

models:
  - name: fact_invoices
    description: "Fact table. One row per invoice header. Grain: invoice_id. Use for invoice-level analysis — totals, geography, customer. For track-level analysis use fact_invoice_lines."
    columns:
      - name: invoice_id
        description: "Primary key. Unique identifier for each invoice."
        data_tests:
          - unique
          - not_null
      - name: customer_id
        description: "Foreign key to dim_customers."
        data_tests:
          - not_null
          - relationships:
              to: ref('dim_customers')
              field: customer_id
      - name: invoice_timestamp
        description: "Date and time the invoice was created."
        data_tests:
          - not_null
      - name: billing_address
        description: "Billing street address. Nullable."
      - name: billing_city
        description: "Billing city. Nullable."
      - name: billing_state
        description: "Billing state or province. Nullable."
      - name: billing_country
        description: "Billing country. Nullable."
      - name: billing_postal_code
        description: "Billing postal code. Nullable."
      - name: total_amount
        description: "Total invoice amount in USD, sourced from the invoice header."
        data_tests:
          - not_null
      - name: invoice_line_count
        description: "Number of line items on this invoice."
        data_tests:
          - not_null
```

- [ ] **Step 2: Write fact_invoices.sql**

```sql
with invoice_lines as (
    select * from {{ ref('int_invoice_lines_enriched') }}
)

select
    invoice_id,
    customer_id,
    invoice_timestamp,
    billing_address,
    billing_city,
    billing_state,
    billing_country,
    billing_postal_code,
    invoice_total_amount             as total_amount,
    count(invoice_line_id)           as invoice_line_count
from invoice_lines
group by
    invoice_id,
    customer_id,
    invoice_timestamp,
    billing_address,
    billing_city,
    billing_state,
    billing_country,
    billing_postal_code,
    invoice_total_amount
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select fact_invoices
```
Expected: `PASS=3 WARN=0 ERROR=0 SKIP=0 TOTAL=4`

- [ ] **Step 4: Commit**

```bash
git add chinook/models/marts/sales/fact_invoices.sql \
        chinook/models/marts/sales/fact_invoices.yml
git commit -m "feat: add fact_invoices"
```

---

### Task 23: fact_invoice_lines

**Files:**
- Create: `chinook/models/marts/sales/fact_invoice_lines.sql`
- Create: `chinook/models/marts/sales/fact_invoice_lines.yml`

> **Dependency:** Tasks 19 (dim_tracks), 21 (dim_customers), 22 (fact_invoices) must be completed before all `relationships` tests will pass.

- [ ] **Step 1: Write fact_invoice_lines.yml**

```yaml
version: 2

models:
  - name: fact_invoice_lines
    description: "Fact table. One row per invoice line — the most granular sales event. Grain: invoice_line_id. Use for track-level, artist-level, and genre-level sales analysis."
    columns:
      - name: invoice_line_id
        description: "Primary key. Unique identifier for each invoice line."
        data_tests:
          - unique
          - not_null
      - name: invoice_id
        description: "Foreign key to fact_invoices."
        data_tests:
          - not_null
          - relationships:
              to: ref('fact_invoices')
              field: invoice_id
      - name: track_id
        description: "Foreign key to dim_tracks."
        data_tests:
          - not_null
          - relationships:
              to: ref('dim_tracks')
              field: track_id
      - name: customer_id
        description: "Foreign key to dim_customers."
        data_tests:
          - not_null
          - relationships:
              to: ref('dim_customers')
              field: customer_id
      - name: invoice_timestamp
        description: "Date and time the invoice was created."
        data_tests:
          - not_null
      - name: unit_price_amount
        description: "Unit price of the track on this line in USD."
        data_tests:
          - not_null
      - name: quantity
        description: "Number of units purchased."
        data_tests:
          - not_null
      - name: line_total_amount
        description: "Total for this line (unit_price_amount * quantity) in USD."
        data_tests:
          - not_null
      - name: billing_country
        description: "Billing country from the invoice header. Nullable. Useful for geographic slicing without joining dim_customers."
      - name: artist_id
        description: "Foreign key to dim_artists. Nullable. Useful for artist-level slicing without joining dim_tracks."
        data_tests:
          - relationships:
              to: ref('dim_artists')
              field: artist_id
      - name: genre_id
        description: "Genre identifier. Nullable. Useful for genre-level slicing without joining dim_tracks."
```

- [ ] **Step 2: Write fact_invoice_lines.sql**

```sql
select
    invoice_line_id,
    invoice_id,
    track_id,
    customer_id,
    invoice_timestamp,
    unit_price_amount,
    quantity,
    line_total_amount,
    billing_country,
    artist_id,
    genre_id
from {{ ref('int_invoice_lines_enriched') }}
```

- [ ] **Step 3: Build and test**

```bash
cd chinook && dbt build --select fact_invoice_lines
```
Expected: `PASS=8 WARN=0 ERROR=0 SKIP=0 TOTAL=9`

- [ ] **Step 4: Full project build — confirm everything passes end-to-end**

```bash
cd chinook && dbt build
```
Expected: All models build, all tests pass. `ERROR=0`

- [ ] **Step 5: Commit**

```bash
git add chinook/models/marts/sales/fact_invoice_lines.sql \
        chinook/models/marts/sales/fact_invoice_lines.yml
git commit -m "feat: add fact_invoice_lines"
```
