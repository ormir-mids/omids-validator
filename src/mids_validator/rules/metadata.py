"""Layer 3 rules: JSON metadata fields and values."""

import json
from pathlib import Path
from typing import Callable

from mids_validator.acquisition_profiles import (
    image_suffix,
    metadata_fields_for_suffix,
)
from mids_validator.file_types import is_json_file, is_nifti_file, nifti_stem
from mids_validator.inventory import DatasetInventory, build_inventory
from mids_validator.models import Finding, Severity


def _is_empty_metadata_value(value: object) -> bool:
    """Return whether a present metadata value contains no usable value."""

    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    if isinstance(value, (list, dict)):
        return len(value) == 0

    return False


def mids_301_303_304_metadata_fields(
    inventory: DatasetInventory,
) -> list[Finding]:
    """Check missing and empty fields without performing MIDS-302."""

    findings: list[Finding] = []

    for subject_directory in inventory.subject_directories():
        for datatype_directory in inventory.datatype_directories(
            subject_directory
        ):
            datatype_items = inventory.children(datatype_directory)
            json_paths = {
                item.name.casefold(): item
                for item in datatype_items
                if is_json_file(item)
            }

            for image_path in datatype_items:
                if not is_nifti_file(image_path):
                    continue

                suffix = image_suffix(image_path)
                if suffix is None:
                    continue

                metadata_fields = metadata_fields_for_suffix(suffix)
                if metadata_fields is None:
                    continue

                image_stem = nifti_stem(image_path)
                if image_stem is None:
                    continue

                expected_json_name = f"{image_stem}.json".casefold()
                json_path = json_paths.get(expected_json_name)
                if json_path is None:
                    continue

                try:
                    with json_path.open(encoding="utf-8") as json_file:
                        json_data = json.load(json_file)
                except (json.JSONDecodeError, UnicodeDecodeError, OSError):
                    continue

                if not isinstance(json_data, dict):
                    continue

                for field in metadata_fields:
                    field_name = field["name"]
                    requirement_status = field["requirement_status"]

                    if requirement_status == "mandatory":
                        if field_name not in json_data:
                            findings.append(
                                Finding(
                                    rule_id="MIDS-301",
                                    severity=Severity.WARNING,
                                    title="Mandatory metadata field is missing",
                                    message=(
                                        f"Mandatory field {field_name} is "
                                        "absent from the primary JSON sidecar."
                                    ),
                                    path=inventory.relative_path(json_path),
                                )
                            )
                        elif _is_empty_metadata_value(json_data[field_name]):
                            findings.append(
                                Finding(
                                    rule_id="MIDS-303",
                                    severity=Severity.WARNING,
                                    title="Mandatory metadata field is empty",
                                    message=(
                                        f"Mandatory field {field_name} is "
                                        "present but empty."
                                    ),
                                    path=inventory.relative_path(json_path),
                                )
                            )

                    elif (
                        requirement_status == "optional"
                        and field_name not in json_data
                    ):
                        findings.append(
                            Finding(
                                rule_id="MIDS-304",
                                severity=Severity.INFO,
                                title="Optional metadata field is missing",
                                message=(
                                    f"Optional field {field_name} is absent "
                                    "from the primary JSON sidecar."
                                ),
                                path=inventory.relative_path(json_path),
                            )
                        )

    return findings


MetadataRule = Callable[[DatasetInventory], list[Finding]]

METADATA_RULES: tuple[MetadataRule, ...] = (
    mids_301_303_304_metadata_fields,
)


def validate_metadata(dataset_path: Path) -> list[Finding]:
    """Run standard 300-series metadata rules for a dataset."""

    inventory = build_inventory(dataset_path)
    findings: list[Finding] = []

    for rule in METADATA_RULES:
        findings.extend(rule(inventory))

    return findings
