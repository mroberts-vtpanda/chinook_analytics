---
name: enforce-naming-standards
description: Use when adding, editing, or reviewing dbt models in chinook/models/ to check that file/folder names, .sql/.yml pairing, snake_case, and per-layer materialization match the standards in docs/superpowers/specs/2026-04-15-analytics-layer-design.md. Runs automatically before every git commit via PreToolUse hook.
---

# enforce-naming-standards

## Overview

Runs a Python validator against the dbt models in this repo to enforce the mechanical naming rules from the analytics-layer design spec. Five rules:

1. **Model name prefix matches folder** — `stg_<source>__*` in `staging/<source>/`, `int_*` in `intermediate/`, `fact_*`/`dim_*` in `marts/<domain>/`.
2. **`.sql` and `.yml` are paired** — every model SQL has a sibling YAML and vice versa (leading-underscore YAMLs like `_chinook__sources.yml` are exempt from needing a SQL sibling).
3. **All names are snake_case** — file stems and folder names under `chinook/models/` match `^[a-z][a-z0-9_]*$`. YAML files may have leading underscores; SQL files may not.
4. **Materialization matches layer** — staging → `view`, intermediate → `view`, marts → `table`. Resolution: inline `{{ config(materialized=...) }}` wins, then `dbt_project.yml`, then dbt's `view` default.
5. **Sources file naming** — the source-defining YAML in `chinook/models/staging/<source>/` must be named `_<source>__sources.yml` (so `_chinook__sources.yml` for the `chinook` source).

This skill complements the existing `validate-dbt-models` skill (which checks YAML/SQL column consistency, descriptions, and `_key` tests). The two are run together by the `PreToolUse` hook on every `git commit`.

## When to use

- After editing any `.sql` or `.yml` under `chinook/models/`.
- After renaming a model file or folder.
- Before opening a PR that touches models.
- When debugging a hook failure on `git commit`.

## How to run

From the repo root:

```bash
# whole project
python3 .claude/skills/enforce-naming-standards/validate.py

# one file or one subfolder
python3 .claude/skills/enforce-naming-standards/validate.py chinook/models/marts
python3 .claude/skills/enforce-naming-standards/validate.py chinook/models/marts/customers/dim_customers.sql

# suppress the per-file ✓ lines
python3 .claude/skills/enforce-naming-standards/validate.py --quiet
```

Exit codes: `0` = clean, `1` = violations found, `2` = usage / setup error.

## Interpreting output

Each violation is printed as:

```
✗ <path>
    [<file>] <message>
```

`<path>` is the offending file (or folder, for snake_case folder violations). `<file>` is the file you need to edit (often the same as `<path>`, but for paired-file violations may differ).

## What to do when violations fire

| Violation | Fix |
|-----------|-----|
| `model name 'X' does not match folder '<folder>/' (expected prefix '<prefix>')` | Rename the file (and its `.yml` sibling) so its stem starts with the expected prefix. |
| `no companion .yml for <path>` | Create the YAML file and document the model's columns. |
| `no companion .sql for <path>` | Either add the SQL model or remove the stale YAML. |
| `folder name 'X' is not snake_case` / `file name 'X' is not snake_case` | Rename the folder/file. |
| `model 'X' has materialization 'Y', expected 'Z' for layer '<layer>'` | Either remove the inline `{{ config(materialized=...) }}` and let `dbt_project.yml` win, or update the config to match the layer's expected materialization. |
| `sources file 'X' must be named '<expected>'` | Rename the file. |

## Conventions enforced

These rules trace back to the analytics-layer design spec. See [`docs/superpowers/specs/2026-04-15-analytics-layer-design.md`](../../../docs/superpowers/specs/2026-04-15-analytics-layer-design.md) for the source of truth.

## Relationship to the pre-commit hook

A `PreToolUse` hook in `.claude/settings.json` matches Claude's `Bash` calls. When the command is `git commit`, the hook (`.claude/hooks/dbt_pre_commit.sh`) runs both this validator and the existing `validate-dbt-models` validator. If either reports violations, the commit is blocked and Claude sees the violations in the block reason. To bypass, append `--no-verify` to the commit or set `SKIP_DBT_CHECKS=1`.
