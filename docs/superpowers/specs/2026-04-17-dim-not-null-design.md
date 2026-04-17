# Dimension Models — Universal `not_null` Coverage

**Date:** 2026-04-17
**Project:** chinook_analytics
**Scope:** `chinook/models/marts/**/dim_*.{sql,yml}`

---

## Overview

Every column in every `dim_*` model gets a `not_null` data test. Columns that are currently nullable in source (e.g., `dim_customers.company`, `dim_employees.fax`) get coalesced to a type-based default in the model SQL so the test passes. Each dim also gets a sentinel `-1` / `'Unknown'` row appended via `UNION ALL` so FKs that coalesce to `-1` still resolve through existing `relationships` tests.

The work is staged **red-first**: a single commit adds every `not_null` test up front, turning `dbt test` into a visible TODO list. Subsequent commits (one per dim) add the coalesce + sentinel row until all tests are green.

---

## Motivation

Today `not_null` coverage on dim models is uneven — keys and a handful of "required" columns have it, but most business columns don't. That makes "is this dim complete?" a judgment call rather than a test outcome. Making every column `not_null` turns the question into a binary check and forces explicit handling of every nullable column at the dim layer.

---

## Scope

### In scope

- All dim models under `chinook/models/marts/`. At time of writing:
  - `dim_customers`
  - `dim_employees`
  - `dim_artists`
  - `dim_albums`
  - `dim_tracks`
  - (Implementation will verify no others exist.)
- Every column in each dim's `.yml` gets `not_null`.
- Each dim's `.sql` gets coalesce defaults on nullable columns + a sentinel `-1` row via `UNION ALL`.

### Out of scope

- Fact tables (`fact_invoices`, `fact_invoice_lines`) — unchanged.
- Staging and intermediate models — unchanged.
- No change to the `validate-dbt-models` skill or the pre-commit hook.
- No change to existing `unique` / `relationships` data tests.
- No validator rule to enforce this convention going forward — honor system + code review.

---

## Type-based defaults

Applied uniformly across all dims. No per-column judgment.

| Column type | Default |
|---|---|
| String / varchar | `'Unknown'` |
| Integer / numeric | `0` |
| FK id column | `-1` |
| Date | `'1900-01-01'` |
| Timestamp | `'1900-01-01 00:00:00'` |
| Boolean | `false` |

"FK id column" means any column in the dim's `.yml` that has a `relationships:` data test. Those coalesce to `-1` rather than `0` so they resolve to the sentinel row in the referenced dim. Primary-key id columns are not nullable and don't need coalesce — they only appear as `-1` in the sentinel row itself.

---

## Sentinel row pattern

Every dim appends one row where the PK = `-1` and every other column is its type default. This preserves `relationships` tests when nullable FKs are coalesced to `-1`.

Sketch for `dim_employees`:

```sql
with base as (
    -- …existing model CTE…
)

select * from base

union all

select
    -1                          as employee_id,
    'Unknown'                   as first_name,
    'Unknown'                   as last_name,
    'Unknown'                   as title,
    date '1900-01-01'           as hire_date,
    date '1900-01-01'           as birth_date,
    'Unknown'                   as address,
    'Unknown'                   as city,
    'Unknown'                   as state,
    'Unknown'                   as country,
    'Unknown'                   as postal_code,
    'Unknown'                   as phone,
    'Unknown'                   as fax,
    'Unknown'                   as email,
    -1                          as reports_to_id,
    'Unknown'                   as reports_to_name
```

Notes:
- Column order and types must match `base` exactly.
- `dim_employees` is self-referencing; the sentinel's `reports_to_id = -1` points at itself, which is acceptable — the `relationships` test passes.
- The `unique` test on the PK still passes (only one `-1` row per dim).

---

## Staging: red-first TDD

### Commit 1 — add every failing `not_null` (the TODO list)

- Edits: **only** `.yml` files. Every column in every dim gets a `not_null` entry under `data_tests:`.
- No SQL changes.
- After this commit, `dbt test` exits non-zero with a concrete list of failing tests: `not_null_dim_customers_company`, `not_null_dim_employees_fax`, etc. That list is the remaining work.
- Suggested commit message: `test(dims): add not_null to every column (failing — TODO list)`.

### Commits 2–N — one per dim, turning tests green

For each dim:

1. **Coalesce nullable columns in SQL** using the type-based defaults.
2. **Append the sentinel `-1` row** via `UNION ALL`.
3. **Verify** `dbt build --select <dim_name>+` passes clean (model + tests).
4. Commit. Suggested message format: `feat(dim): make every column in <dim_name> not-null`.

Order within the batch doesn't matter much, but doing FK-target dims first (`dim_employees`, `dim_artists`, `dim_albums`) before dims that reference them (`dim_customers`, `dim_tracks`) avoids a transient state where an upstream sentinel is missing.

---

## Verification / done criteria

1. `dbt build` from a clean state exits 0 (no model errors, no test failures).
2. `dbt test --select dim_customers dim_employees dim_artists dim_albums dim_tracks` exits 0.
3. Each dim has exactly one row where PK = `-1` (the sentinel).
4. Row count of each dim equals source grain count + 1.
5. Spot-check: for each dim that is referenced by another dim's nullable FK (e.g., `dim_employees` via `dim_customers.support_rep_id`), a join from the referencing dim to the target dim returns the sentinel row for previously-null FKs — zero rows lost.

---

## Known risks / things to watch

- **FK fan-in graph.** Any dim referenced by a nullable FK — from another dim OR from a fact — must have the `-1` sentinel before its referencing model is built. Facts are out of scope here, but if a future change coalesces a fact's nullable FK, the dim sentinel is what makes it work.
- **Column inventory is incomplete until implementation.** `dim_tracks`, `dim_albums`, and the `dim_customers` support-rep satellite columns may have nullable columns not enumerated in this spec. The implementation plan will enumerate them from the current `.sql` files.
- **Sentinel row semantics leak to BI.** Analysts querying `dim_employees` will see an "Unknown" employee. Any BI-layer filter that wants "real employees only" needs `where employee_id != -1`. Acceptable trade for uniform `not_null` coverage, but worth calling out in dim model descriptions.
- **`date '1900-01-01'` is a sentinel, not a fact.** Any date-range aggregation that doesn't filter out `-1` rows will pull 1900 into its range. Same mitigation as above.
