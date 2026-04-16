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


class RuleN1Tests(FixtureMixin, unittest.TestCase):
    def test_staging_file_with_wrong_prefix_is_flagged(self) -> None:
        # Rename the staging model to break the stg_chinook__ prefix
        bad = self.models_root / "staging" / "chinook" / "customers.sql"
        (self.models_root / "staging" / "chinook" / "stg_chinook__customers.sql").rename(bad)
        # Also rename the YAML so we don't trip rule N2 in this test
        (self.models_root / "staging" / "chinook" / "stg_chinook__customers.yml").rename(
            self.models_root / "staging" / "chinook" / "customers.yml"
        )
        violations = [v for v in self.run_validator() if "prefix" in v.message or "match folder" in v.message]
        self.assertEqual(len(violations), 1)
        self.assertIn("stg_chinook__", violations[0].message)
        self.assertEqual(violations[0].path, bad)

    def test_intermediate_file_with_wrong_prefix_is_flagged(self) -> None:
        bad = self.models_root / "intermediate" / "customers_enriched.sql"
        (self.models_root / "intermediate" / "int_customers_enriched.sql").rename(bad)
        (self.models_root / "intermediate" / "int_customers_enriched.yml").rename(
            self.models_root / "intermediate" / "customers_enriched.yml"
        )
        violations = [v for v in self.run_validator() if "int_" in v.message]
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].path, bad)

    def test_marts_file_with_wrong_prefix_is_flagged(self) -> None:
        bad = self.models_root / "marts" / "customers" / "customers.sql"
        (self.models_root / "marts" / "customers" / "dim_customers.sql").rename(bad)
        (self.models_root / "marts" / "customers" / "dim_customers.yml").rename(
            self.models_root / "marts" / "customers" / "customers.yml"
        )
        violations = [v for v in self.run_validator() if "fact_" in v.message or "dim_" in v.message]
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].path, bad)


class RuleN2Tests(FixtureMixin, unittest.TestCase):
    def test_sql_without_yml_is_flagged(self) -> None:
        (self.models_root / "marts" / "customers" / "dim_customers.yml").unlink()
        violations = [v for v in self.run_validator() if "no companion .yml" in v.message]
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].path, self.models_root / "marts" / "customers" / "dim_customers.sql")

    def test_yml_without_sql_is_flagged(self) -> None:
        (self.models_root / "marts" / "customers" / "dim_customers.sql").unlink()
        violations = [v for v in self.run_validator() if "no companion .sql" in v.message]
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].path, self.models_root / "marts" / "customers" / "dim_customers.yml")

    def test_leading_underscore_yml_without_sql_is_not_flagged(self) -> None:
        # _chinook__sources.yml has no SQL sibling and shouldn't be flagged
        violations = [v for v in self.run_validator() if "no companion .sql" in v.message]
        self.assertEqual(violations, [])


class RuleN3Tests(FixtureMixin, unittest.TestCase):
    def test_camelcase_sql_filename_is_flagged(self) -> None:
        bad = self.models_root / "marts" / "customers" / "DimCustomers.sql"
        (self.models_root / "marts" / "customers" / "dim_customers.sql").rename(bad)
        (self.models_root / "marts" / "customers" / "dim_customers.yml").rename(
            self.models_root / "marts" / "customers" / "DimCustomers.yml"
        )
        violations = [v for v in self.run_validator() if "snake_case" in v.message and "DimCustomers" in v.message]
        self.assertGreaterEqual(len(violations), 1)

    def test_leading_underscore_sql_is_flagged(self) -> None:
        bad = self.models_root / "marts" / "customers" / "_dim_customers.sql"
        (self.models_root / "marts" / "customers" / "dim_customers.sql").rename(bad)
        (self.models_root / "marts" / "customers" / "dim_customers.yml").rename(
            self.models_root / "marts" / "customers" / "_dim_customers.yml"
        )
        violations = [v for v in self.run_validator() if "snake_case" in v.message and v.path.suffix == ".sql"]
        self.assertEqual(len(violations), 1)

    def test_leading_underscore_yml_is_allowed(self) -> None:
        # _chinook__sources.yml exists in the clean fixture; should not trip snake_case
        violations = [v for v in self.run_validator() if "snake_case" in v.message and "_chinook__sources" in v.message]
        self.assertEqual(violations, [])

    def test_camelcase_folder_is_flagged(self) -> None:
        old = self.models_root / "marts" / "customers"
        new = self.models_root / "marts" / "Customers"
        old.rename(new)
        violations = [v for v in self.run_validator() if "snake_case" in v.message and "Customers" in v.message]
        self.assertGreaterEqual(len(violations), 1)


class RuleN4Tests(FixtureMixin, unittest.TestCase):
    def test_marts_with_view_materialization_is_flagged(self) -> None:
        # Inline config that overrides the layer default
        sql = self.models_root / "marts" / "customers" / "dim_customers.sql"
        sql.write_text(
            "{{ config(materialized='view') }}\n"
            "select customer_id, first_name from {{ ref('int_customers_enriched') }}\n"
        )
        violations = [v for v in self.run_validator() if "materialization" in v.message and "marts" in v.message]
        self.assertEqual(len(violations), 1)
        self.assertIn("'view'", violations[0].message)
        self.assertIn("'table'", violations[0].message)

    def test_staging_with_table_materialization_is_flagged(self) -> None:
        sql = self.models_root / "staging" / "chinook" / "stg_chinook__customers.sql"
        sql.write_text(
            "{{ config(materialized='table') }}\n"
            "select customerid as customer_id, firstname as first_name "
            "from {{ source('chinook', 'customer') }}\n"
        )
        violations = [v for v in self.run_validator() if "materialization" in v.message and "staging" in v.message]
        self.assertEqual(len(violations), 1)

    def test_inline_config_matching_layer_is_not_flagged(self) -> None:
        # Inline config that matches the layer default — should not flag
        sql = self.models_root / "marts" / "customers" / "dim_customers.sql"
        sql.write_text(
            "{{ config(materialized='table') }}\n"
            "select customer_id, first_name from {{ ref('int_customers_enriched') }}\n"
        )
        violations = [v for v in self.run_validator() if "materialization" in v.message]
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
