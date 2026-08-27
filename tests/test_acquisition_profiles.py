"""Tests for acquisition-profile loading and image-suffix interpretation."""

import tempfile
import unittest
from pathlib import Path

from mids_validator.acquisition_profiles import (
    acquisition_profile_for_suffix,
    acquisition_profiles,
    image_suffix,
    metadata_fields_for_suffix,
)


def _touch(root: Path, filename: str) -> Path:
    """Create and return an empty test file."""

    path = root / filename
    path.touch()
    return path


class AcquisitionProfileTests(unittest.TestCase):
    """Test packaged profiles and robust suffix extraction."""

    def test_packaged_acquisition_profiles_load(self) -> None:
        profiles = acquisition_profiles()

        self.assertIn("hrpqct", profiles)
        self.assertIn("mri_megre", profiles)
        self.assertEqual(profiles["mri_dess"]["folders"], ["mr-anat"])

    def test_recognized_compound_suffix_is_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dess_echo = _touch(root, "sub-01_DESS_ECHO.nii.gz")
            megre_part = _touch(root, "sub-01_part-phase_MEGRE.NII")

            self.assertEqual(image_suffix(dess_echo), "dess_echo")
            self.assertEqual(image_suffix(megre_part), "part-phase_megre")
            self.assertEqual(
                acquisition_profile_for_suffix(image_suffix(megre_part)),
                acquisition_profiles()["mri_megre"],
            )

    def test_unknown_suffix_uses_final_filename_component(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            unknown_image = _touch(
                root,
                "003_sub-01_custom_neuromelanin.nii.gz",
            )

            suffix = image_suffix(unknown_image)

            self.assertEqual(suffix, "neuromelanin")
            self.assertIsNone(acquisition_profile_for_suffix(suffix))

    def test_profile_fields_include_inheritance_and_child_overrides(self) -> None:
        dess_fields = {
            field["name"]: field for field in metadata_fields_for_suffix("dess")
        }
        megre_fields = {
            field["name"]: field
            for field in metadata_fields_for_suffix("part-phase_megre")
        }

        self.assertIn("RepetitionTime", dess_fields)
        self.assertIn("PulseSequenceType", dess_fields)
        self.assertEqual(
            megre_fields["EchoTime"]["expected_json_type"],
            "array",
        )


if __name__ == "__main__":
    unittest.main()
