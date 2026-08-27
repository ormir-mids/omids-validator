"""Tests for Layer 2 sidecar-file rules."""

import tempfile
import unittest
from pathlib import Path

from mids_validator.inventory import build_inventory
from mids_validator.models import Severity
from mids_validator.rules.sidecars import (
    mids_201_missing_primary_json,
    mids_202_and_203_malformed_json_sidecars,
    mids_204_and_205_missing_optional_sidecars,
    mids_206_orphan_json_sidecars,
    mids_207_invalid_extra_json_structure,
)


def _touch(root: Path, relative_path: str) -> None:
    """Create an empty test file and any parent directories it needs."""

    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _write(root: Path, relative_path: str, contents: str) -> None:
    """Create a test file containing text and any needed directories."""

    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")


class SidecarRuleTests(unittest.TestCase):
    """Test Layer 2 sidecar-file rules."""

    def test_mids_201_reports_image_without_primary_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-01/mr-anat/sub-01_T1.nii.gz")
            _touch(root, "sub-01/mr-anat/sub-01_T1.JSON")
            _touch(root, "sub-01/mr-anat/sub-01_T2.NII")
            _touch(root, "sub-01/mr-anat/sub-01_T2_patient.json")

            findings = mids_201_missing_primary_json(build_inventory(root))

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].rule_id, "MIDS-201")
            self.assertEqual(
                findings[0].path,
                "sub-01/mr-anat/sub-01_T2.NII",
            )

    def test_mids_202_and_203_classify_malformed_json_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(
                root,
                "sub-01/ct/sub-01_hrpqct.json",
                """{
  "Manufacturer": "SCANCO Medical",
  "Modality": "CT",
  "KVP": 68.0,
}
""",
            )
            _write(
                root,
                "sub-01/ct/sub-01_hrpqct_extra.JSON",
                """{
  "meta": {
    "00020000": {
      "vr": "UL",
      "Value": [186]
    }
  }
""",
            )
            _write(
                root,
                "sub-01/ct/sub-01_hrpqct_patient.json",
                """{
  "PatientID": "example-subject"
}
""",
            )

            findings = mids_202_and_203_malformed_json_sidecars(
                build_inventory(root)
            )

            self.assertEqual(len(findings), 2)
            self.assertEqual(
                {
                    (finding.rule_id, finding.severity, finding.path)
                    for finding in findings
                },
                {
                    (
                        "MIDS-202",
                        Severity.ERROR,
                        "sub-01/ct/sub-01_hrpqct.json",
                    ),
                    (
                        "MIDS-203",
                        Severity.WARNING,
                        "sub-01/ct/sub-01_hrpqct_extra.JSON",
                    ),
                },
            )

    def test_mids_204_and_205_report_missing_optional_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-01/mr-quant/sub-01_T1.nii.gz")
            _write(root, "sub-01/mr-quant/sub-01_T1_patient.JSON", "{}")
            _touch(root, "sub-01/mr-quant/sub-01_T2.NII")
            _write(root, "sub-01/mr-quant/sub-01_T2_extra.json", "{")

            findings = mids_204_and_205_missing_optional_sidecars(
                build_inventory(root)
            )

            self.assertEqual(len(findings), 2)
            self.assertEqual(
                {
                    (finding.rule_id, finding.severity, finding.path)
                    for finding in findings
                },
                {
                    (
                        "MIDS-205",
                        Severity.INFO,
                        "sub-01/mr-quant/sub-01_T1.nii.gz",
                    ),
                    (
                        "MIDS-204",
                        Severity.INFO,
                        "sub-01/mr-quant/sub-01_T2.NII",
                    ),
                },
            )

    def test_mids_206_consolidates_orphan_json_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-01/ct/sub-01_ct.NII.GZ")
            _write(root, "sub-01/ct/sub-01_CT.json", "{}")
            _write(root, "sub-01/ct/sub-01_CT_patient.json", "{}")
            _write(root, "sub-01/ct/sub-01_hrpqct.json", "{}")
            _write(root, "sub-01/ct/sub-01_hrpqct_patient.JSON", "{}")
            _write(root, "sub-01/ct/sub-01_hrpqct_extra.json", "{}")

            findings = mids_206_orphan_json_sidecars(build_inventory(root))

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].rule_id, "MIDS-206")
            self.assertEqual(findings[0].severity, Severity.WARNING)
            self.assertEqual(
                findings[0].path,
                "sub-01/ct/sub-01_hrpqct.json",
            )
            self.assertIn("sub-01_hrpqct.json", findings[0].message)
            self.assertIn("sub-01_hrpqct_patient.JSON", findings[0].message)
            self.assertIn("sub-01_hrpqct_extra.json", findings[0].message)

    def test_mids_207_reports_invalid_extra_json_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write(
                root,
                "sub-01/ct/sub-01_valid_extra.json",
                '{"meta": {}, "extra": {}}',
            )
            _write(
                root,
                "sub-01/ct/sub-01_missing_extra.json",
                '{"meta": {}}',
            )
            _write(
                root,
                "sub-01/ct/sub-01_additional_extra.json",
                '{"meta": {}, "extra": {}, "other": {}}',
            )
            _write(
                root,
                "sub-01/ct/sub-01_array_extra.json",
                '["meta", "extra"]',
            )
            _write(
                root,
                "sub-01/ct/sub-01_malformed_extra.json",
                '{"meta":',
            )

            findings = mids_207_invalid_extra_json_structure(
                build_inventory(root)
            )

            self.assertEqual(len(findings), 3)
            self.assertEqual(
                {finding.rule_id for finding in findings},
                {"MIDS-207"},
            )
            self.assertEqual(
                {finding.path for finding in findings},
                {
                    "sub-01/ct/sub-01_missing_extra.json",
                    "sub-01/ct/sub-01_additional_extra.json",
                    "sub-01/ct/sub-01_array_extra.json",
                },
            )


if __name__ == "__main__":
    unittest.main()
