"""Read, validate, create, and safely populate ``participants.tsv``."""

import csv
from pathlib import Path

from mids_validator.inventory import DatasetInventory
from mids_validator.participant_table import read_participants_table


# These are the columns in the supplied BIDS study example. Only the first
# column can be populated from a MIDS directory inventory.
PARTICIPANT_COLUMNS = ("participant_id", "age", "sex", "group")


def _subject_ids(inventory: DatasetInventory) -> list[str]:
    """Return discovered subject directory names in stable order."""

    return sorted(
        subject_directory.name
        for subject_directory in inventory.subject_directories()
    )


def _create_table(path: Path, subject_ids: list[str]) -> None:
    """Create a new table with the example headers and blank attributes."""

    # Exclusive creation prevents a case-insensitive filesystem from
    # overwriting a differently cased existing file.
    with path.open("x", encoding="utf-8", newline="") as table_file:
        writer = csv.writer(table_file, delimiter="\t", lineterminator="\n")
        writer.writerow(PARTICIPANT_COLUMNS)
        for subject_id in subject_ids:
            writer.writerow((subject_id, "", "", ""))


def _append_subjects(path: Path, header: list[str], subject_ids: list[str]) -> None:
    """Append missing IDs while preserving the existing table structure."""

    content = path.read_bytes()
    missing_newline = bool(content) and not content.endswith((b"\n", b"\r"))
    with path.open("a", encoding="utf-8", newline="") as table_file:
        if missing_newline:
            table_file.write("\n")
        writer = csv.writer(table_file, delimiter="\t", lineterminator="\n")
        participant_id_index = header.index("participant_id")
        for subject_id in subject_ids:
            row = [""] * len(header)
            row[participant_id_index] = subject_id
            writer.writerow(row)


def create_or_populate_participants(inventory: DatasetInventory) -> dict[str, object]:
    """Create or safely populate the root-level participant table.

    Invalid tables are left untouched. A case-variant filename does not block
    creation of the correctly named file on a case-sensitive filesystem.
    """

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
            _create_table(table_path, subject_ids)
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
        }

    table, problems = read_participants_table(inventory)
    if problems or table is None:
        return {
            "operation": "skipped",
            "path": "participants.tsv",
            "reason": "existing participants.tsv is malformed",
        }

    missing_subject_ids = sorted(set(subject_ids) - table.participant_ids)
    if missing_subject_ids:
        with table.path.open(encoding="utf-8", newline="") as table_file:
            header = next(csv.reader(table_file, delimiter="\t"))
        _append_subjects(table.path, header, missing_subject_ids)

    return {
        "operation": "populated" if missing_subject_ids else "unchanged",
        "path": "participants.tsv",
        "added_participant_ids": missing_subject_ids,
    }
