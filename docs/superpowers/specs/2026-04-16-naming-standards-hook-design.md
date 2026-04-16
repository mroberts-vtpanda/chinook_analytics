# Naming-Standards Enforcement Skill + Pre-Commit Hook

**Date:** 2026-04-16
**Project:** chinook_analytics
**Source of truth for the standards:** [`docs/superpowers/specs/2026-04-15-analytics-layer-design.md`](2026-04-15-analytics-layer-design.md)

---

## Overview

A new Claude skill, `enforce-naming-standards`, that validates the dbt models in `chinook/models/` against the mechanical naming rules defined in the analytics-layer design spec. The skill is wired into a `PreToolUse` hook so that every `git commit` Claude attempts is gated on both this new validator and the existing `validate-dbt-models` validator passing.

The hook hard-blocks the commit when either validator fails, with two documented escape hatches (`git commit --no-verify` and `SKIP_DBT_CHECKS=1`) for intentional WIP commits.

---

## High-level architecture

A new skill lives at `.claude/skills/enforce-naming-standards/`:

```
.claude/skills/enforce-naming-standards/
├── SKILL.md
├── validate.py
└── tests/
    ├── fixtures/
    │   ├── clean/          # passes all rules
    │   └── violations/     # each rule broken at least once
    ├── test_validate.py    # pytest (or unittest fallback)
    └── smoke.sh            # end-to-end hook simulation
```

A `PreToolUse` hook in `.claude/settings.json` (committed) intercepts every `Bash` tool call and delegates to a small shell handler at `.claude/hooks/dbt_pre_commit.sh` (also committed). The handler:

1. Reads the tool-input JSON from stdin.
2. Lets non-`git commit` calls through with exit `0`.
3. Honors `--no-verify` and `SKIP_DBT_CHECKS=1` as bypass mechanisms (skip checks, allow the commit, log the bypass to stderr).
4. Otherwise runs the two validators in sequence:
   ```
   python3 .claude/skills/validate-dbt-models/validate.py --quiet \
     && python3 .claude/skills/enforce-naming-standards/validate.py --quiet
   ```
5. If both pass, exits `0` (allow). If either fails, emits a JSON decision blocking the call and surfaces the captured validator output as the block reason so Claude sees the actual violations.

The block reason ends with a one-liner pointing at the bypass options:

> *To bypass, re-run with `git commit --no-verify` or `SKIP_DBT_CHECKS=1 git commit ...` — only when intentional.*

The new `validate.py` mirrors the existing one's CLI shape, output format, and exit-code convention (`0` clean, `1` violations, `2` setup error), so chaining the two with `&&` gives correct hard-block semantics without any glue code.

The existing `.claude/skills/validate-dbt-models/` skill is **not modified**.

---

## Naming validator rules

The new validator enforces five mechanically-checkable rules drawn from the analytics-layer design spec. Each violation prints in the same `✗ <path>` / `[<file>] <message>` format the existing validator uses.

### Rule N1 — Model name prefix matches folder

| Folder | Required prefix |
|---|---|
| `chinook/models/staging/<source>/` | `stg_<source>__` |
| `chinook/models/intermediate/` | `int_` |
| `chinook/models/marts/<domain>/` | `fact_` or `dim_` |

Example violation: `model name 'foo_bar' does not match folder 'staging/chinook/' (expected prefix 'stg_chinook__')`.

### Rule N2 — `.sql` and `.yml` are paired

- Every `.sql` file under `chinook/models/` must have a sibling `.yml` of the same stem.
- Every `.yml` file (other than leading-underscore files like `_chinook__sources.yml`) must have a sibling `.sql`.

### Rule N3 — All names are `snake_case`

- File stems and folder names under `chinook/models/` must match `^[a-z0-9_]+$` and not start with a digit.
- YAML files whose stem starts with a leading underscore (e.g. `_chinook__sources.yml`) are exempt from the leading-character rule but the rest of the stem must still be `snake_case`. SQL files have no leading-underscore exception.

### Rule N4 — Materialization matches layer

| Layer | Required materialization |
|---|---|
| Staging (`models/staging/**`) | `view` |
| Intermediate (`models/intermediate/**`) | `view` |
| Marts (`models/marts/**`) | `table` |

Resolution order for the effective materialization of a model:

1. `{{ config(materialized='...') }}` inside the SQL file (highest precedence).
2. The `models:` tree in `dbt_project.yml`, using path-prefix matching.
3. dbt's built-in default (`view`).

If the resolved materialization does not match the expected one for the layer, that's a violation.

### Rule N5 — Sources file naming

The sources YAML inside `chinook/models/staging/<source>/` must be named exactly `_<source>__sources.yml` (so `_chinook__sources.yml` for the `chinook` source). Any other filename for a source-defining YAML in that folder is a violation.

### Out of scope (not enforced by this validator)

- Column-suffix conventions (`_id`, `_key`, `_timestamp`, `_date`, `_amount`, `_count`, `is_*`, `has_*`) — these need semantic context the validator doesn't have. Some of the load-bearing column rules (`_key` → `not_null`, `_key` in `dim_*` → `unique`, every column documented) are already enforced by the existing `validate-dbt-models` skill.
- Model-level and column-level descriptions — already enforced by `validate-dbt-models`.
- Documentation completeness beyond what `validate-dbt-models` already checks.

---

## Hook configuration

### `.claude/settings.json` (new, committed)

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/dbt_pre_commit.sh"
          }
        ]
      }
    ]
  }
}
```

Permission allowlists stay in `.claude/settings.local.json` (per-machine, gitignored). `settings.json` carries only the hook so it doesn't pull in any user-specific state.

### `.claude/hooks/dbt_pre_commit.sh` (new, committed, executable)

Responsibilities, in order:

1. Read tool-input JSON from stdin (Claude Code passes the matched tool's input here).
2. Extract `tool_input.command`. Match against the regex `^\s*git\s+commit(\s|$)` — i.e. `git commit` as a whole word, optionally followed by arguments. If no match (e.g. `git status`, `git commit-tree`, `gitk`), exit `0` immediately so other Bash calls are unaffected.
3. If the command contains `--no-verify`, print `[dbt_pre_commit] --no-verify detected, skipping checks` to stderr and exit `0`.
4. If `$SKIP_DBT_CHECKS` is `1`, print `[dbt_pre_commit] SKIP_DBT_CHECKS=1, skipping checks` to stderr and exit `0`.
5. Run the two validators in sequence, capturing combined stdout+stderr. If both exit `0`, exit `0`.
6. Otherwise, emit a JSON decision on stdout that blocks the tool call. The `reason` field contains the captured validator output followed by the bypass one-liner.

The handler is a script (not an inline command in `settings.json`) because steps 1–6 are too much logic to inline cleanly and benefit from being independently readable and testable.

---

## Skill packaging

`SKILL.md` frontmatter for the new skill:

```yaml
---
name: enforce-naming-standards
description: Use when adding, editing, or reviewing dbt models in chinook/models/ to check that file/folder names, .sql/.yml pairing, snake_case, and per-layer materialization match the standards in docs/superpowers/specs/2026-04-15-analytics-layer-design.md. Runs automatically before every git commit via PreToolUse hook.
---
```

Body sections (parallel structure to the existing `validate-dbt-models/SKILL.md` so the two read consistently):

- **Overview** — the five rules N1–N5 in plain language, one example each.
- **When to use** — manual invocation triggers (after editing a model, before opening a PR, when renaming files or folders, debugging a hook failure).
- **How to run** — `python3 .claude/skills/enforce-naming-standards/validate.py [path] [--quiet]`. Same CLI shape as the existing validator: optional path argument (file, folder, or none = whole project), `--quiet` suppresses per-file `✓` lines, exit codes `0`/`1`/`2`.
- **Interpreting output** — same `✗ <path>` / `[<file>] <message>` format used by `validate-dbt-models`.
- **What to do when violations fire** — table mapping each rule (N1–N5) to the concrete fix.
- **Conventions enforced** — pointer back to the analytics-layer design spec as the source of truth.

`validate.py` shape:

- Single Python file. Standard library only, plus `PyYAML` for reading `dbt_project.yml` (already used by the existing validator).
- One function per rule (`check_n1_prefix_matches_folder`, `check_n2_sql_yml_pairing`, etc.), each yielding violations.
- A small CLI entry point that resolves the path argument, walks the relevant files, runs all enabled rules, prints results, and returns the right exit code.

---

## Testing strategy

### Fixture-based unit tests

`.claude/skills/enforce-naming-standards/tests/`:

- `fixtures/clean/` — minimal valid model tree (one staging model, one intermediate, one fact, one dim, with `dbt_project.yml` and a sources YAML) that should produce zero violations.
- `fixtures/violations/` — a parallel tree where each rule N1–N5 is broken in at least one file, with a known-expected violation list.
- `test_validate.py` — uses `pytest` if available, otherwise `unittest`. For each rule, asserts the validator produces the expected violations on the broken fixture and zero on the clean fixture.

### End-to-end smoke test

`tests/smoke.sh`:

1. Runs both validators against the real `chinook/models/` tree and asserts exit `0`. (The repo must currently be clean against the new rules — verified before the skill is declared done.)
2. Simulates the hook by piping a fake `git commit` JSON payload into `dbt_pre_commit.sh` and asserts it exits `0`.
3. Re-runs the simulated hook with `--no-verify` in the command and asserts exit `0` with the bypass message on stderr.
4. Re-runs the simulated hook with `SKIP_DBT_CHECKS=1` set and asserts the same bypass behavior.

### Manual verification before declaring done

- Trigger Claude to `git commit` in a deliberately-broken state (e.g. rename `dim_customers.sql` to `dim_customer.sql` to break N1) — confirm the hook blocks and Claude sees the violation in the block reason.
- Run `git commit --no-verify` through Claude — confirm it goes through.
- Run `python3 .claude/skills/enforce-naming-standards/validate.py chinook/models/marts` — confirm subfolder scoping works.
- Run a non-commit Bash call (e.g. `git status`) and confirm it is not affected by the hook.

The existing `validate-dbt-models` validator is not re-tested; it is untouched.

---

## Out of scope for this design

- Modifying or extending the existing `validate-dbt-models` skill.
- Adding column-suffix or boolean-prefix enforcement (column conventions are mostly semantic and would need dbt-manifest data).
- A real `git`-level pre-commit hook (`.git/hooks/pre-commit` or husky) that catches manual commits outside Claude. The user explicitly chose option B (Claude `PreToolUse` hook) over option A (git-native pre-commit).
- Auto-fixing violations. The validator only reports.
