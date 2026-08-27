"""Tests for supported file recognition."""

import tempfile
import unittest
from pathlib import Path

from mids_validator.file_types import (
    is_json_file,
    is_nifti_file,
    is_supported_file,
    nifti_stem,
)


class FileTypeTests(unittest.TestCase):
    """Test case-insensitive file recognition and NIfTI stems."""

    def test_nifti_extensions_are_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            compressed = root / "sub-01_T1.NII.GZ"
            uncompressed = root / "sub-01_T2.NiI"
            compressed.touch()
            uncompressed.touch()

            self.assertTrue(is_nifti_file(compressed))
            self.assertTrue(is_nifti_file(uncompressed))
            self.assertEqual(nifti_stem(compressed), "sub-01_T1")
            self.assertEqual(nifti_stem(uncompressed), "sub-01_T2")

    def test_json_extension_is_case_insensitive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            json_path = Path(temporary_directory) / "sub-01_T1.JSON"
            json_path.touch()

            self.assertTrue(is_json_file(json_path))
            self.assertTrue(is_supported_file(json_path))

    def test_unsupported_file_and_directory_are_not_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            text_path = root / "notes.txt"
            misleading_directory = root / "not-an-image.nii.gz"
            text_path.touch()
            misleading_directory.mkdir()

            self.assertFalse(is_supported_file(text_path))
            self.assertFalse(is_supported_file(misleading_directory))
            self.assertIsNone(nifti_stem(text_path))
            self.assertIsNone(nifti_stem(misleading_directory))


if __name__ == "__main__":
    unittest.main()
