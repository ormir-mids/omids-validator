"""Tests for acquisition-profile loading and image-suffix interpretation."""

from copy import deepcopy
import tempfile
import unittest
from pathlib import Path

from mids_validator.acquisition_profiles import (
    MetadataRequirementsError,
    acquisition_profile_for_suffix,
    acquisition_profiles,
    image_suffix,
    load_metadata_requirements,
    metadata_fields_for_suffix,
    validate_metadata_requirements,
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

    def test_metadata_requirements_reject_unknown_parent_profile(self) -> None:
        requirements = deepcopy(load_metadata_requirements())
        requirements["profiles"]["mri_dess"][
            "inherits_json_fields_from"
        ] = "missing_profile"

        with self.assertRaisesRegex(
            MetadataRequirementsError,
            "inherits from unknown profile",
        ):
            validate_metadata_requirements(requirements)

    def test_metadata_requirements_reject_inheritance_cycle(self) -> None:
        requirements = deepcopy(load_metadata_requirements())
        requirements["profiles"]["mri_common"][
            "inherits_json_fields_from"
        ] = "mri_dess"

        with self.assertRaisesRegex(
            MetadataRequirementsError,
            "inheritance contains a cycle",
        ):
            validate_metadata_requirements(requirements)

    def test_metadata_requirements_reject_duplicate_suffix(self) -> None:
        requirements = deepcopy(load_metadata_requirements())
        requirements["profiles"]["ct"]["suffixes"].append("DESS")

        with self.assertRaisesRegex(
            MetadataRequirementsError,
            "assigned to both",
        ):
            validate_metadata_requirements(requirements)

    def test_metadata_requirements_reject_unknown_requirement_status(self) -> None:
        requirements = deepcopy(load_metadata_requirements())
        requirements["profiles"]["ct"]["json_fields"][0][
            "requirement_status"
        ] = "required"

        with self.assertRaisesRegex(
            MetadataRequirementsError,
            "requirement_status must be one of",
        ):
            validate_metadata_requirements(requirements)


if __name__ == "__main__":
    unittest.main()
