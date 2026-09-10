"""Tests for Layer 3 JSON metadata rules."""

import json
import tempfile
import unittest
from pathlib import Path

from mids_validator.inventory import build_inventory
from mids_validator.models import Severity
from mids_validator.rules.metadata import (
    mids_301_303_304_metadata_fields,
    validate_metadata,
)


def _touch(root: Path, relative_path: str) -> None:
    """Create an empty test file and any parent directories it needs."""

    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def _write_json(root: Path, relative_path: str, contents: object) -> None:
    """Write a JSON test fixture and any parent directories it needs."""

    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contents), encoding="utf-8")


class MetadataRuleTests(unittest.TestCase):
    """Test standard Layer 3 metadata-field rules."""

    def test_mids_301_and_303_report_missing_and_empty_mandatory_fields(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-01/ct/sub-01_hrpqct.nii.gz")
            _write_json(
                root,
                "sub-01/ct/sub-01_hrpqct.json",
                {
                    "XRayEnergy": 68.0,
                    "XRayExposure": 63,
                    "XRayExposureTime": 43,
                    "ConvolutionKernel": "   ",
                    "RescaleIntercept": -1000.0,
                    "RescaleSlope": 0.504,
                    "ScancoMuScaling": 8192,
                    "ScancoDensitySlope": 1569.3,
                    "ScancoDensityIntercept": -386.4,
                },
            )

            findings = mids_301_303_304_metadata_fields(
                build_inventory(root)
            )

            self.assertEqual(len(findings), 2)
            self.assertEqual(
                {(finding.rule_id, finding.severity) for finding in findings},
                {
                    ("MIDS-301", Severity.WARNING),
                    ("MIDS-303", Severity.WARNING),
                },
            )
            self.assertTrue(
                any("ScancoMuWater" in finding.message for finding in findings)
            )
            self.assertTrue(
                any(
                    "ConvolutionKernel" in finding.message
                    for finding in findings
                )
            )

    def test_mids_304_reports_only_missing_optional_field(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-01/mr-quant/sub-01_T1.nii.gz")
            _write_json(
                root,
                "sub-01/mr-quant/sub-01_T1.json",
                {
                    "EchoTime": 10,
                    "RepetitionTime": 20,
                    "FlipAngle": 15,
                    "RefocusingFlipAngle": 180,
                    "InversionTime": 100,
                    "ScanningSequence": "GR",
                    "SequenceVariant": "SP",
                    "ScanOptions": "FS",
                    "SequenceName": "example",
                    "MRAcquisitionType": "3D",
                    "ParallelReductionFactorInPlane": 2,
                    "ParallelAcquisitionTechnique": "GRAPPA",
                    "PartialFourier": 1,
                    "PartialFourierDirection": "phase",
                    "PixelBandwidth": 200,
                    "ImagingFrequency": 123.2,
                    "MagneticFieldStrength": 3,
                    "ImageType": ["ORIGINAL", "PRIMARY"],
                    "PhaseEncodingDirection": "j",
                },
            )

            findings = mids_301_303_304_metadata_fields(
                build_inventory(root)
            )

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].rule_id, "MIDS-304")
            self.assertEqual(findings[0].severity, Severity.INFO)
            self.assertIn("Manufacturer", findings[0].message)

    def test_metadata_checks_skip_layer_2_and_unknown_suffix_problems(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-01/ct/sub-01_cbct.nii.gz")
            _touch(root, "sub-01/ct/sub-01_hrpqct.nii.gz")
            malformed_path = root / "sub-01/ct/sub-01_hrpqct.json"
            malformed_path.write_text("{", encoding="utf-8")
            _touch(root, "sub-01/ct/sub-01_neuromelanin.nii.gz")

            findings = mids_301_303_304_metadata_fields(
                build_inventory(root)
            )

            self.assertEqual(findings, [])

    def test_validate_metadata_runs_registered_metadata_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _touch(root, "sub-01/ct/sub-01_cbct.nii.gz")
            _write_json(root, "sub-01/ct/sub-01_cbct.json", {})

            findings = validate_metadata(root)

            self.assertEqual(len(findings), 1)
            self.assertEqual(findings[0].rule_id, "MIDS-301")
            self.assertIn("XRayEnergy", findings[0].message)


if __name__ == "__main__":
    unittest.main()
