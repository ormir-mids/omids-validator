"""Tests for Layer 1 naming and relationship rules."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mids_validator.inventory import DatasetInventory, build_inventory
from mids_validator.rules.naming import (
    mids_101_unsupported_item,
    mids_102_subject_identifier_mismatch,
    mids_103_suffix_in_wrong_datatype,
    mids_104_case_conflicting_filenames,
    validate_naming,
)


def _touch(root: Path, relative_path: str) -> None:
    """Create an empty test file and any parent directories it needs."""

    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


class NamingRuleTests(unittest.TestCase):
    """Test Layer 1 naming and relationship rules."""

    def test_mids_101_reports_unsupported_files_and_directories(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-01/mr-anat/sub-01_T1w.NII.GZ")
            _touch(root, "sub-01/mr-anat/sub-01_T1w.JSON")
            _touch(root, "sub-01/mr-anat/notes.txt")
            (root / "sub-01/mr-anat/nested").mkdir()

            findings = mids_101_unsupported_item(build_inventory(root))

            self.assertEqual(len(findings), 2)
            self.assertEqual(
                {finding.rule_id for finding in findings},
                {"MIDS-101"},
            )
            self.assertEqual(
                {finding.path for finding in findings},
                {
                    "sub-01/mr-anat/notes.txt",
                    "sub-01/mr-anat/nested",
                },
            )

    def test_mids_102_reports_subject_identifier_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-01/mr-anat/sub-01_T1w.nii.gz")
            _touch(root, "sub-01/mr-anat/sub-01_T1w.json")
            _touch(root, "sub-01/mr-anat/003_sub-01_MESE.nii.gz")
            _touch(root, "sub-01/mr-anat/sub-02_T2w.json")

            findings = mids_102_subject_identifier_mismatch(
                build_inventory(root)
            )

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].rule_id, "MIDS-102")
            self.assertEqual(findings[0].path, "sub-01/mr-anat/sub-02_T2w.json")

    def test_mids_102_reports_missing_subject_identifier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-02/ses-01/ct/ct.json")

            findings = mids_102_subject_identifier_mismatch(
                build_inventory(root)
            )

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].rule_id, "MIDS-102")
            self.assertEqual(findings[0].path, "sub-02/ses-01/ct/ct.json")

    def test_mids_103_reports_recognized_suffix_in_wrong_datatype(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-01/ct/sub-01_hrpqct.nii.gz")
            _touch(root, "sub-01/rx/sub-01_CT.NII.GZ")
            _touch(root, "sub-01/mr-anat/sub-01_neuromelanin.nii.gz")

            findings = mids_103_suffix_in_wrong_datatype(
                build_inventory(root)
            )

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].rule_id, "MIDS-103")
            self.assertEqual(findings[0].path, "sub-01/rx/sub-01_CT.NII.GZ")

    def test_mids_104_reports_case_conflicting_filenames(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            subject = root / "sub-01"
            datatype = subject / "mr-anat"
            datatype.mkdir(parents=True)

            uppercase_path = datatype / "sub-01_T1.nii.gz"
            lowercase_path = datatype / "sub-01_t1.nii.gz"
            uppercase_json_path = datatype / "sub-01_T1.JSON"
            lowercase_json_path = datatype / "sub-01_t1.json"
            inventory = DatasetInventory(
                root=root,
                root_items=(subject,),
                all_items=(
                    subject,
                    datatype,
                    uppercase_path,
                    lowercase_path,
                    uppercase_json_path,
                    lowercase_json_path,
                ),
            )
            test_files = {
                uppercase_path,
                lowercase_path,
                uppercase_json_path,
                lowercase_json_path,
            }

            with patch.object(
                Path,
                "is_file",
                autospec=True,
                side_effect=lambda path: path in test_files,
            ):
                findings = mids_104_case_conflicting_filenames(inventory)

            self.assertEqual(len(findings), 4)
            self.assertEqual(
                {finding.rule_id for finding in findings},
                {"MIDS-104"},
            )
            self.assertEqual(
                {finding.path for finding in findings},
                {
                    "sub-01/mr-anat/sub-01_T1.nii.gz",
                    "sub-01/mr-anat/sub-01_t1.nii.gz",
                    "sub-01/mr-anat/sub-01_T1.JSON",
                    "sub-01/mr-anat/sub-01_t1.json",
                },
            )

    def test_valid_two_subject_dataset_has_no_naming_findings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-01/mr-quant/sub-01_t1.NII")
            _touch(root, "sub-01/mr-quant/sub-01_t1.JSON")
            _touch(root, "sub-02/ses-01/ct/sub-02_HRPQCT.NII.GZ")
            _touch(root, "sub-02/ses-01/ct/sub-02_HRPQCT.json")

            self.assertEqual(validate_naming(root), [])

    def test_validate_naming_runs_registered_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-01/ct/sub-02_T1.nii")
            _touch(root, "sub-01/ct/notes.txt")

            findings = validate_naming(root)

            self.assertEqual(
                {finding.rule_id for finding in findings},
                {"MIDS-101", "MIDS-102", "MIDS-103"},
            )


if __name__ == "__main__":
    unittest.main()
