"""Layer 1 rules: file naming and file-to-directory relationships.

This includes subject identifiers in filenames, known suffix placement, and
case-conflicting filenames while allowing unknown researcher-defined suffixes.
"""

import re
from pathlib import Path
from typing import Callable

from mids_validator.acquisition_profiles import (
    acquisition_profile_for_suffix,
    image_suffix,
)
from mids_validator.file_types import is_supported_file
from mids_validator.inventory import DatasetInventory, build_inventory
from mids_validator.models import Finding, Severity


SUBJECT_COMPONENT_PATTERN = re.compile(
    r"(?:^|_)(sub-[A-Za-z0-9]+)(?=_|\.|$)"
)


def mids_101_unsupported_item(inventory: DatasetInventory) -> list[Finding]:
    """MIDS-101: report unsupported items in datatype directories."""

    findings: list[Finding] = []

    for subject_directory in inventory.subject_directories():
        for datatype_directory in inventory.datatype_directories(
            subject_directory
        ):
            for item in inventory.children(datatype_directory):
                if not is_supported_file(item):
                    findings.append(
                        Finding(
                            rule_id="MIDS-101",
                            severity=Severity.ERROR,
                            title="Unsupported item in datatype directory",
                            message=(
                                "Datatype directories may contain only NIfTI "
                                "images and JSON sidecars."
                            ),
                            path=inventory.relative_path(item),
                        )
                    )

    return findings


def mids_102_subject_identifier_mismatch(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-102: require filenames to match their subject directory."""

    findings: list[Finding] = []

    for subject_directory in inventory.subject_directories():
        expected_subject = subject_directory.name

        for datatype_directory in inventory.datatype_directories(
            subject_directory
        ):
            for file_path in inventory.children(datatype_directory):
                if not is_supported_file(file_path):
                    continue

                subject_match = SUBJECT_COMPONENT_PATTERN.search(file_path.name)
                actual_subject = (
                    subject_match.group(1) if subject_match is not None else None
                )

                if actual_subject != expected_subject:
                    findings.append(
                        Finding(
                            rule_id="MIDS-102",
                            severity=Severity.ERROR,
                            title="Filename subject identifier mismatch",
                            message=(
                                f"Filename must contain the subject identifier "
                                f"{expected_subject}."
                            ),
                            path=inventory.relative_path(file_path),
                        )
                    )

    return findings


def mids_103_suffix_in_wrong_datatype(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-103: require recognized suffixes to use their datatype."""

    findings: list[Finding] = []

    for subject_directory in inventory.subject_directories():
        for datatype_directory in inventory.datatype_directories(
            subject_directory
        ):
            for file_path in inventory.children(datatype_directory):
                suffix = image_suffix(file_path)
                if suffix is None:
                    continue

                profile = acquisition_profile_for_suffix(suffix)
                if profile is None:
                    continue

                expected_datatypes = profile["folders"]
                actual_datatype = datatype_directory.name

                if actual_datatype not in expected_datatypes:
                    expected_text = " or ".join(expected_datatypes)
                    findings.append(
                        Finding(
                            rule_id="MIDS-103",
                            severity=Severity.ERROR,
                            title="Recognized suffix in wrong datatype directory",
                            message=(
                                f"Suffix {suffix} belongs in {expected_text}, "
                                f"not {actual_datatype}."
                            ),
                            path=inventory.relative_path(file_path),
                        )
                    )

    return findings


def mids_104_case_conflicting_filenames(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-104: report filenames that differ only by capitalization."""

    case_groups: dict[tuple[Path, str], list[Path]] = {}

    for subject_directory in inventory.subject_directories():
        for datatype_directory in inventory.datatype_directories(
            subject_directory
        ):
            for file_path in inventory.children(datatype_directory):
                if not is_supported_file(file_path):
                    continue

                comparison_key = (
                    file_path.parent,
                    file_path.name.casefold(),
                )
                case_groups.setdefault(comparison_key, []).append(file_path)

    findings: list[Finding] = []

    for conflicting_paths in case_groups.values():
        if len(conflicting_paths) < 2:
            continue

        conflicting_names = ", ".join(
            path.name for path in conflicting_paths
        )
        for file_path in conflicting_paths:
            findings.append(
                Finding(
                    rule_id="MIDS-104",
                    severity=Severity.WARNING,
                    title="Case-conflicting filename",
                    message=(
                        "Filename differs only by capitalization from another "
                        f"file in the same directory: {conflicting_names}."
                    ),
                    path=inventory.relative_path(file_path),
                )
            )

    return findings


NamingRule = Callable[[DatasetInventory], list[Finding]]

NAMING_RULES: tuple[NamingRule, ...] = (
    mids_101_unsupported_item,
    mids_102_subject_identifier_mismatch,
    mids_103_suffix_in_wrong_datatype,
    mids_104_case_conflicting_filenames,
)


def validate_naming(dataset_path: Path) -> list[Finding]:
    """Run 100 series MIDS rules on the dataset at the given path."""

    inventory = build_inventory(dataset_path)
    findings: list[Finding] = []

    for rule in NAMING_RULES:
        findings.extend(rule(inventory))

    return findings
