#!/usr/bin/env python3
"""
Validate dbt model file/folder naming, pairing, snake_case, materialization,
and sources file naming against the analytics-layer design spec.

Rules:
  N1. Model name prefix matches folder.
  N2. Every .sql has a sibling .yml (and vice versa, except leading-underscore YAMLs).
  N3. File stems and folder names under chinook/models/ are snake_case.
  N4. Materialization matches layer (staging/intermediate=view, marts=table).
  N5. Sources YAML in staging/<source>/ is named _<source>__sources.yml.

Usage:
    python validate.py [<path>] [--quiet]
    python validate.py                  # defaults to chinook/models/

<path> may be a .sql file, a .yml file, or a directory.

Exit code is 0 when there are no violations, 1 when violations are found,
and 2 when parsing/usage errors prevented a check from running.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import yaml


REPO_ROOT_DEFAULT = Path("chinook")
MODELS_SUBPATH = Path("models")


@dataclass(frozen=True)
class Violation:
    """One naming-standard violation.

    path:     the offending file or folder (used for the ✗ header line)
    edit:     the file the engineer needs to edit (printed in the [<file>] tag)
    message:  human-readable description of what's wrong
    """
    path: Path
    edit: Path
    message: str


def _iter_models(path: Path) -> Iterator[Path]:
    """Yield every .sql and .yml file under `path` that is inside `models_root`."""
    if path.is_file():
        yield path
        return
    for entry in sorted(path.rglob("*")):
        if entry.is_file() and entry.suffix in (".sql", ".yml"):
            yield entry


def _walk_up_for_project(start: Path) -> Path | None:
    """Walk up from `start` looking for a dir containing dbt_project.yml. None if not found."""
    candidate = start if start.is_dir() else start.parent
    while True:
        if (candidate / "dbt_project.yml").is_file():
            return candidate
        if candidate == candidate.parent:
            return None
        candidate = candidate.parent


def _resolve_target(arg: str | None) -> tuple[Path, Path, Path]:
    """Resolve the CLI path argument.

    Returns (target_to_walk, models_root, project_root).
    Raises SystemExit(2) if the path can't be located.
    """
    if arg is None:
        project_root = (
            _walk_up_for_project(Path.cwd())
            or _walk_up_for_project(Path(__file__).resolve().parent)
            or REPO_ROOT_DEFAULT.resolve()
        )
    else:
        p = Path(arg).resolve()
        project_root = _walk_up_for_project(p)
        if project_root is None:
            print(f"error: could not locate dbt_project.yml above {p}", file=sys.stderr)
            raise SystemExit(2)

    models_root = project_root / MODELS_SUBPATH
    if not models_root.is_dir():
        print(f"error: {models_root} is not a directory", file=sys.stderr)
        raise SystemExit(2)

    target = Path(arg).resolve() if arg else models_root
    return target, models_root, project_root


def run_checks(models_root: Path, project_root: Path) -> list[Violation]:
    """Run all rule checks against the given models tree. Returns sorted violations.

    No rules are implemented yet — they are added in subsequent tasks (N1–N5).
    """
    violations: list[Violation] = []
    # Rules will be added in subsequent tasks.
    return sorted(violations, key=lambda v: (str(v.path), v.message))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", nargs="?", default=None, help="file or directory to validate")
    parser.add_argument("--quiet", action="store_true", help="suppress per-file ✓ lines")
    args = parser.parse_args(argv)

    target, models_root, project_root = _resolve_target(args.path)
    violations = run_checks(models_root, project_root)

    # Group violations by path for printing
    by_path: dict[Path, list[Violation]] = {}
    for v in violations:
        by_path.setdefault(v.path, []).append(v)

    # Files we walked (for ✓ printing) — only those under target
    if target.is_file():
        walked = [target]
    else:
        walked = [p for p in _iter_models(target)]

    for f in walked:
        relevant = by_path.get(f, [])
        # Rule N3 may attach violations to folder paths; surface them against each walked file under that folder.
        for path, vs in by_path.items():
            if path != f and path.is_dir() and f.is_relative_to(path):
                relevant = relevant + vs
        if relevant:
            try:
                rel = f.relative_to(project_root)
            except ValueError:
                rel = f
            print(f"✗ {rel}")
            for v in relevant:
                edit_rel = v.edit
                try:
                    edit_rel = v.edit.relative_to(project_root)
                except ValueError:
                    pass
                print(f"    [{edit_rel}] {v.message}")
        elif not args.quiet:
            try:
                rel = f.relative_to(project_root)
            except ValueError:
                rel = f
            print(f"✓ {rel}")

    # Rule N3 folder-only violations: any folder violation whose path isn't an ancestor of any walked file.
    folder_only = [v for path, vs in by_path.items() for v in vs if path.is_dir() and not any(w.is_relative_to(path) for w in walked)]
    for v in folder_only:
        try:
            rel = v.path.relative_to(project_root)
        except ValueError:
            rel = v.path
        print(f"✗ {rel}/")
        edit_rel = v.edit
        try:
            edit_rel = v.edit.relative_to(project_root)
        except ValueError:
            pass
        print(f"    [{edit_rel}] {v.message}")

    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
