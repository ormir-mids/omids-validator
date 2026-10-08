"""Layer 2: check the JSON sidecar files that accompany each image.

These rules find missing, unreadable, incorrectly named, and unpaired primary,
patient, and extra JSON files.
"""

import json
from pathlib import Path
from typing import Callable

from omids_validator.file_types import is_json_file, is_nifti_file, nifti_stem
from omids_validator.inventory import DatasetInventory, build_inventory
from omids_validator.models import Finding
from omids_validator.rule_catalog import finding_for_rule


def _image_stem_for_json_sidecar(json_path: Path) -> str:
    """Return the image stem represented by a primary or optional sidecar."""

    json_stem = json_path.name[:-5]
    normalized_stem = json_stem.casefold()

    if normalized_stem.endswith("_patient"):
        return json_stem[:-8]
    if normalized_stem.endswith("_extra"):
        return json_stem[:-6]

    return json_stem


def mids_201_missing_primary_json(inventory: DatasetInventory) -> list[Finding]:
    """MIDS-201: require one primary JSON sidecar for every NIfTI image."""

    findings: list[Finding] = []

    for subject_directory in inventory.subject_directories():
        for datatype_directory in inventory.datatype_directories(
            subject_directory
        ):
            datatype_items = inventory.children(datatype_directory)
            json_names = {
                item.name.casefold()
                for item in datatype_items
                if is_json_file(item)
            }

            for image_path in datatype_items:
                if not is_nifti_file(image_path):
                    continue

                image_stem = nifti_stem(image_path)
                if image_stem is None:
                    continue

                expected_json_name = f"{image_stem}.json"
                if expected_json_name.casefold() not in json_names:
                    findings.append(
                        finding_for_rule(
                            "MIDS-201",
                            message=(
                                "NIfTI image requires a primary JSON sidecar "
                                f"named {expected_json_name}."
                            ),
                            path=inventory.relative_path(image_path),
                        )
                    )

    return findings


def mids_202_and_203_malformed_json_sidecars(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-202/203: report malformed primary and optional JSON sidecars."""

    findings: list[Finding] = []

    for subject_directory in inventory.subject_directories():
        for datatype_directory in inventory.datatype_directories(
            subject_directory
        ):
            for json_path in inventory.children(datatype_directory):
                if not is_json_file(json_path):
                    continue

                try:
                    with json_path.open(encoding="utf-8") as json_file:
                        json.load(json_file)
                except json.JSONDecodeError:
                    problem = "JSON syntax is invalid."
                except UnicodeDecodeError:
                    problem = "JSON file is not valid UTF-8 text."
                except OSError:
                    problem = "JSON file could not be read."
                else:
                    continue

                normalized_name = json_path.name.casefold()
                is_optional = normalized_name.endswith(
                    ("_patient.json", "_extra.json")
                )

                if is_optional:
                    rule_id = "MIDS-203"
                else:
                    rule_id = "MIDS-202"

                findings.append(
                    finding_for_rule(
                        rule_id,
                        message=problem,
                        path=inventory.relative_path(json_path),
                    )
                )

    return findings


def mids_204_and_205_missing_optional_sidecars(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-204/205: report absent patient and extra JSON sidecars."""

    findings: list[Finding] = []
    optional_sidecars = (
        ("patient", "MIDS-204"),
        ("extra", "MIDS-205"),
    )

    for subject_directory in inventory.subject_directories():
        for datatype_directory in inventory.datatype_directories(
            subject_directory
        ):
            datatype_items = inventory.children(datatype_directory)
            json_names = {
                item.name.casefold()
                for item in datatype_items
                if is_json_file(item)
            }

            for image_path in datatype_items:
                if not is_nifti_file(image_path):
                    continue

                image_stem = nifti_stem(image_path)
                if image_stem is None:
                    continue

                for qualifier, rule_id in optional_sidecars:
                    expected_json_name = f"{image_stem}_{qualifier}.json"
                    if expected_json_name.casefold() in json_names:
                        continue

                    findings.append(
                        finding_for_rule(
                            rule_id,
                            message=(
                                "Optional JSON sidecar is absent; expected "
                                f"{expected_json_name}."
                            ),
                            path=inventory.relative_path(image_path),
                        )
                    )

    return findings


def mids_206_orphan_json_sidecars(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-206: report JSON sidecar groups without a NIfTI image."""

    findings: list[Finding] = []

    for subject_directory in inventory.subject_directories():
        for datatype_directory in inventory.datatype_directories(
            subject_directory
        ):
            datatype_items = inventory.children(datatype_directory)
            nifti_stems: set[str] = set()

            for item in datatype_items:
                image_stem = nifti_stem(item)

                if image_stem is not None:
                    nifti_stems.add(image_stem.casefold())

            json_groups: dict[str, list[Path]] = {}

            for json_path in datatype_items:
                if not is_json_file(json_path):
                    continue

                image_stem = _image_stem_for_json_sidecar(json_path)
                normalized_stem = image_stem.casefold()
                json_groups.setdefault(normalized_stem, []).append(json_path)

            for normalized_stem, json_paths in json_groups.items():
                if normalized_stem in nifti_stems:
                    continue

                primary_name = f"{normalized_stem}.json"
                representative_path = next(
                    (
                        path
                        for path in json_paths
                        if path.name.casefold() == primary_name
                    ),
                    json_paths[0],
                )
                orphaned_names = ", ".join(path.name for path in json_paths)

                findings.append(
                    finding_for_rule(
                        "MIDS-206",
                        message=(
                            "JSON sidecars have no corresponding NIfTI image: "
                            f"{orphaned_names}."
                        ),
                        path=inventory.relative_path(representative_path),
                    )
                )

    return findings


def mids_207_invalid_extra_json_structure(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-207: require exact meta and extra top-level structures."""

    findings: list[Finding] = []
    expected_keys = {"meta", "extra"}

    for subject_directory in inventory.subject_directories():
        for datatype_directory in inventory.datatype_directories(
            subject_directory
        ):
            for json_path in inventory.children(datatype_directory):
                if not is_json_file(json_path):
                    continue
                if not json_path.name.casefold().endswith("_extra.json"):
                    continue

                try:
                    with json_path.open(encoding="utf-8") as json_file:
                        json_data = json.load(json_file)
                except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                    continue

                is_json_object = isinstance(json_data, dict)
                has_expected_keys = (
                    is_json_object
                    and set(json_data.keys()) == expected_keys
                )

                if not has_expected_keys:
                    findings.append(
                        finding_for_rule(
                            "MIDS-207",
                            message=(
                                "Extra JSON sidecar must be an object with "
                                "exactly the top-level keys meta and extra."
                            ),
                            path=inventory.relative_path(json_path),
                        )
                    )

    return findings


SidecarRule = Callable[[DatasetInventory], list[Finding]]

SIDECAR_RULES: tuple[SidecarRule, ...] = (
    mids_201_missing_primary_json,
    mids_202_and_203_malformed_json_sidecars,
    mids_204_and_205_missing_optional_sidecars,
    mids_206_orphan_json_sidecars,
    mids_207_invalid_extra_json_structure,
)


def validate_sidecars(dataset_path: Path) -> list[Finding]:
    """Run 200-series MIDS rules on the dataset at the given path."""

    inventory = build_inventory(dataset_path)
    findings: list[Finding] = []

    for rule in SIDECAR_RULES:
        findings.extend(rule(inventory))

    return findings
