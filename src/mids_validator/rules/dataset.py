"""Layer 5 rules: participants and dataset-wide consistency.

This layer will compare the complete subject inventory with
``participants.tsv`` and apply other checks requiring a dataset-wide view.
"""

import csv
from dataclasses import dataclass
from pathlib import Path

from mids_validator.inventory import DatasetInventory, build_inventory
from mids_validator.models import Finding, Severity


@dataclass(frozen=True)
class ParticipantTable:
    """Validated participant identifiers read from ``participants.tsv``."""

    path: Path
    participant_ids: frozenset[str]


def mids_501_missing_participants_table(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-501: require an exactly named ``participants.tsv`` file."""

    exact_table_exists = any(
        item.is_file() and item.name == "participants.tsv"
        for item in inventory.root_items
    )
    if exact_table_exists:
        return []

    case_variant_names = [
        item.name
        for item in inventory.root_items
        if item.is_file() and item.name.casefold() == "participants.tsv"
    ]
    message = "Dataset does not contain an exactly named participants.tsv file."
    if case_variant_names:
        names = ", ".join(repr(name) for name in case_variant_names)
        message += f" Found case-variant file(s): {names}; rename exactly."

    return [
        Finding(
            rule_id="MIDS-501",
            severity=Severity.WARNING,
            title="Participants table is absent",
            message=message,
            path="participants.tsv",
        )
    ]


def _parse_participants_table(
    inventory: DatasetInventory,
) -> tuple[ParticipantTable | None, list[Finding]]:
    """Read one valid participant table or return its MIDS-502 findings."""

    table_path = next(
        (
            item
            for item in inventory.root_items
            if item.is_file() and item.name == "participants.tsv"
        ),
        None,
    )
    if table_path is None:
        return None, []

    try:
        with table_path.open(encoding="utf-8", newline="") as table_file:
            rows = list(csv.reader(table_file, delimiter="\t"))
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        return None, [
            Finding(
                rule_id="MIDS-502",
                severity=Severity.ERROR,
                title="Participants table is invalid",
                message=f"participants.tsv could not be read as UTF-8 TSV: {error}.",
                path=inventory.relative_path(table_path),
            )
        ]

    nonempty_rows = [
        (line_number, row)
        for line_number, row in enumerate(rows, start=1)
        if any(cell.strip() for cell in row)
    ]
    if not nonempty_rows:
        return None, [
            Finding(
                rule_id="MIDS-502",
                severity=Severity.ERROR,
                title="Participants table is invalid",
                message="participants.tsv is empty and has no header row.",
                path=inventory.relative_path(table_path),
            )
        ]

    _, header = nonempty_rows[0]
    participant_id_count = header.count("participant_id")
    if participant_id_count != 1:
        return None, [
            Finding(
                rule_id="MIDS-502",
                severity=Severity.ERROR,
                title="Participants table is invalid",
                message=(
                    "Header row must contain exactly one participant_id column; "
                    f"found {participant_id_count}."
                ),
                path=inventory.relative_path(table_path),
            )
        ]

    participant_id_index = header.index("participant_id")
    findings: list[Finding] = []
    participant_ids: set[str] = set()
    for line_number, row in nonempty_rows[1:]:
        if len(row) != len(header):
            findings.append(
                Finding(
                    rule_id="MIDS-502",
                    severity=Severity.ERROR,
                    title="Participants table is invalid",
                    message=(
                        f"Row {line_number} has {len(row)} field(s), but the "
                        f"header has {len(header)}."
                    ),
                    path=inventory.relative_path(table_path),
                )
            )
            continue

        participant_id = row[participant_id_index]
        if not participant_id.strip():
            findings.append(
                Finding(
                    rule_id="MIDS-502",
                    severity=Severity.ERROR,
                    title="Participants table is invalid",
                    message=f"Row {line_number} has an empty participant_id.",
                    path=inventory.relative_path(table_path),
                )
            )
        elif participant_id in participant_ids:
            findings.append(
                Finding(
                    rule_id="MIDS-502",
                    severity=Severity.ERROR,
                    title="Participants table is invalid",
                    message=(
                        f"Row {line_number} duplicates participant_id "
                        f"{participant_id!r}."
                    ),
                    path=inventory.relative_path(table_path),
                )
            )
        else:
            participant_ids.add(participant_id)

    if findings:
        return None, findings

    return (
        ParticipantTable(
            path=table_path,
            participant_ids=frozenset(participant_ids),
        ),
        [],
    )


def mids_502_invalid_participants_table(
    inventory: DatasetInventory,
) -> list[Finding]:
    """MIDS-502: report whether ``participants.tsv`` can be used safely."""

    _, findings = _parse_participants_table(inventory)
    return findings


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
            Finding(
                rule_id="MIDS-503",
                severity=Severity.WARNING,
                title="Participant inventory mismatch",
                message=(
                    f"Subject directory {subject_id!r} has no matching "
                    "participant_id row."
                ),
                path=inventory.relative_path(inventory.root / subject_id),
            )
        )

    for participant_id in missing_directory:
        findings.append(
            Finding(
                rule_id="MIDS-503",
                severity=Severity.WARNING,
                title="Participant inventory mismatch",
                message=(
                    f"participant_id {participant_id!r} has no matching "
                    "subject directory."
                ),
                path=inventory.relative_path(participant_table.path),
            )
        )

    return findings


def validate_dataset(dataset_path: Path) -> list[Finding]:
    """Run Layer 5 rules with one inventory scan and one table read."""

    inventory = build_inventory(dataset_path)
    findings = mids_501_missing_participants_table(inventory)
    participant_table, table_findings = _parse_participants_table(inventory)
    findings.extend(table_findings)

    if participant_table is not None:
        findings.extend(
            mids_503_participant_inventory_mismatch(inventory, participant_table)
        )

    return findings
