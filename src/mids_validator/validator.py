"""Coordinate validation and return one renderer-ready report object."""

from datetime import datetime
from pathlib import Path
from typing import Callable

from mids_validator import __version__
from mids_validator.inventory import DatasetInventory, build_inventory
from mids_validator.participants import create_or_populate_participants
from mids_validator.models import (
    Finding,
    Severity,
    ValidationReport,
    ValidationRun,
)
from mids_validator.rules import dataset, metadata, naming, sidecars, structure


SCHEMA_VERSION = "1.0"

InventoryRule = Callable[[DatasetInventory], list[Finding]]


def _run_rules(inventory: DatasetInventory, rules: tuple[InventoryRule, ...]) -> list[Finding]:
    """Run rules in their declared order against one inventory."""

    findings: list[Finding] = []
    for rule in rules:
        findings.extend(rule(inventory))
    return findings


def _dataset_findings(inventory: DatasetInventory) -> list[Finding]:
    """Run Layer 5 without causing a second inventory scan."""

    return dataset.validate_dataset_inventory(inventory)


def _inventory_summary(inventory: DatasetInventory) -> dict[str, object]:
    """Capture facts needed by future reporters without rescanning."""

    subjects = inventory.subject_directories()
    images = inventory.nifti_image_paths()
    units = 0
    direct_subjects = 0
    for subject in subjects:
        sessions = inventory.session_directories(subject)
        if sessions:
            units += len(sessions)
        else:
            units += 1
            direct_subjects += 1

    images_by_datatype: dict[str, int] = {}
    for image in images:
        images_by_datatype[image.parent.name] = (
            images_by_datatype.get(image.parent.name, 0) + 1
        )

    return {
        "subject_count": len(subjects),
        "subject_session_unit_count": units,
        "direct_data_subject_count": direct_subjects,
        "image_count": len(images),
        "images_by_datatype": dict(sorted(images_by_datatype.items())),
    }


def _ordered_findings(findings: list[Finding]) -> tuple[Finding, ...]:
    """Make output stable while retaining message variants."""

    return tuple(
        sorted(
            findings,
            key=lambda finding: (
                finding.rule_id,
                finding.path or "",
                finding.message,
            ),
        )
    )


def _summary(findings: tuple[Finding, ...]) -> dict[str, int]:
    return {
        severity.value: sum(
            finding.severity is severity for finding in findings
        )
        for severity in Severity
    }


def validate(
    dataset_path: Path,
    *,
    inspect_images: bool = False,
    participants_requested: bool = False,
    timestamp: str | None = None,
) -> ValidationReport:
    """Run all implemented layers and return one structured report.

    When requested, participant-table creation/population occurs after the
    inventory is built and before Layer 5. The inventory snapshot is updated
    only for a newly created root-level table so Layer 5 sees that action
    without rescanning the dataset.
    """

    requested_path = Path(dataset_path).expanduser()
    run = ValidationRun(
        timestamp=timestamp or datetime.now().astimezone().isoformat(),
        inspect_images=inspect_images,
        participants_requested=participants_requested,
    )

    path_finding = structure.mids_001_invalid_dataset_path(requested_path)
    if path_finding:
        findings = _ordered_findings(path_finding)
        return ValidationReport(
            schema_version=SCHEMA_VERSION,
            validator_version=__version__,
            dataset_root=str(requested_path.resolve()),
            run=run,
            findings=findings,
            summary=_summary(findings),
            inventory={},
        )

    inventory = build_inventory(requested_path)
    actions: tuple[dict[str, object], ...] = ()
    if participants_requested:
        action = create_or_populate_participants(inventory)
        actions = (action,)
        if action["operation"] == "created":
            created_path = inventory.root / "participants.tsv"
            inventory = DatasetInventory(
                root=inventory.root,
                root_items=tuple(
                    sorted((*inventory.root_items, created_path), key=str)
                ),
                all_items=tuple(
                    sorted((*inventory.all_items, created_path), key=str)
                ),
            )
    findings: list[Finding] = []
    findings.extend(
        _run_rules(
            inventory,
            (
                structure.mids_002_unexpected_root_items,
                structure.mids_003_invalid_subject_identifiers,
                structure.mids_004_invalid_session_identifiers,
                structure.mids_005_mixed_subject_structure,
                structure.mids_006_unrecognized_datatype_items,
                structure.mids_007_empty_datatype_directories,
                structure.mids_008_subjects_without_imaging_data,
                structure.mids_009_operating_system_artifacts,
            ),
        )
    )
    findings.extend(_run_rules(inventory, naming.NAMING_RULES))
    findings.extend(_run_rules(inventory, sidecars.SIDECAR_RULES))
    findings.extend(_run_rules(inventory, metadata.METADATA_RULES))

    if inspect_images:
        from mids_validator.rules import image_headers

        collection = image_headers.collect_image_headers(inventory)
        findings.extend(collection.findings)
        findings.extend(
            image_headers.mids_402_acquisition_dimension_outliers(
                inventory,
                collection.headers,
            )
        )

    findings.extend(_dataset_findings(inventory))
    ordered_findings = _ordered_findings(findings)
    return ValidationReport(
        schema_version=SCHEMA_VERSION,
        validator_version=__version__,
        dataset_root=str(inventory.root),
        run=run,
        findings=ordered_findings,
        summary=_summary(ordered_findings),
        inventory=_inventory_summary(inventory),
        actions=actions,
    )
