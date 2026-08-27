"""
validator.py

Validates MIDS dataset, identifies non-compliance, updates participants.tsv, creates human readable data report

Usage:
    python validator.py <mids_directory>

Created by: S.D. McGarry 07/10/2026
Last modified: 07/10/2026
"""
import argparse
import sys
from pathlib import Path
import csv
import re

VALID_DATATYPE_DIRECTORIES = {
    "mr-anat",
    "mr-quant",
    "ct",
    "rx",
}

VALID_IMAGE_EXTENSIONS = {
    ".nii",
    ".nii.gz"
}

def validate_inputs(mids_directory: str) -> Path:
    path = Path(mids_directory)

    if not path.exists():
        sys.exit(f"ERROR: MIDS directory does not exist:\n{path}")

    if not path.is_dir():
        sys.exit(f"ERROR: MIDS path is not a directory:\n{path}")

    return path

def print_findings(findings: list[dict[str, str]]) -> None:
    """
    Print findings in a human-readable format.
    """
    if not findings:
        return

    for finding in findings:
        rule_id = finding.get("rule_id", "Unknown Rule")
        path = finding.get("path", "Unknown Path")
        message = finding.get(
            "message",
            "No additional information provided.",
        )
        print(f"Finding: {rule_id} - {message} at {path}")

def create_participants_tsv_if_missing(mids_directory: Path) -> bool:
    """
    Create participants.tsv with a participant_id header if it does not exist.

    Returns True if the file was created, otherwise False.
    """
    participants_tsv = mids_directory / "participants.tsv"

    if participants_tsv.exists():
        return False

    participants_tsv.write_text(
        "participant_id\tage\tsex\n",
        encoding="utf-8",
    )

    return True

def get_data_containers(subject_directory: Path) -> list[Path]:
    """
    Return directories expected to contain datatype folders.

    If any directories begin with 'ses-', the subject is treated as
    session-based. Session naming validity is handled by MIDS-003.
    Otherwise, the subject directory itself is returned.
    """
    session_directories = sorted(
        item
        for item in subject_directory.iterdir()
        if item.is_dir() and item.name.startswith("ses-")
    )

    if session_directories:
        return session_directories

    return [subject_directory]

def mids_001_validate_root_structure(
    mids_directory: Path,
) -> list[dict[str, str]]:
    """
    MIDS-001: The MIDS directory may contain only subject directories
    and participants.tsv.

    Returns findings for unexpected files or directories.
    """
    findings = []

    for item in mids_directory.iterdir():
        is_subject_directory = (
            item.is_dir() and item.name.startswith("sub-")
        )
        is_participants_file = (
            item.is_file() and item.name == "participants.tsv"
        )

        if not is_subject_directory and not is_participants_file:
            findings.append(
                {
                    "rule_id": "MIDS-001",
                    "path": str(item),
                }
            )

    return findings

def populate_participants_tsv(mids_directory: Path) -> list[str]:
    """
    Add participant IDs found in subject directories to participants.tsv.

    Existing rows, columns, and values are preserved.

    Returns a list of participant IDs added to the table.
    """
    participants_tsv = mids_directory / "participants.tsv"

    subject_ids = sorted(
        item.name
        for item in mids_directory.iterdir()
        if item.is_dir() and item.name.startswith("sub-")
    )

    with participants_tsv.open(
        "r",
        newline="",
        encoding="utf-8",
    ) as file:
        reader = csv.DictReader(file, delimiter="\t")

        if reader.fieldnames is None:
            raise ValueError(
                "participants.tsv does not contain a header row."
            )

        if "participant_id" not in reader.fieldnames:
            raise ValueError(
                "participants.tsv is missing the required "
                "'participant_id' column."
            )

        fieldnames = reader.fieldnames
        rows = list(reader)

    existing_ids = {
        row["participant_id"]
        for row in rows
        if row.get("participant_id")
    }

    added_ids = []

    for subject_id in subject_ids:
        if subject_id not in existing_ids:
            new_row = {field: "" for field in fieldnames}
            new_row["participant_id"] = subject_id
            rows.append(new_row)
            added_ids.append(subject_id)

    if added_ids:
        with participants_tsv.open(
            "w",
            newline="",
            encoding="utf-8",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
                delimiter="\t",
                lineterminator="\n",
            )
            writer.writeheader()
            writer.writerows(rows)

    return added_ids

def mids_002_subj_ids(mids_directory: Path,) -> list[dict[str, str]]:
    """
    MIDS-002: Subject directory names must follow the pattern
    sub-<alphanumeric>.
    """
    findings = []

    subject_directories = [
        item
        for item in mids_directory.iterdir()
        if item.is_dir() and item.name.startswith("sub-")
    ]

    for subject_directory in subject_directories:
        if not re.fullmatch(
            r"sub-[A-Za-z0-9]+",
            subject_directory.name,
        ):
            findings.append(
                {
                    "rule_id": "MIDS-002",
                    "path": str(subject_directory),
                    "message": (
                        "Subject ID does not follow the required "
                        "'sub-<alphanumeric>' pattern."
                    ),
                }
            )

    return findings

def mids_003_subject_session_structure(
    mids_directory: Path,
) -> list[dict[str, str]]:
    """
    MIDS-003: A subject directory must use either session directories
    or datatype directories directly, but not both.

    If session directories are present, all items in the subject
    directory must be valid session directories.
    """
    findings = []

    subject_directories = [
        item
        for item in mids_directory.iterdir()
        if item.is_dir() and re.fullmatch(r"sub-[A-Za-z0-9]+", item.name)
    ]

    for subject_directory in subject_directories:
        items = list(subject_directory.iterdir())

        session_directories = [
            item
            for item in items
            if item.is_dir() and item.name.startswith("ses-")
        ]

        if not session_directories:
            continue

        for item in items:
            is_valid_session_directory = (
                item.is_dir()
                and re.fullmatch(r"ses-[A-Za-z0-9]+", item.name)
            )

            if not is_valid_session_directory:
                findings.append(
                    {
                        "rule_id": "MIDS-003",
                        "path": str(item),
                        "message": (
                            "Subject uses session directories, so all items "
                            "inside the subject directory must be valid "
                            "'ses-<alphanumeric>' directories."
                        ),
                    }
                )

    return findings

def mids_004_datatype_directories(
    mids_directory: Path,
) -> list[dict[str, str]]:
    """
    MIDS-004: Subject data must be stored only in recognized datatype
    directories.

    Datatype directories may appear directly inside a subject directory
    or inside session directories.
    """
    findings = []

    subject_directories = [
        item
        for item in mids_directory.iterdir()
        if item.is_dir() and re.fullmatch(r"sub-[A-Za-z0-9]+", item.name)
    ]

    for subject_directory in subject_directories:
        containers = get_data_containers(subject_directory)

        for container in containers:
            for item in container.iterdir():
                if not item.is_dir():
                    findings.append(
                        {
                            "rule_id": "MIDS-004",
                            "path": str(item),
                            "message": (
                                "Only recognized datatype directories are "
                                "permitted at this level."
                            ),
                        }
                    )
                    continue

                if item.name not in VALID_DATATYPE_DIRECTORIES:
                    findings.append(
                        {
                            "rule_id": "MIDS-004",
                            "path": str(item),
                            "message": (
                                f"Unrecognized datatype directory "
                                f"'{item.name}'."
                            ),
                        }
                    )

    return findings

def mids_005_allowed_file_types(datatype_directory: Path) -> list[dict[str, str]]:
    """
    MIDS-005: Datatype directories may contain only recognized image files and metadata files.
    """

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a MIDS dataset."
    )
    parser.add_argument(
        "mids_directory",
        type=str,
        help="Path to the MIDS dataset directory.",
    )

    args = parser.parse_args()
    mids_directory = validate_inputs(args.mids_directory)

    participants_created = create_participants_tsv_if_missing(
        mids_directory
    )

    if participants_created:
        print("Created participants.tsv")

    try:
        added_participants = populate_participants_tsv(mids_directory)
    except ValueError as error:
        print(f"ERROR: {error}")
        added_participants = []

    if added_participants:
        print(
            f"Added participant IDs to participants.tsv: {', '.join(added_participants)}"
        )

    findings001 = mids_001_validate_root_structure(mids_directory)
    print_findings(findings001)

    findings002 = mids_002_subj_ids(mids_directory)
    print_findings(findings002)

    findings003 = mids_003_subject_session_structure(mids_directory)
    print_findings(findings003)

    findings004 = mids_004_datatype_directories(mids_directory)
    print_findings(findings004)


if __name__ == "__main__":
    main()
