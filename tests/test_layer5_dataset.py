"""Tests for Layer 5 dataset-wide rules."""

import json
import tempfile
import unittest
from pathlib import Path

from omids_validator.inventory import DatasetInventory, build_inventory
from omids_validator.models import Severity
from omids_validator.rules.layer5_dataset import (
    mids_501_conflicting_participants_table_filenames,
    mids_502_invalid_participants_table,
    mids_504_missing_participants_table,
    mids_505_patient_age_differs_within_session,
    mids_506_patient_sex_differs_within_subject,
    validate_dataset,
)


def _write_patient_json(
    root: Path,
    relative_path: str,
    contents: dict[str, object],
) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contents), encoding="utf-8")
    return path


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

    def test_mids_505_reports_different_ages_within_one_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/ses-01/mr-anat/sub-01_scan1_patient.json",
                {"Age": "025Y"},
            )
            _write_patient_json(
                root,
                "sub-01/ses-01/ct/sub-01_scan2_patient.json",
                {"Age": "026Y"},
            )

            findings = mids_505_patient_age_differs_within_session(
                build_inventory(root)
            )

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].rule_id, "MIDS-505")
            self.assertEqual(findings[0].severity, Severity.WARNING)
            self.assertEqual(findings[0].path, "sub-01/ses-01")
            self.assertNotIn("025Y", findings[0].message)
            self.assertNotIn("026Y", findings[0].message)

    def test_mids_505_allows_age_to_change_between_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/ses-01/mr-anat/sub-01_scan_patient.json",
                {"Age": "025Y"},
            )
            _write_patient_json(
                root,
                "sub-01/ses-02/mr-anat/sub-01_scan_patient.json",
                {"Age": "026Y"},
            )

            findings = mids_505_patient_age_differs_within_session(
                build_inventory(root)
            )

            self.assertEqual(findings, [])

    def test_mids_505_treats_direct_layout_as_one_session(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/mr-anat/sub-01_scan1_patient.json",
                {"Age": "025Y"},
            )
            _write_patient_json(
                root,
                "sub-01/ct/sub-01_scan2_patient.json",
                {"Age": "026Y"},
            )

            findings = mids_505_patient_age_differs_within_session(
                build_inventory(root)
            )

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].path, "sub-01")
            self.assertIn("implicit imaging session", findings[0].message)

    def test_mids_506_reports_different_sex_values_across_sessions(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/ses-01/mr-anat/sub-01_scan_patient.json",
                {"Sex": "F"},
            )
            _write_patient_json(
                root,
                "sub-01/ses-02/mr-anat/sub-01_scan_patient.json",
                {"Sex": "M"},
            )

            findings = mids_506_patient_sex_differs_within_subject(
                build_inventory(root)
            )

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].rule_id, "MIDS-506")
            self.assertEqual(findings[0].severity, Severity.INFO)
            self.assertEqual(findings[0].path, "sub-01")
            self.assertNotIn('"F"', findings[0].message)
            self.assertNotIn('"M"', findings[0].message)

    def test_demographic_rules_run_without_participants_table(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/mr-anat/sub-01_scan1_patient.json",
                {"Age": "025Y", "Sex": "F"},
            )
            _write_patient_json(
                root,
                "sub-01/ct/sub-01_scan2_patient.json",
                {"Age": "026Y", "Sex": "M"},
            )

            findings = validate_dataset(root)
            rule_ids = {finding.rule_id for finding in findings}

            self.assertIn("MIDS-504", rule_ids)
            self.assertIn("MIDS-505", rule_ids)
            self.assertIn("MIDS-506", rule_ids)


if __name__ == "__main__":
    unittest.main()
