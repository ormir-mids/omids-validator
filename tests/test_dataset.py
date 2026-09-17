"""Tests for Layer 5 dataset-wide rules."""

import tempfile
import unittest
from pathlib import Path

from mids_validator.inventory import DatasetInventory, build_inventory
from mids_validator.models import Severity
from mids_validator.rules.dataset import (
    mids_501_conflicting_participants_table_filenames,
    mids_502_invalid_participants_table,
    mids_504_missing_participants_table,
    validate_dataset,
)


class DatasetRuleTests(unittest.TestCase):
    """Test the initial participants-table presence rule."""

    def test_mids_504_reports_absent_participants_table(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)

            findings = mids_504_missing_participants_table(build_inventory(root))

            self.assertEqual(len(findings), 1)
            finding = findings[0]
            self.assertEqual(finding.rule_id, "MIDS-504")
            self.assertEqual(finding.severity, Severity.WARNING)
            self.assertEqual(finding.path, "participants.tsv")

    def test_mids_504_accepts_exact_participants_table_name(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "participants.tsv").touch()

            self.assertEqual(
                mids_504_missing_participants_table(build_inventory(root)),
                [],
            )

    def test_mids_504_reports_case_variant_participants_table(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "Participants.tsv").touch()

            findings = mids_504_missing_participants_table(build_inventory(root))

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].rule_id, "MIDS-504")
            self.assertIn("case-variant", findings[0].message)
            self.assertIn("'Participants.tsv'", findings[0].message)

    def test_mids_501_reports_exact_and_case_variant_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            exact = root / "participants.tsv"
            variant = root / "Participants.tsv"
            exact.write_text("participant_id\n", encoding="utf-8")
            variant.write_text("participant_id\n", encoding="utf-8")
            inventory = DatasetInventory.from_items(root, (exact, variant))

            findings = mids_501_conflicting_participants_table_filenames(inventory)

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].rule_id, "MIDS-501")
            self.assertEqual(findings[0].severity, Severity.ERROR)
            self.assertIn("case-variant", findings[0].message)

    def test_mids_502_accepts_well_formed_table(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "participants.tsv").write_text(
                "participant_id\tage\nsub-01\t30\n\nsub-02\t31\n",
                encoding="utf-8",
            )

            self.assertEqual(
                mids_502_invalid_participants_table(build_inventory(root)),
                [],
            )

    def test_mids_502_reports_empty_table(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "participants.tsv").touch()

            findings = mids_502_invalid_participants_table(build_inventory(root))

            self.assertEqual(len(findings), 1)
            self.assertIn("no header", findings[0].message)

    def test_mids_502_reports_missing_participant_id_header(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "participants.tsv").write_text("age\n30\n", encoding="utf-8")

            findings = mids_502_invalid_participants_table(build_inventory(root))

            self.assertEqual(len(findings), 1)
            self.assertIn("participant_id column", findings[0].message)

    def test_mids_502_reports_malformed_rows_and_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "participants.tsv").write_text(
                "participant_id\tage\n"
                "sub-01\t30\n"
                "sub-02\n"
                "\t31\n"
                "sub-01\t32\n",
                encoding="utf-8",
            )

            findings = mids_502_invalid_participants_table(build_inventory(root))

            self.assertEqual(len(findings), 3)
            self.assertTrue(all(finding.rule_id == "MIDS-502" for finding in findings))
            self.assertIn("Row 3 has 1 field", findings[0].message)
            self.assertIn("empty participant_id", findings[1].message)
            self.assertIn("duplicates participant_id", findings[2].message)

    def test_mids_502_leaves_identifier_matching_to_mids_503(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "participants.tsv").write_text(
                "participant_id\nsubject-01\n",
                encoding="utf-8",
            )

            self.assertEqual(
                mids_502_invalid_participants_table(build_inventory(root)),
                [],
            )

    def test_mids_503_accepts_equivalent_subject_sets(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sub-01").mkdir()
            (root / "sub-02").mkdir()
            (root / "participants.tsv").write_text(
                "participant_id\nsub-02\nsub-01\n",
                encoding="utf-8",
            )

            self.assertEqual(validate_dataset(root), [])

    def test_mids_503_reports_both_directions_of_a_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sub-01").mkdir()
            (root / "sub-02").mkdir()
            (root / "participants.tsv").write_text(
                "participant_id\nsub-01\nsubject-03\n",
                encoding="utf-8",
            )

            findings = validate_dataset(root)

            self.assertEqual(len(findings), 2)
            self.assertTrue(all(finding.rule_id == "MIDS-503" for finding in findings))
            self.assertEqual(findings[0].path, "sub-02")
            self.assertIn("sub-02", findings[0].message)
            self.assertEqual(findings[1].path, "participants.tsv")
            self.assertIn("subject-03", findings[1].message)

    def test_mids_503_does_not_run_after_mids_502(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sub-01").mkdir()
            (root / "participants.tsv").write_text("age\n30\n", encoding="utf-8")

            findings = validate_dataset(root)

            self.assertEqual([finding.rule_id for finding in findings], ["MIDS-502"])


if __name__ == "__main__":
    unittest.main()
