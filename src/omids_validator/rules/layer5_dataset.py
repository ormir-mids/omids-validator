"""Layer 5: compare participant information across the dataset.

These rules compare subject folders with ``participants.tsv`` and check values
that should agree within a subject or imaging session.
"""

from pathlib import Path

from omids_validator.inventory import DatasetInventory, build_inventory
from omids_validator.models import Finding
from omids_validator.patient_metadata import (
    PatientMetadataCollection,
    collect_patient_metadata,
)
from omids_validator.participant_table import (
    ParticipantTable,
    ParticipantTableProblem,
    read_participants_table,
)
from omids_validator.rule_catalog import finding_for_rule


def _participants_table_names(
    inventory: DatasetInventory,
) -> tuple[bool, list[str]]:
    """Return exact-table presence and differently cased table names."""

    exact_table_exists = any(
        item.is_file() and item.name == "participants.tsv"
        for item in inventory.root_items
    )
    case_variant_names = [
        item.name
        for item in inventory.root_items
        if item.is_file()
        and item.name.casefold() == "participants.tsv"
        and item.name != "participants.tsv"
    ]
    return exact_table_exists, case_variant_names


def mids_501_conflicting_participants_table_filenames(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-501: report exact and case-variant table conflicts."""

    exact_table_exists, case_variant_names = _participants_table_names(
        inventory
    )
    if not exact_table_exists or not case_variant_names:
        return []

    return [
        finding_for_rule(
            "MIDS-501",
            message=(
                "Dataset contains the correctly named participants.tsv "
                "and case-variant file(s): "
                + ", ".join(repr(name) for name in case_variant_names)
                + "."
            ),
            path="participants.tsv",
        )
    ]


def mids_504_missing_participants_table(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-504: require one exactly named ``participants.tsv`` file."""

    exact_table_exists, case_variant_names = _participants_table_names(
        inventory
    )
    if exact_table_exists:
        return []

    message = "Dataset does not contain an exactly named participants.tsv file."
    if case_variant_names:
        names = ", ".join(repr(name) for name in case_variant_names)
        message += f" Found case-variant file(s): {names}; rename exactly."

    return [
        finding_for_rule(
            "MIDS-504",
            message=message,
            path="participants.tsv",
        )
    ]


def _participants_table_findings(
    inventory: DatasetInventory,
    problems: tuple[ParticipantTableProblem, ...],
) -> list[Finding]:
    """Translate shared table-reading problems into MIDS-502 findings."""

    return [
        finding_for_rule(
            "MIDS-502",
            message=problem.message,
            path=inventory.relative_path(problem.path),
        )
        for problem in problems
    ]


def mids_502_invalid_participants_table(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-502: report whether ``participants.tsv`` can be used safely."""

    _, problems = read_participants_table(inventory)
    return _participants_table_findings(inventory, problems)


def mids_503_participant_inventory_mismatch(
    inventory: DatasetInventory,
    participant_table: ParticipantTable,
) -> list[Finding]:
    """MIDS-503: compare valid participant IDs with subject directories."""

    directory_subjects = {
        subject_directory.name
        for subject_directory in inventory.subject_directories()
    }
    missing_from_table = sorted(directory_subjects - participant_table.participant_ids)
    missing_directory = sorted(participant_table.participant_ids - directory_subjects)

    findings: list[Finding] = []
    for subject_id in missing_from_table:
        findings.append(
            finding_for_rule(
                "MIDS-503",
                message=(
                    f"Subject directory {subject_id!r} has no matching "
                    "participant_id row."
                ),
                path=inventory.relative_path(inventory.root / subject_id),
            )
        )

    for participant_id in missing_directory:
        findings.append(
            finding_for_rule(
                "MIDS-503",
                message=(
                    f"participant_id {participant_id!r} has no matching "
                    "subject directory."
                ),
                path=inventory.relative_path(participant_table.path),
            )
        )

    return findings


def mids_505_patient_age_differs_within_session(
    inventory: DatasetInventory,
    patient_metadata: PatientMetadataCollection | None = None,
) -> list[Finding]:
    """MIDS-505: compare patient age strings within each imaging session."""

    collection = patient_metadata or collect_patient_metadata(inventory)
    ages_by_session: dict[tuple[str, str | None], list[str]] = {}
    for observation in collection.observations:
        if observation.age is None:
            continue
        key = (observation.subject_id, observation.session_id)
        ages_by_session.setdefault(key, []).append(observation.age)

    findings: list[Finding] = []
    for (subject_id, session_id), ages in ages_by_session.items():
        if len(set(ages)) < 2:
            continue

        affected_directory = inventory.root / subject_id
        session_description = "the implicit imaging session"
        if session_id is not None:
            affected_directory /= session_id
            session_description = f"session {session_id!r}"
        findings.append(
            finding_for_rule(
                "MIDS-505",
                message=(
                    f"Subject {subject_id!r} has conflicting patient age "
                    f"metadata within {session_description} across "
                    f"{len(ages)} patient sidecars."
                ),
                path=inventory.relative_path(affected_directory),
            )
        )

    return findings


def mids_506_patient_sex_differs_within_subject(
    inventory: DatasetInventory,
    patient_metadata: PatientMetadataCollection | None = None,
) -> list[Finding]:
    """MIDS-506: compare patient sex strings across each subject."""

    collection = patient_metadata or collect_patient_metadata(inventory)
    sex_values_by_subject: dict[str, list[str]] = {}
    for observation in collection.observations:
        if observation.sex is None:
            continue
        sex_values_by_subject.setdefault(observation.subject_id, []).append(
            observation.sex
        )

    findings: list[Finding] = []
    for subject_id, sex_values in sex_values_by_subject.items():
        if len(set(sex_values)) < 2:
            continue
        findings.append(
            finding_for_rule(
                "MIDS-506",
                message=(
                    f"Subject {subject_id!r} has conflicting patient sex "
                    f"metadata across {len(sex_values)} patient sidecars."
                ),
                path=inventory.relative_path(inventory.root / subject_id),
            )
        )

    return findings


def validate_dataset(dataset_path: Path) -> list[Finding]:
    """Run Layer 5 rules with one inventory scan and one table read."""

    inventory = build_inventory(dataset_path)
    return validate_dataset_inventory(inventory)


def validate_dataset_inventory(
    inventory: DatasetInventory,
    patient_metadata: PatientMetadataCollection | None = None,
) -> list[Finding]:
    """Run Layer 5 rules against an inventory supplied by the coordinator."""

    collection = patient_metadata or collect_patient_metadata(inventory)
    findings = mids_501_conflicting_participants_table_filenames(inventory)
    findings.extend(mids_504_missing_participants_table(inventory))
    participant_table, table_problems = read_participants_table(inventory)
    findings.extend(_participants_table_findings(inventory, table_problems))

    if participant_table is not None:
        findings.extend(
            mids_503_participant_inventory_mismatch(inventory, participant_table)
        )

    findings.extend(
        mids_505_patient_age_differs_within_session(inventory, collection)
    )
    findings.extend(
        mids_506_patient_sex_differs_within_subject(inventory, collection)
    )

    return findings
