"""Create or populate subject, age, and sex fields in ``participants.tsv``.

The coordinator calls this module only when the user requests ``--participants``.
"""

import csv
import os
import stat
import tempfile
from pathlib import Path

from omids_validator.inventory import DatasetInventory
from omids_validator.patient_metadata import (
    PatientMetadataCollection,
    collect_patient_metadata,
    consistent_sex_for_subject,
    youngest_age_for_subject,
)
from omids_validator.participant_table import read_participants_table


PARTICIPANT_COLUMNS = ("participant_id", "age", "sex", "group")


def _subject_ids(inventory: DatasetInventory) -> list[str]:
    """Return discovered subject directory names in stable order."""

    return sorted(
        subject_directory.name
        for subject_directory in inventory.subject_directories()
    )


def _participant_values(
    patient_metadata: PatientMetadataCollection,
    subject_id: str,
) -> dict[str, str]:
    """Return demographic values safe to place in blank participant cells."""

    values: dict[str, str] = {}
    age = youngest_age_for_subject(patient_metadata, subject_id)
    sex = consistent_sex_for_subject(patient_metadata, subject_id)
    if age is not None:
        values["age"] = age
    if sex is not None:
        values["sex"] = sex
    return values


def _create_table(
    path: Path,
    subject_ids: list[str],
    patient_metadata: PatientMetadataCollection,
) -> int:
    """Create a participant table and return the number of filled cells."""

    # Exclusive creation prevents a case-insensitive filesystem from
    # overwriting a differently cased existing file.
    filled_cells = 0
    with path.open("x", encoding="utf-8", newline="") as table_file:
        writer = csv.writer(table_file, delimiter="\t", lineterminator="\n")
        writer.writerow(PARTICIPANT_COLUMNS)
        for subject_id in subject_ids:
            values = _participant_values(patient_metadata, subject_id)
            filled_cells += len(values)
            writer.writerow(
                (
                    subject_id,
                    values.get("age", ""),
                    values.get("sex", ""),
                    "",
                )
            )
    return filled_cells


def _write_table(path: Path, rows: list[list[str]]) -> None:
    """Replace a participant table after writing a complete temporary file."""

    original_mode = stat.S_IMODE(path.stat().st_mode)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
        text=True,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(
            descriptor,
            "w",
            encoding="utf-8",
            newline="",
        ) as table_file:
            writer = csv.writer(table_file, delimiter="\t", lineterminator="\n")
            writer.writerows(rows)
        temporary_path.chmod(original_mode)
        temporary_path.replace(path)
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def _populate_existing_table(
    path: Path,
    subject_ids: list[str],
    patient_metadata: PatientMetadataCollection,
) -> tuple[list[str], list[str], int]:
    """Add subjects and fill blank demographic cells in a valid table."""

    with path.open(encoding="utf-8", newline="") as table_file:
        rows = list(csv.reader(table_file, delimiter="\t"))

    header_index = next(
        index
        for index, row in enumerate(rows)
        if any(cell.strip() for cell in row)
    )
    header = rows[header_index]
    values_by_subject = {
        subject_id: _participant_values(patient_metadata, subject_id)
        for subject_id in subject_ids
    }
    available_columns = {
        column
        for values in values_by_subject.values()
        for column in values
    }
    added_columns = [
        column
        for column in ("age", "sex")
        if column in available_columns and column not in header
    ]
    header.extend(added_columns)

    for row in rows[header_index + 1 :]:
        if any(cell.strip() for cell in row):
            row.extend([""] * (len(header) - len(row)))

    participant_id_index = header.index("participant_id")
    rows_by_subject = {
        row[participant_id_index]: row
        for row in rows[header_index + 1 :]
        if any(cell.strip() for cell in row)
    }
    missing_subject_ids = sorted(set(subject_ids) - rows_by_subject.keys())
    for subject_id in missing_subject_ids:
        row = [""] * len(header)
        row[participant_id_index] = subject_id
        rows.append(row)
        rows_by_subject[subject_id] = row

    filled_cells = 0
    for subject_id in subject_ids:
        row = rows_by_subject[subject_id]
        for column, value in values_by_subject[subject_id].items():
            column_index = header.index(column)
            if not row[column_index].strip():
                row[column_index] = value
                filled_cells += 1

    changed = bool(added_columns or missing_subject_ids or filled_cells)
    if changed:
        _write_table(path, rows)

    return missing_subject_ids, added_columns, filled_cells


def create_or_populate_participants(
    inventory: DatasetInventory,
    patient_metadata: PatientMetadataCollection | None = None,
) -> dict[str, object]:
    """Create or safely populate the root-level participant table.

    Invalid tables are left untouched. A case-variant filename does not block
    creation of the correctly named file on a case-sensitive filesystem.
    """

    collection = patient_metadata or collect_patient_metadata(inventory)
    table_path = inventory.root / "participants.tsv"
    subject_ids = _subject_ids(inventory)
    exact_exists = any(
        item.is_file() and item.name == "participants.tsv"
        for item in inventory.root_items
    )

    if not exact_exists:
        case_variants = [
            item.name
            for item in inventory.root_items
            if item.is_file() and item.name.casefold() == "participants.tsv"
        ]
        try:
            filled_cells = _create_table(table_path, subject_ids, collection)
        except FileExistsError:
            # macOS commonly uses a case-insensitive filesystem, where the
            # requested exact name aliases the case-variant path.
            return {
                "operation": "skipped",
                "path": "participants.tsv",
                "reason": (
                    "could not create exact participants.tsv because the "
                    f"case-variant file {case_variants[0]!r} already exists"
                ),
            }
        return {
            "operation": "created",
            "path": "participants.tsv",
            "columns": list(PARTICIPANT_COLUMNS),
            "added_participant_ids": subject_ids,
            "filled_demographic_cells": filled_cells,
        }

    table, problems = read_participants_table(inventory)
    if problems or table is None:
        return {
            "operation": "skipped",
            "path": "participants.tsv",
            "reason": "existing participants.tsv is malformed",
        }

    missing_subject_ids, added_columns, filled_cells = _populate_existing_table(
        table.path,
        subject_ids,
        collection,
    )
    changed = bool(missing_subject_ids or added_columns or filled_cells)

    return {
        "operation": "populated" if changed else "unchanged",
        "path": "participants.tsv",
        "added_participant_ids": missing_subject_ids,
        "added_columns": added_columns,
        "filled_demographic_cells": filled_cells,
    }
