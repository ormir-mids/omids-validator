"""Read and describe the root-level ``participants.tsv`` table."""

import csv
from dataclasses import dataclass
from pathlib import Path

from mids_validator.inventory import DatasetInventory


@dataclass(frozen=True)
class ParticipantTable:
    """Validated participant identifiers read from ``participants.tsv``."""

    path: Path
    participant_ids: frozenset[str]


@dataclass(frozen=True)
class ParticipantTableProblem:
    """One structural or readability problem found in ``participants.tsv``."""

    path: Path
    message: str


def read_participants_table(
    inventory: DatasetInventory,
) -> tuple[ParticipantTable | None, tuple[ParticipantTableProblem, ...]]:
    """Read one valid participant table or describe why it cannot be used."""

    table_path = next(
        (
            item
            for item in inventory.root_items
            if item.is_file() and item.name == "participants.tsv"
        ),
        None,
    )
    if table_path is None:
        return None, ()

    try:
        with table_path.open(encoding="utf-8", newline="") as table_file:
            rows = list(csv.reader(table_file, delimiter="\t"))
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        return None, (
            ParticipantTableProblem(
                path=table_path,
                message=(
                    "participants.tsv could not be read as UTF-8 TSV: "
                    f"{error}."
                ),
            ),
        )

    nonempty_rows = [
        (line_number, row)
        for line_number, row in enumerate(rows, start=1)
        if any(cell.strip() for cell in row)
    ]
    if not nonempty_rows:
        return None, (
            ParticipantTableProblem(
                path=table_path,
                message="participants.tsv is empty and has no header row.",
            ),
        )

    _, header = nonempty_rows[0]
    participant_id_count = header.count("participant_id")
    if participant_id_count != 1:
        return None, (
            ParticipantTableProblem(
                path=table_path,
                message=(
                    "Header row must contain exactly one participant_id column; "
                    f"found {participant_id_count}."
                ),
            ),
        )

    participant_id_index = header.index("participant_id")
    problems: list[ParticipantTableProblem] = []
    participant_ids: set[str] = set()
    for line_number, row in nonempty_rows[1:]:
        if len(row) != len(header):
            problems.append(
                ParticipantTableProblem(
                    path=table_path,
                    message=(
                        f"Row {line_number} has {len(row)} field(s), but the "
                        f"header has {len(header)}."
                    ),
                )
            )
            continue

        participant_id = row[participant_id_index]
        if not participant_id.strip():
            problems.append(
                ParticipantTableProblem(
                    path=table_path,
                    message=f"Row {line_number} has an empty participant_id.",
                )
            )
        elif participant_id in participant_ids:
            problems.append(
                ParticipantTableProblem(
                    path=table_path,
                    message=(
                        f"Row {line_number} duplicates participant_id "
                        f"{participant_id!r}."
                    ),
                )
            )
        else:
            participant_ids.add(participant_id)

    if problems:
        return None, tuple(problems)

    return (
        ParticipantTable(
            path=table_path,
            participant_ids=frozenset(participant_ids),
        ),
        (),
    )
