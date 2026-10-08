"""Tests for implemented Layer 4 NIfTI header checks."""

import tempfile
import unittest
from pathlib import Path

import nibabel as nib
import numpy as np

from omids_validator.inventory import build_inventory
from omids_validator.models import Severity
from omids_validator.rules.layer4_image_headers import (
    collect_image_headers,
    image_type_key,
    mids_402_acquisition_dimension_outliers,
    validate_image_headers,
)


def _write_nifti(
    root: Path,
    relative_path: str,
    shape: tuple[int, ...] = (4, 5, 6),
) -> Path:
    """Write a small valid NIfTI image for a header-reading test."""

    image_path = root / relative_path
    image_path.parent.mkdir(parents=True, exist_ok=True)
    image = nib.Nifti1Image(np.zeros(shape, dtype=np.int16), np.eye(4))
    nib.save(image, image_path)
    return image_path


class ImageHeaderRuleTests(unittest.TestCase):
    """Test one-pass NIfTI header collection and Layer 4 findings."""

    def test_collect_image_headers_returns_shape_for_valid_nifti(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            image_path = _write_nifti(
                root,
                "sub-01/mr-anat/sub-01_T1w.nii.gz",
            )

            collection = collect_image_headers(build_inventory(root))

            self.assertEqual(collection.findings, ())
            self.assertEqual(len(collection.headers), 1)
            self.assertEqual(collection.headers[0].path, image_path.resolve())
            self.assertEqual(collection.headers[0].shape, (4, 5, 6))
            self.assertEqual(collection.headers[0].image_type, "t1w")

    def test_image_type_key_preserves_full_post_subject_label(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            image_path = _write_nifti(
                root,
                "sub-01/mr-anat/003_sub-01_part-phase_MEGRE.nii.gz",
            )

            self.assertEqual(image_type_key(image_path), "part-phase_megre")

    def test_mids_401_reports_malformed_nifti_once(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            image_path = root / "sub-01/ct/sub-01_ct.nii.gz"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"not a NIfTI file")

            collection = collect_image_headers(build_inventory(root))
            findings = validate_image_headers(root)

            self.assertEqual(collection.headers, ())
            self.assertEqual(len(collection.findings), 1)
            self.assertEqual(len(findings), 1)
            finding = findings[0]
            self.assertEqual(finding.rule_id, "MIDS-401")
            self.assertEqual(finding.severity, Severity.ERROR)
            self.assertEqual(finding.path, "sub-01/ct/sub-01_ct.nii.gz")
            self.assertIn("could not be opened", finding.message)

    def test_mids_402_reports_shapes_outside_eighty_percent_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for subject_id in range(1, 6):
                shape = (4, 5, 6) if subject_id < 5 else (3, 5, 6)
                _write_nifti(
                    root,
                    f"sub-{subject_id:02d}/mr-anat/sub-{subject_id:02d}_MEGRE.nii.gz",
                    shape,
                )

            findings = validate_image_headers(root)

            self.assertEqual(len(findings), 1)
            finding = findings[0]
            self.assertEqual(finding.rule_id, "MIDS-402")
            self.assertEqual(finding.severity, Severity.WARNING)
            self.assertEqual(
                finding.path,
                "sub-05/mr-anat/sub-05_MEGRE.nii.gz",
            )
            self.assertIn("4 of 5", finding.message)

    def test_mids_402_suppresses_groups_without_an_eighty_percent_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for subject_id, shape in enumerate(
                ((4, 5, 6), (4, 5, 6), (4, 5, 6), (3, 5, 6)),
                start=1,
            ):
                _write_nifti(
                    root,
                    f"sub-{subject_id:02d}/ct/sub-{subject_id:02d}_hrpqct.nii.gz",
                    shape,
                )

            inventory = build_inventory(root)
            collection = collect_image_headers(inventory)

            self.assertEqual(
                mids_402_acquisition_dimension_outliers(
                    inventory,
                    collection.headers,
                ),
                [],
            )

    def test_mids_402_does_not_combine_distinct_megre_component_types(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            for subject_id in range(1, 6):
                phase_shape = (4, 5, 6) if subject_id < 5 else (3, 5, 6)
                _write_nifti(
                    root,
                    f"sub-{subject_id:02d}/mr-anat/"
                    f"sub-{subject_id:02d}_part-phase_MEGRE.nii.gz",
                    phase_shape,
                )
                _write_nifti(
                    root,
                    f"sub-{subject_id:02d}/mr-anat/"
                    f"sub-{subject_id:02d}_part-real_MEGRE.nii.gz",
                    (3, 5, 6),
                )

            inventory = build_inventory(root)
            collection = collect_image_headers(inventory)
            findings = mids_402_acquisition_dimension_outliers(
                inventory,
                collection.headers,
            )

            self.assertEqual(len(findings), 1)
            self.assertEqual(
                findings[0].path,
                "sub-05/mr-anat/sub-05_part-phase_MEGRE.nii.gz",
            )


if __name__ == "__main__":
    unittest.main()
