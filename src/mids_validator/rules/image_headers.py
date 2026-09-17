"""Layer 4 rules: optional image integrity and consistency checks.

This validator-extension module inspects NIfTI headers when invoked.
They assess whether images can be used reliably, but they do not represent
requirements currently defined by the MIDS standard.
"""

from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re

import nibabel as nib
from nibabel.filebasedimages import ImageFileError

from mids_validator.file_types import nifti_stem
from mids_validator.inventory import DatasetInventory, build_inventory
from mids_validator.models import Finding
from mids_validator.rule_catalog import finding_for_rule


SUBJECT_LABEL_PATTERN = re.compile(r"(?:^|_)(sub-[A-Za-z0-9]+)_(.+)$")


@dataclass(frozen=True)
class ImageHeader:
    """Header values retained for one NIfTI image that opened successfully."""

    path: Path
    shape: tuple[int, ...]
    image_type: str | None


@dataclass(frozen=True)
class HeaderCollection:
    """Valid image headers and MIDS-401 findings from one inspection pass."""

    headers: tuple[ImageHeader, ...]
    findings: tuple[Finding, ...]


def image_type_key(image_path: Path) -> str | None:
    """Return the normalized full image label after ``sub-<ID>_``.

    This is deliberately distinct from the final acquisition suffix used for
    profile lookup. For example, ``sub-01_part-phase_MEGRE.nii.gz`` has the
    image type ``part-phase_megre``.
    """

    image_stem = nifti_stem(image_path)
    if image_stem is None:
        return None

    subject_match = SUBJECT_LABEL_PATTERN.search(image_stem)
    if subject_match is None:
        return None

    return subject_match.group(2).casefold()


def collect_image_headers(
    inventory: DatasetInventory,
) -> HeaderCollection:
    """Open each discovered NIfTI once and collect its shape or MIDS-401."""

    headers: list[ImageHeader] = []
    findings: list[Finding] = []

    for image_path in inventory.nifti_image_paths():
        try:
            image = nib.load(image_path, mmap=False)
            shape = tuple(int(dimension) for dimension in image.shape)
        except (ImageFileError, OSError, EOFError, ValueError) as error:
            findings.append(
                finding_for_rule(
                    "MIDS-401",
                    message=(
                        "NIfTI header could not be opened and interpreted: "
                        f"{error}."
                    ),
                    path=inventory.relative_path(image_path),
                )
            )
            continue

        headers.append(
            ImageHeader(
                path=image_path,
                shape=shape,
                image_type=image_type_key(image_path),
            )
        )

    return HeaderCollection(
        headers=tuple(headers),
        findings=tuple(findings),
    )


def mids_402_acquisition_dimension_outliers(
    inventory: DatasetInventory,
    headers: tuple[ImageHeader, ...],
) -> list[Finding]:
    """Report shapes outside an image type's 80 percent modal shape."""

    headers_by_image_type: dict[str, list[ImageHeader]] = {}
    for header in headers:
        if header.image_type is not None:
            headers_by_image_type.setdefault(header.image_type, []).append(header)

    findings: list[Finding] = []
    for image_type, image_headers in headers_by_image_type.items():
        if len(image_headers) < 2:
            continue

        shape_counts = Counter(header.shape for header in image_headers)
        common_shape, common_count = max(
            shape_counts.items(),
            key=lambda item: (item[1], item[0]),
        )
        total_count = len(image_headers)
        if common_count * 5 < total_count * 4:
            continue

        for header in image_headers:
            if header.shape == common_shape:
                continue

            findings.append(
                finding_for_rule(
                    "MIDS-402",
                    message=(
                        f"Image type {image_type!r} usually has shape "
                        f"{common_shape} ({common_count} of {total_count} "
                        "readable images), but this image has shape "
                        f"{header.shape}."
                    ),
                    path=inventory.relative_path(header.path),
                )
            )

    return findings


def validate_image_headers(dataset_path: Path) -> list[Finding]:
    """Run the implemented MIDS-401 and MIDS-402 checks for one dataset."""

    inventory = build_inventory(dataset_path)
    collection = collect_image_headers(inventory)
    return [
        *collection.findings,
        *mids_402_acquisition_dimension_outliers(inventory, collection.headers),
    ]
