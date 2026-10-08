"""Recognize supported image and JSON files from their names.

These small path helpers are shared by the dataset inventory, the validation
coordinator, the scan-type definitions, and Layers 0 through 4.
"""

from pathlib import Path


SUPPORTED_FILE_EXTENSIONS = (".nii", ".nii.gz", ".json")


def is_nifti_file(path: Path) -> bool:
    """Return whether a file has a supported NIfTI extension."""

    normalized_name = path.name.casefold()
    return path.is_file() and normalized_name.endswith((".nii", ".nii.gz"))


def is_json_file(path: Path) -> bool:
    """Return whether a file has a JSON extension."""

    return path.is_file() and path.name.casefold().endswith(".json")


def is_supported_file(path: Path) -> bool:
    """Return whether a file is a supported NIfTI image or JSON sidecar."""

    return path.is_file() and path.name.casefold().endswith(
        SUPPORTED_FILE_EXTENSIONS
    )


def nifti_stem(path: Path) -> str | None:
    """Return a NIfTI filename without its extension, or ``None``."""

    normalized_name = path.name.casefold()

    if not path.is_file():
        return None
    if normalized_name.endswith(".nii.gz"):
        return path.name[:-7]
    if normalized_name.endswith(".nii"):
        return path.name[:-4]

    return None
