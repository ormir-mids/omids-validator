"""Layer 0 rules: dataset, subject, session, and datatype structure.

Each rule accepts the shared inventory and returns findings. Rules do not print
output or modify the dataset.
"""

import re
from pathlib import Path
from typing import Callable

from mids_validator.file_types import is_nifti_file
from mids_validator.inventory import (
    VALID_DATATYPE_DIRECTORIES,
    DatasetInventory,
    build_inventory,
)
from mids_validator.models import Finding, Severity


SUBJECT_PATTERN = re.compile(r"sub-[A-Za-z0-9]+")
SESSION_PATTERN = re.compile(r"ses-[A-Za-z0-9]+")


def _is_operating_system_artifact(path: Path) -> bool:
    """Return whether a path is a common operating-system artifact."""

    lower_name = path.name.lower()
    return (
        path.name == ".DS_Store"
        or lower_name in {"thumbs.db", "desktop.ini"}
        or path.name.startswith("._")
    )


def mids_001_invalid_dataset_path(dataset_path: Path) -> list[Finding]:
    """MIDS-001: the supplied path must be a readable directory."""

    path = dataset_path.expanduser()

    if not path.exists():
        message = "Dataset path does not exist."
    elif not path.is_dir():
        message = "Dataset path is not a directory."
    else:
        try:
            next(path.iterdir(), None)
        except PermissionError:
            message = "Dataset directory is not readable."
        else:
            return []

    return [
        Finding(
            rule_id="MIDS-001",
            severity=Severity.ERROR,
            title="Invalid dataset path",
            message=message,
            path=str(path),
        )
    ]


def mids_002_unexpected_root_items(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-002: report unsupported items in the dataset root."""

    findings: list[Finding] = []

    for item in inventory.root_items:
        is_subject = item.is_dir() and item.name.startswith("sub-")
        is_participants = item.is_file() and item.name == "participants.tsv"

        if not is_subject and not is_participants and not _is_operating_system_artifact(item):
            findings.append(
                Finding(
                    rule_id="MIDS-002",
                    severity=Severity.ERROR,
                    title="Unexpected item in dataset root",
                    message=(
                        "Dataset root items must be subject directories or "
                        "participants.tsv."
                    ),
                    path=inventory.relative_path(item),
                )
            )

    return findings


def mids_003_invalid_subject_identifiers(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-003: validate subject directory identifiers."""

    return [
        Finding(
            rule_id="MIDS-003",
            severity=Severity.ERROR,
            title="Invalid subject identifier",
            message="Subject directory must follow sub-<alphanumeric>.",
            path=inventory.relative_path(subject),
        )
        for subject in inventory.subject_directories()
        if SUBJECT_PATTERN.fullmatch(subject.name) is None
    ]


def mids_004_invalid_session_identifiers(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-004: validate optional session directory identifiers."""

    findings: list[Finding] = []

    for subject in inventory.subject_directories():
        for session in inventory.session_directories(subject):
            if SESSION_PATTERN.fullmatch(session.name) is None:
                findings.append(
                    Finding(
                        rule_id="MIDS-004",
                        severity=Severity.ERROR,
                        title="Invalid session identifier",
                        message="Session directory must follow ses-<alphanumeric>.",
                        path=inventory.relative_path(session),
                    )
                )

    return findings


def mids_005_mixed_subject_structure(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-005: prevent mixing sessions and direct datatype directories."""

    findings: list[Finding] = []

    for subject in inventory.subject_directories():
        sessions = inventory.session_directories(subject)
        direct_datatypes = tuple(
            item
            for item in inventory.children(subject)
            if item.is_dir() and item.name in VALID_DATATYPE_DIRECTORIES
        )

        if sessions and direct_datatypes:
            findings.append(
                Finding(
                    rule_id="MIDS-005",
                    severity=Severity.ERROR,
                    title="Mixed session and direct-datatype structure",
                    message=(
                        "Subject must use session directories or direct "
                        "datatype directories, not both."
                    ),
                    path=inventory.relative_path(subject),
                )
            )

    return findings


def mids_006_unrecognized_datatype_items(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-006: report unsupported items where datatype folders belong."""

    findings: list[Finding] = []

    for subject in inventory.subject_directories():
        sessions = inventory.session_directories(subject)
        subject_children = inventory.children(subject)

        for item in subject_children:
            allowed_subject_item = (
                item in sessions
                or (item.is_dir() and item.name in VALID_DATATYPE_DIRECTORIES)
                or _is_operating_system_artifact(item)
            )
            if not allowed_subject_item:
                findings.append(
                    Finding(
                        rule_id="MIDS-006",
                        severity=Severity.ERROR,
                        title="Unrecognized datatype item",
                        message=(
                            "Only session or recognized datatype directories "
                            "are permitted at this level."
                        ),
                        path=inventory.relative_path(item),
                    )
                )

        for session in sessions:
            for item in inventory.children(session):
                allowed_session_item = (
                    (item.is_dir() and item.name in VALID_DATATYPE_DIRECTORIES)
                    or _is_operating_system_artifact(item)
                )
                if not allowed_session_item:
                    findings.append(
                        Finding(
                            rule_id="MIDS-006",
                            severity=Severity.ERROR,
                            title="Unrecognized datatype item",
                            message=(
                                "Only recognized datatype directories are "
                                "permitted inside a session."
                            ),
                            path=inventory.relative_path(item),
                        )
                    )

    return findings


def mids_007_empty_datatype_directories(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-007: report datatype directories containing no NIfTI images."""

    findings: list[Finding] = []

    for subject in inventory.subject_directories():
        for datatype in inventory.datatype_directories(subject):
            contains_image = any(
                is_nifti_file(item) for item in inventory.children(datatype)
            )
            if not contains_image:
                findings.append(
                    Finding(
                        rule_id="MIDS-007",
                        severity=Severity.WARNING,
                        title="Empty datatype directory",
                        message="Datatype directory contains no NIfTI images.",
                        path=inventory.relative_path(datatype),
                    )
                )

    return findings


def mids_008_subjects_without_imaging_data(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-008: report subjects with no NIfTI images in known datatypes."""

    findings: list[Finding] = []

    for subject in inventory.subject_directories():
        datatypes = inventory.datatype_directories(subject)
        contains_image = any(
            is_nifti_file(item)
            for datatype in datatypes
            for item in inventory.children(datatype)
        )

        if not contains_image:
            findings.append(
                Finding(
                    rule_id="MIDS-008",
                    severity=Severity.WARNING,
                    title="Subject contains no recognized imaging data",
                    message=(
                        "Subject contains no NIfTI images in recognized "
                        "datatype directories."
                    ),
                    path=inventory.relative_path(subject),
                )
            )

    return findings


def mids_009_operating_system_artifacts(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-009: report common operating-system artifacts anywhere in data."""

    return [
        Finding(
            rule_id="MIDS-009",
            severity=Severity.WARNING,
            title="Operating-system artifact present",
            message="Remove operating-system artifacts before sharing data.",
            path=inventory.relative_path(item),
        )
        for item in inventory.all_items
        if _is_operating_system_artifact(item)
    ]


StructureRule = Callable[[DatasetInventory], list[Finding]]

STRUCTURE_RULES: tuple[StructureRule, ...] = (
    mids_002_unexpected_root_items,
    mids_003_invalid_subject_identifiers,
    mids_004_invalid_session_identifiers,
    mids_005_mixed_subject_structure,
    mids_006_unrecognized_datatype_items,
    mids_007_empty_datatype_directories,
    mids_008_subjects_without_imaging_data,
    mids_009_operating_system_artifacts,
)


def validate_structure(dataset_path: Path) -> list[Finding]:
    """Run MIDS-001 through MIDS-009 in rule order."""

    path_findings = mids_001_invalid_dataset_path(dataset_path)
    if path_findings:
        return path_findings

    inventory = build_inventory(dataset_path)
    findings: list[Finding] = []

    for rule in STRUCTURE_RULES:
        findings.extend(rule(inventory))

    return findings
