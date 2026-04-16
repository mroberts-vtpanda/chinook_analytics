"""Unit tests for the naming-standards validator.

Each test copies the on-disk `fixtures/clean/` tree into a tempdir, optionally
mutates one or more files to break a single rule, then runs the validator
against the tempdir and asserts on the violations.
"""
from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

# Make validate.py importable
SKILL_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_ROOT))

import validate  # noqa: E402

CLEAN_FIXTURE = SKILL_ROOT / "tests" / "fixtures" / "clean"


class FixtureMixin:
    """Provides a fresh copy of the clean fixture in a tempdir per test."""

    def setUp(self) -> None:  # type: ignore[override]
        import tempfile
        self._tmp = tempfile.mkdtemp(prefix="enforce_naming_")
        self.project_root = Path(self._tmp) / "fixture"
        shutil.copytree(CLEAN_FIXTURE, self.project_root)
        self.models_root = self.project_root / "models"

    def tearDown(self) -> None:  # type: ignore[override]
        shutil.rmtree(self._tmp, ignore_errors=True)

    def run_validator(self) -> list[validate.Violation]:
        return validate.run_checks(self.models_root, self.project_root)


class CleanFixtureTests(FixtureMixin, unittest.TestCase):
    def test_clean_fixture_has_no_violations(self) -> None:
        self.assertEqual(self.run_validator(), [])


if __name__ == "__main__":
    unittest.main()
