"""Tests for Layer 0 dataset-structure rules."""

import tempfile
import unittest
from pathlib import Path

from mids_validator.rules.structure import validate_structure


class StructureRuleTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _touch(self, relative_path: str) -> Path:
        path = self.root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
        return path

    def _rule_ids(self) -> list[str]:
        return [finding.rule_id for finding in validate_structure(self.root)]

    def test_valid_direct_datatype_structure_has_no_findings(self) -> None:
        self._touch("sub-01/ct/sub-01_ct.nii.gz")

        self.assertEqual(validate_structure(self.root), [])

    def test_mids_001_reports_missing_dataset_path(self) -> None:
        missing_path = self.root / "does-not-exist"

        findings = validate_structure(missing_path)

        self.assertEqual([finding.rule_id for finding in findings], ["MIDS-001"])

    def test_mids_001_reports_file_instead_of_directory(self) -> None:
        file_path = self._touch("dataset.txt")

        findings = validate_structure(file_path)

        self.assertEqual([finding.rule_id for finding in findings], ["MIDS-001"])

    def test_mids_002_reports_unexpected_root_item(self) -> None:
        self._touch("sub-01/ct/sub-01_ct.nii.gz")
        self._touch("notes.txt")

        self.assertIn("MIDS-002", self._rule_ids())

    def test_mids_002_defers_case_variant_participants_table_to_layer_5(self) -> None:
        self._touch("Participants.tsv")

        self.assertNotIn("MIDS-002", self._rule_ids())

    def test_mids_003_reports_invalid_subject_identifier(self) -> None:
        self._touch("sub-bad_name/ct/sub-bad_name_ct.nii.gz")

        self.assertIn("MIDS-003", self._rule_ids())

    def test_mids_004_reports_invalid_session_identifier(self) -> None:
        self._touch("sub-01/ses-bad_name/ct/sub-01_ct.nii.gz")

        self.assertIn("MIDS-004", self._rule_ids())

    def test_mids_005_reports_mixed_subject_structure(self) -> None:
        self._touch("sub-01/ct/sub-01_ct.nii.gz")
        self._touch("sub-01/ses-01/mr-anat/sub-01_MESE.nii.gz")

        self.assertIn("MIDS-005", self._rule_ids())

    def test_mids_006_reports_unknown_datatype_directory(self) -> None:
        self._touch("sub-01/ultrasound/image.nii.gz")

        self.assertIn("MIDS-006", self._rule_ids())

    def test_mids_007_reports_empty_datatype_directory(self) -> None:
        (self.root / "sub-01" / "ct").mkdir(parents=True)

        self.assertIn("MIDS-007", self._rule_ids())

    def test_mids_008_reports_subject_without_recognized_images(self) -> None:
        (self.root / "sub-01").mkdir()

        self.assertIn("MIDS-008", self._rule_ids())

    def test_mids_009_reports_operating_system_artifact(self) -> None:
        self._touch("sub-01/ct/sub-01_ct.nii.gz")
        self._touch("sub-01/.DS_Store")

        findings = validate_structure(self.root)
        artifact_findings = [
            finding for finding in findings if finding.rule_id == "MIDS-009"
        ]

        self.assertEqual(len(artifact_findings), 1)
        self.assertEqual(artifact_findings[0].path, "sub-01/.DS_Store")


if __name__ == "__main__":
    unittest.main()
