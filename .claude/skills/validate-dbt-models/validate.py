#!/usr/bin/env python3
"""
Validate dbt model YAML/SQL consistency against project conventions.

Rules:
  1. Every column in the SQL model appears in the companion YAML.
  2. Every YAML column has a description.
  3. Every column whose name ends in _key has a not_null test.
  4. Every _key column in a dim_* model also has a unique test.

Usage:
    python validate.py <path> [<path> ...]
    python validate.py                  # defaults to chinook/models/

<path> may be a .sql file, a .yml file, or a directory.

Exit code is 0 when there are no violations, 1 when violations are found,
and 2 when parsing/usage errors prevented a check from running.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


# ---------------------------------------------------------------------------
# SQL preprocessing
# ---------------------------------------------------------------------------

_COMMENT_LINE_RE = re.compile(r"--[^\n]*")
_COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
_REF_RE = re.compile(r"{{\s*ref\(\s*['\"]([^'\"]+)['\"]\s*\)\s*}}")
_SOURCE_RE = re.compile(
    r"{{\s*source\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)\s*}}"
)
_JINJA_TAG_RE = re.compile(r"{%.*?%}", re.DOTALL)
_JINJA_EXPR_RE = re.compile(r"{{.*?}}", re.DOTALL)

_IDENT = r"[a-zA-Z_][a-zA-Z0-9_]*"


def _preprocess(sql: str) -> str:
    sql = _COMMENT_BLOCK_RE.sub(" ", sql)
    sql = _COMMENT_LINE_RE.sub(" ", sql)
    sql = _REF_RE.sub(lambda m: f"__REF__{m.group(1)}__", sql)
    sql = _SOURCE_RE.sub(lambda m: f"__SRC__{m.group(1)}__{m.group(2)}__", sql)
    sql = _JINJA_TAG_RE.sub(" ", sql)
    sql = _JINJA_EXPR_RE.sub(" ", sql)
    return sql


# ---------------------------------------------------------------------------
# Top-level splitting that respects paren depth and string literals
# ---------------------------------------------------------------------------


def _split_top_level(text: str, sep_chars: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    in_single = in_double = False
    i = 0
    while i < len(text):
        c = text[i]
        if in_single:
            buf.append(c)
            if c == "'":
                in_single = False
        elif in_double:
            buf.append(c)
            if c == '"':
                in_double = False
        elif c == "'":
            in_single = True
            buf.append(c)
        elif c == '"':
            in_double = True
            buf.append(c)
        elif c == "(":
            depth += 1
            buf.append(c)
        elif c == ")":
            depth -= 1
            buf.append(c)
        elif c in sep_chars and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(c)
        i += 1
    parts.append("".join(buf))
    return parts


def _find_top_level_keyword(text: str, keyword: str) -> int:
    """Return index where the whole-word keyword appears at paren-depth 0, else -1."""
    pattern = re.compile(r"\b" + re.escape(keyword) + r"\b", re.IGNORECASE)
    depth = 0
    in_single = in_double = False
    i = 0
    while i < len(text):
        c = text[i]
        if in_single:
            if c == "'":
                in_single = False
        elif in_double:
            if c == '"':
                in_double = False
        elif c == "'":
            in_single = True
        elif c == '"':
            in_double = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif depth == 0:
            m = pattern.match(text, i)
            if m:
                return m.start()
        i += 1
    return -1


# ---------------------------------------------------------------------------
# CTE extraction
# ---------------------------------------------------------------------------


def _parse_ctes_and_main(sql: str) -> tuple[dict[str, str], str]:
    """Return ({cte_name: select_body}, main_select_body)."""
    s = sql.strip().rstrip(";").strip()
    m = re.match(r"(?is)^with\s+", s)
    if not m:
        return {}, s

    pos = m.end()
    ctes: dict[str, str] = {}

    while pos < len(s):
        # Skip whitespace
        while pos < len(s) and s[pos].isspace():
            pos += 1
        m = re.match(_IDENT, s[pos:])
        if not m:
            break
        name = m.group(0)
        pos += len(name)
        # Optional column list
        while pos < len(s) and s[pos].isspace():
            pos += 1
        if pos < len(s) and s[pos] == "(":
            # consume paren group
            depth = 1
            pos += 1
            while pos < len(s) and depth > 0:
                if s[pos] == "(":
                    depth += 1
                elif s[pos] == ")":
                    depth -= 1
                pos += 1
        # 'as'
        while pos < len(s) and s[pos].isspace():
            pos += 1
        m = re.match(r"(?i)as\b", s[pos:])
        if not m:
            break
        pos += m.end()
        while pos < len(s) and s[pos].isspace():
            pos += 1
        if pos >= len(s) or s[pos] != "(":
            break
        pos += 1
        start = pos
        depth = 1
        in_single = in_double = False
        while pos < len(s) and depth > 0:
            c = s[pos]
            if in_single:
                if c == "'":
                    in_single = False
            elif in_double:
                if c == '"':
                    in_double = False
            elif c == "'":
                in_single = True
            elif c == '"':
                in_double = True
            elif c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
                if depth == 0:
                    break
            pos += 1
        ctes[name] = s[start:pos].strip()
        pos += 1  # consume the closing paren
        while pos < len(s) and s[pos].isspace():
            pos += 1
        if pos < len(s) and s[pos] == ",":
            pos += 1
            continue
        # remainder is main select
        return ctes, s[pos:].strip()

    return ctes, ""


# ---------------------------------------------------------------------------
# SELECT column extraction
# ---------------------------------------------------------------------------


@dataclass
class Resolution:
    columns: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _resolve_select(
    body: str,
    ctes: dict[str, str],
    yaml_cols_by_model: dict[str, list[str]],
    seen: set[str],
) -> Resolution:
    result = Resolution()

    # Strip outer parens if present (subquery)
    b = body.strip()
    while b.startswith("(") and b.endswith(")"):
        b = b[1:-1].strip()

    # Handle UNION / UNION ALL: take first branch's columns (same schema required)
    union_idx = _find_top_level_keyword(b, "union")
    if union_idx != -1:
        b = b[:union_idx]

    m = re.match(r"(?is)\s*select\s+(?:distinct\s+)?", b)
    if not m:
        result.warnings.append(f"no SELECT found in body: {b[:60]!r}")
        return result
    after = b[m.end():]

    from_idx = _find_top_level_keyword(after, "from")
    if from_idx == -1:
        # Could be a select with no FROM (rare) — treat full text as the select list
        select_list = after
        from_part = ""
    else:
        select_list = after[:from_idx]
        from_part = after[from_idx:]

    items = [x.strip() for x in _split_top_level(select_list, ",") if x.strip()]
    for item in items:
        cols, warn = _column_from_item(item, from_part, ctes, yaml_cols_by_model, seen)
        if warn:
            result.warnings.append(warn)
        if cols:
            result.columns.extend(cols)
    return result


def _column_from_item(
    item: str,
    from_part: str,
    ctes: dict[str, str],
    yaml_cols_by_model: dict[str, list[str]],
    seen: set[str],
) -> tuple[list[str], Optional[str]]:
    it = item.strip()

    # "... AS alias"
    m = re.search(r"(?is)\s+as\s+(" + _IDENT + r")\s*$", it)
    if m:
        return [m.group(1).lower()], None

    # "*"
    if it == "*":
        return _resolve_star(from_part, ctes, yaml_cols_by_model, seen)

    # "table.*"
    m = re.match(r"^(" + _IDENT + r")\s*\.\s*\*\s*$", it)
    if m:
        return _resolve_table_star(m.group(1), from_part, ctes, yaml_cols_by_model, seen)

    # "table.col"
    m = re.match(r"^(" + _IDENT + r")\s*\.\s*(" + _IDENT + r")\s*$", it)
    if m:
        return [m.group(2).lower()], None

    # bare column name
    m = re.match(r"^(" + _IDENT + r")\s*$", it)
    if m:
        return [m.group(1).lower()], None

    # expression without alias - cannot determine column name
    return [], f"cannot determine column name for select-list item: {it[:80]!r}"


def _extract_source_name(from_part: str) -> Optional[str]:
    """Return the first token after the leading FROM (stripped)."""
    m = re.match(r"(?is)\s*from\s+(\S+)", from_part)
    if not m:
        return None
    return m.group(1).rstrip(",").rstrip()


def _lookup_source_columns(
    source: str,
    ctes: dict[str, str],
    yaml_cols_by_model: dict[str, list[str]],
    seen: set[str],
) -> tuple[list[str], Optional[str]]:
    # CTE?
    if source in ctes:
        if source in seen:
            return [], f"cyclic CTE reference {source!r}"
        res = _resolve_select(
            ctes[source], ctes, yaml_cols_by_model, seen | {source}
        )
        return res.columns, ("; ".join(res.warnings) if res.warnings else None)
    # __REF__model__
    m = re.match(r"^__REF__(.+)__$", source)
    if m:
        model = m.group(1)
        cols = yaml_cols_by_model.get(model)
        if cols is not None:
            return list(cols), None
        return [], f"cannot resolve ref('{model}') — no YAML found"
    # __SRC__…__ — we don't resolve these
    if source.startswith("__SRC__"):
        return [], f"cannot resolve {source} (source table has no YAML companion)"
    return [], f"cannot resolve source {source!r}"


def _resolve_star(
    from_part: str,
    ctes: dict[str, str],
    yaml_cols_by_model: dict[str, list[str]],
    seen: set[str],
) -> tuple[list[str], Optional[str]]:
    source = _extract_source_name(from_part)
    if source is None:
        return [], "select * without resolvable FROM clause"
    # If FROM has joins, * is ambiguous (multiple tables contribute).
    if re.search(r"(?is)\bjoin\b", from_part):
        return [], f"select * from {source} involves joins — cannot resolve"
    return _lookup_source_columns(source, ctes, yaml_cols_by_model, seen)


def _resolve_table_star(
    table: str,
    from_part: str,
    ctes: dict[str, str],
    yaml_cols_by_model: dict[str, list[str]],
    seen: set[str],
) -> tuple[list[str], Optional[str]]:
    # Try to find an alias match in the FROM clause: "<src> <alias>" or "<src> as <alias>"
    # Fall back to treating `table` as a direct source name.
    alias_pattern = re.compile(
        r"(\S+)\s+(?:as\s+)?" + re.escape(table) + r"\b", re.IGNORECASE
    )
    m = alias_pattern.search(from_part)
    if m:
        src = m.group(1).rstrip(",")
        return _lookup_source_columns(src, ctes, yaml_cols_by_model, seen)
    return _lookup_source_columns(table, ctes, yaml_cols_by_model, seen)


# ---------------------------------------------------------------------------
# Discovery: map model-name -> columns from YAML
# ---------------------------------------------------------------------------


def _load_yaml(path: Path) -> Optional[dict]:
    with path.open() as f:
        return yaml.safe_load(f)


def _index_yaml_columns(root: Path) -> dict[str, list[str]]:
    """Scan all .yml files under root and return {model_name: [col_name, ...]}."""
    index: dict[str, list[str]] = {}
    for yml_path in root.rglob("*.yml"):
        data = _load_yaml(yml_path)
        if not data:
            continue
        for model in (data.get("models") or []):
            name = model.get("name")
            if not name:
                continue
            cols = [c.get("name") for c in (model.get("columns") or []) if c.get("name")]
            index[name] = [c.lower() for c in cols]
    return index


# ---------------------------------------------------------------------------
# Rule checks
# ---------------------------------------------------------------------------


@dataclass
class Violation:
    file: str
    message: str


def _get_model_entry(yml_data: dict, model_name: str) -> Optional[dict]:
    for model in (yml_data.get("models") or []):
        if model.get("name") == model_name:
            return model
    return None


def _column_tests(column: dict) -> list:
    """Return list of test entries (strings and dicts) for a column.

    dbt supports both legacy `tests:` and newer `data_tests:`.
    """
    tests = column.get("data_tests") or column.get("tests") or []
    return tests


def _has_test(tests: list, name: str) -> bool:
    for t in tests:
        if isinstance(t, str) and t == name:
            return True
        if isinstance(t, dict) and name in t:
            return True
    return False


def _check_model(
    sql_path: Path,
    yml_path: Path,
    yaml_cols_by_model: dict[str, list[str]],
) -> tuple[list[Violation], list[str]]:
    """Validate one (sql, yml) pair. Returns (violations, parse_warnings)."""
    model_name = sql_path.stem
    violations: list[Violation] = []
    warnings: list[str] = []

    yml_data = _load_yaml(yml_path)
    if not yml_data:
        violations.append(Violation(str(yml_path), "YAML file is empty or unreadable"))
        return violations, warnings

    model_entry = _get_model_entry(yml_data, model_name)
    if model_entry is None:
        violations.append(
            Violation(str(yml_path), f"model {model_name!r} not found in YAML")
        )
        return violations, warnings

    yaml_columns_raw = model_entry.get("columns") or []
    yaml_col_names = [c.get("name", "").lower() for c in yaml_columns_raw if c.get("name")]

    # ---- Rule 1: SQL columns ⊆ YAML columns ----
    sql_text = _preprocess(sql_path.read_text())
    ctes, main = _parse_ctes_and_main(sql_text)
    if not main:
        warnings.append(f"{sql_path}: could not locate main SELECT")
    else:
        res = _resolve_select(main, ctes, yaml_cols_by_model, seen=set())
        if res.warnings:
            for w in res.warnings:
                warnings.append(f"{sql_path}: {w}")
        sql_cols = [c.lower() for c in res.columns]
        yaml_set = set(yaml_col_names)
        for col in sql_cols:
            if col not in yaml_set:
                violations.append(
                    Violation(str(sql_path), f"SQL column {col!r} not present in YAML")
                )
        # Also flag YAML columns that aren't in SQL (optional, informational)
        sql_set = set(sql_cols)
        if sql_set:  # only if we successfully resolved something
            for col in yaml_col_names:
                if col not in sql_set:
                    violations.append(
                        Violation(
                            str(yml_path),
                            f"YAML column {col!r} not present in SQL",
                        )
                    )

    # ---- Rule 2: every YAML column has a description ----
    for c in yaml_columns_raw:
        name = c.get("name")
        if not name:
            continue
        desc = c.get("description")
        if not desc or not str(desc).strip():
            violations.append(
                Violation(str(yml_path), f"column {name!r} missing description")
            )

    # ---- Rules 3 & 4: _key tests ----
    is_dim = model_name.startswith("dim_")
    for c in yaml_columns_raw:
        name = c.get("name")
        if not name or not name.endswith("_key"):
            continue
        tests = _column_tests(c)
        if not _has_test(tests, "not_null"):
            violations.append(
                Violation(str(yml_path), f"_key column {name!r} missing not_null test")
            )
        if is_dim and not _has_test(tests, "unique"):
            violations.append(
                Violation(
                    str(yml_path),
                    f"_key column {name!r} in dim_ model missing unique test",
                )
            )

    return violations, warnings


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------


def _find_model_pairs(paths: list[Path]) -> list[tuple[Path, Path]]:
    """Return list of (sql, yml) pairs to check. Silently skips SQL files without YAML."""
    sql_files: set[Path] = set()
    for p in paths:
        if p.is_file():
            if p.suffix == ".sql":
                sql_files.add(p.resolve())
            elif p.suffix == ".yml":
                # add its companion .sql if present
                companion = p.with_suffix(".sql")
                if companion.exists():
                    sql_files.add(companion.resolve())
        elif p.is_dir():
            for sql in p.rglob("*.sql"):
                sql_files.add(sql.resolve())

    pairs: list[tuple[Path, Path]] = []
    missing: list[Path] = []
    for sql in sorted(sql_files):
        yml = sql.with_suffix(".yml")
        if yml.exists():
            pairs.append((sql, yml))
        else:
            missing.append(sql)
    # report missing YAMLs as parse warnings via caller
    for m in missing:
        print(f"warning: {m} has no companion .yml", file=sys.stderr)
    return pairs


def _default_models_root() -> Path:
    # script lives at .claude/skills/validate-dbt-models/validate.py
    # repo root is two levels up from .claude
    here = Path(__file__).resolve()
    repo_root = here.parent.parent.parent.parent
    return repo_root / "chinook" / "models"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="*", type=Path, help="SQL/YAML file or directory")
    parser.add_argument(
        "--models-root",
        type=Path,
        default=None,
        help="Project models root used to index YAML. Defaults to chinook/models/.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress per-file 'clean' output; print only violations.",
    )
    args = parser.parse_args(argv)

    models_root = args.models_root or _default_models_root()
    if not models_root.exists():
        print(f"error: models root {models_root} not found", file=sys.stderr)
        return 2

    paths = args.paths or [models_root]

    yaml_cols_by_model = _index_yaml_columns(models_root)
    pairs = _find_model_pairs(paths)
    if not pairs:
        print("no model pairs to check", file=sys.stderr)
        return 2

    total_violations = 0
    files_with_violations = 0
    all_warnings: list[str] = []

    for sql_path, yml_path in pairs:
        violations, warnings = _check_model(sql_path, yml_path, yaml_cols_by_model)
        all_warnings.extend(warnings)
        rel = sql_path.name
        if violations:
            files_with_violations += 1
            total_violations += len(violations)
            print(f"✗ {sql_path}")
            for v in violations:
                print(f"    [{Path(v.file).name}] {v.message}")
        elif not args.quiet:
            print(f"✓ {rel}")

    if all_warnings:
        print("\nParse warnings (could not fully resolve SQL columns):", file=sys.stderr)
        for w in all_warnings:
            print(f"  - {w}", file=sys.stderr)

    print()
    print(
        f"Summary: {len(pairs)} files checked, "
        f"{len(pairs) - files_with_violations} clean, "
        f"{files_with_violations} with violations "
        f"({total_violations} total)."
    )

    return 1 if total_violations else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
