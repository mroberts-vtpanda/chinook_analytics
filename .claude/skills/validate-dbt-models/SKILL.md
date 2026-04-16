---
name: validate-dbt-models
description: Use when adding, editing, or reviewing dbt models in chinook/models/ (staging, intermediate, marts) to check YAML/SQL consistency — ensures every SQL column is documented in its .yml, every YAML column has a description, every `_key` column has a not_null test, and every `_key` column in a `dim_*` model also has a unique test.
---

# validate-dbt-models

## Overview

Runs a Python validator against the dbt models in this repo to catch four classes of YAML/SQL drift that CI doesn't catch by itself:

1. **Columns in SQL not in YAML** — every column selected by the model must appear in the companion `.yml`.
2. **YAML columns without descriptions** — every documented column needs a non-empty `description:`.
3. **`_key` columns without `not_null`** — by project convention, any column ending in `_key` is a surrogate key and must have a `not_null` data test.
4. **`_key` columns in `dim_*` models without `unique`** — surrogate keys on dimension tables must additionally have a `unique` data test.

A companion `YAML column not in SQL` check is also emitted so stale YAML entries get cleaned up.

## When to use

- After editing any `.sql` or `.yml` under `chinook/models/`.
- Before opening a PR that touches models.
- During review of surrogate-key or schema-consistency work.
- As a quick spot-check on a single file when debugging test failures.

## How to run

From the repo root:

```bash
# whole project
python3 .claude/skills/validate-dbt-models/validate.py

# one file (either .sql or .yml works — the companion is looked up automatically)
python3 .claude/skills/validate-dbt-models/validate.py chinook/models/marts/customers/dim_customers.sql

# one subfolder
python3 .claude/skills/validate-dbt-models/validate.py chinook/models/marts

# suppress the per-file ✓ lines
python3 .claude/skills/validate-dbt-models/validate.py --quiet
```

Exit codes: `0` = clean, `1` = violations found, `2` = usage / setup error.

## Interpreting output

Each violation is printed as:

```
✗ <sql_path>
    [<file>] <message>
```

`<file>` is the one that needs editing — `.sql` for orphan-SQL-columns, `.yml` for everything else.

Parse warnings go to stderr and look like:

```
Parse warnings (could not fully resolve SQL columns):
  - <sql_path>: <reason>
```

When a parse warning fires, **rule 1 (SQL-columns-in-YAML) is effectively skipped for that file** but rules 2–4 still run on the YAML. Typical triggers: `select *` from a `{{ source() }}` the script can't resolve, or `select *` after a join. Usually easy to resolve by selecting columns explicitly.

## Known limitations

- SQL parser handles simple `SELECT` + CTE dbt models (the style used throughout this repo). Complex subqueries with joined `table.*` may produce parse warnings.
- `UNION` branches must share a column list; only the first branch is inspected (this matches the sentinel-union pattern in the surrogate-keys plan).
- The script does not execute dbt — it relies on the sibling YAML files for `ref()` resolution. If a referenced model has no YAML, rule 1 can't fully validate and a warning is emitted.

## What to do when violations fire

| Violation | Fix |
|-----------|-----|
| `SQL column 'x' not present in YAML` | Add a `- name: x` entry with a description (and tests if `_key`) to the `.yml`. |
| `YAML column 'x' not present in SQL` | Either add the column to the SQL `SELECT` or remove the stale YAML entry. |
| `column 'x' missing description` | Add `description: "..."` to the column. |
| `_key column 'x' missing not_null test` | Add `not_null` under `data_tests:`. |
| `_key column 'x' in dim_ model missing unique test` | Add `unique` under `data_tests:` (alongside `not_null`). |

## Conventions enforced

Specific to this repo — if these ever change, update both the rules above and the relevant checks in `validate.py`:

- Surrogate-key columns are suffixed `_key` (see `docs/superpowers/plans/2026-04-16-surrogate-keys.md`).
- Dimension models are named `dim_*`.
- Both `data_tests:` (dbt ≥1.8) and the legacy `tests:` key are accepted.
