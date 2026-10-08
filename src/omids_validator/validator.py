"""Run the validation layers and assemble one complete report.

The command-line interface calls ``validate``, which builds one dataset
inventory, runs the selected rules in layer order, and returns a
``ValidationReport`` for the report writers.
"""

from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Callable

from omids_validator import __version__
from omids_validator.file_types import nifti_stem
from omids_validator.inventory import DatasetInventory, build_inventory
from omids_validator.participants import create_or_populate_participants
from omids_validator.models import (
    Finding,
    Severity,
    ValidationReport,
    ValidationRun,
)
from omids_validator.rules import (
    layer0_structure,
    layer1_naming,
    layer2_sidecars,
    layer3_metadata,
    layer5_dataset,
)


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

    return layer5_dataset.validate_dataset_inventory(inventory)


def _coverage_type(image: Path) -> str:
    """Return a report-facing image type without subject/session entities.

    The exact filename remains available to validation findings.  This
    aggregation removes the subject token and any ``ses-*`` token while
    retaining other entities such as ``loc-*``, ``part-*``, and ``run-*``.
    The datatype is included to prevent similarly named files in different
    datatype directories from being merged.
    """

    stem = nifti_stem(image) or image.name
    tokens = stem.split("_")
    subject_index = next(
        (index for index, token in enumerate(tokens) if token.casefold().startswith("sub-")),
        None,
    )
    if subject_index is not None:
        tokens = tokens[subject_index + 1 :]
    tokens = [
        token for token in tokens if not token.casefold().startswith("ses-")
    ]
    truncated_stem = "_".join(tokens) or stem
    return f"{image.parent.name} / {truncated_stem}"


def _imaging_inventory(inventory: DatasetInventory) -> dict[str, object]:
    """Summarize imaging units and coverage from one existing inventory."""

    units: list[dict[str, object]] = []
    coverage_counts: Counter[str] = Counter()
    coverage_image_counts: Counter[str] = Counter()
    image_paths = set(inventory.nifti_image_paths())

    for subject in inventory.subject_directories():
        sessions = inventory.session_directories(subject)
        unit_directories = sessions or (subject,)
        for unit_directory in unit_directories:
            images = tuple(
                image
                for datatype_directory in inventory.datatype_directories(subject)
                if datatype_directory.parent == unit_directory
                for image in inventory.children(datatype_directory)
                if image in image_paths
            )
            coverage_types = {_coverage_type(image) for image in images}
            for coverage_type in coverage_types:
                coverage_counts[coverage_type] += 1
            for image in images:
                coverage_image_counts[_coverage_type(image)] += 1

            units.append(
                {
                    "path": inventory.relative_path(unit_directory),
                    "session": (
                        unit_directory.name
                        if unit_directory in sessions
                        else None
                    ),
                    "image_count": len(images),
                    "coverage_types": sorted(coverage_types),
                }
            )

    coverage = [
        {
            "type": coverage_type,
            "count": coverage_counts[coverage_type],
            "image_count": coverage_image_counts[coverage_type],
        }
        for coverage_type in sorted(
            coverage_counts,
            key=lambda value: (-coverage_counts[value], value),
        )
    ]
    return {"coverage": coverage, "units": units}


def _inventory_summary(inventory: DatasetInventory) -> dict[str, object]:
    """Capture facts needed by future reporters without rescanning."""

    subjects = inventory.subject_directories()
    images = inventory.nifti_image_paths()
    units = 0
    direct_subjects = 0
    session_counts: Counter[str] = Counter()
    for subject in subjects:
        sessions = inventory.session_directories(subject)
        if sessions:
            units += len(sessions)
            session_counts.update(session.name for session in sessions)
        else:
            units += 1
            direct_subjects += 1

    images_by_datatype: dict[str, int] = {}
    for image in images:
        images_by_datatype[image.parent.name] = (
            images_by_datatype.get(image.parent.name, 0) + 1
        )

    imaging_inventory = _imaging_inventory(inventory)

    return {
        "subject_count": len(subjects),
        "subject_session_unit_count": units,
        "imaging_session_count": units,
        "direct_data_subject_count": direct_subjects,
        "session_counts": dict(sorted(session_counts.items())),
        "image_count": len(images),
        "images_by_datatype": dict(sorted(images_by_datatype.items())),
        "coverage": imaging_inventory["coverage"],
        "imaging_units": imaging_inventory["units"],
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

    path_finding = layer0_structure.mids_001_invalid_dataset_path(requested_path)
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
            inventory = inventory.with_added_item(created_path)
    findings: list[Finding] = []
    findings.extend(_run_rules(inventory, layer0_structure.STRUCTURE_RULES))
    findings.extend(_run_rules(inventory, layer1_naming.NAMING_RULES))
    findings.extend(_run_rules(inventory, layer2_sidecars.SIDECAR_RULES))
    findings.extend(_run_rules(inventory, layer3_metadata.METADATA_RULES))

    if inspect_images:
        from omids_validator.rules import layer4_image_headers

        collection = layer4_image_headers.collect_image_headers(inventory)
        findings.extend(collection.findings)
        findings.extend(
            layer4_image_headers.mids_402_acquisition_dimension_outliers(
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
