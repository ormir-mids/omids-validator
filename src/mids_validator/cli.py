"""Command-line entry point for the validation coordinator."""

import argparse
from datetime import datetime
from pathlib import Path

from mids_validator.reporters import json_report, terminal
from mids_validator.validator import validate


VALIDATION_ERROR = 1
SETUP_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate a MIDS dataset.")
    parser.add_argument("dataset", type=Path, help="dataset directory")
    parser.add_argument(
        "-p",
        "--participants",
        action="store_true",
        help=(
            "create participants.tsv if it does not exist and populate it "
            "with discovered subject IDs"
        ),
    )
    parser.add_argument(
        "-i",
        "--inspect-images",
        action="store_true",
        help="inspect NIfTI headers",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="parent directory for the timestamped JSON report directory",
    )
    return parser


def _create_report_directory(parent: Path) -> Path:
    """Create a timestamped, collision-free report directory."""

    parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    candidate = parent / f"mids_reports_{stamp}"
    suffix = 1
    while True:
        try:
            candidate.mkdir()
            return candidate
        except FileExistsError:
            candidate = parent / f"mids_reports_{stamp}_{suffix:02d}"
            suffix += 1


def main(argv: list[str] | None = None) -> int:
    """Run validation, write the JSON report, and print its location."""

    args = build_parser().parse_args(argv)
    try:
        report = validate(
            args.dataset,
            inspect_images=args.inspect_images,
            participants_requested=args.participants,
        )
        report_directory = _create_report_directory(args.output_dir)
        json_report.write(report, report_directory / "report.json")
    except (OSError, ValueError) as error:
        print(f"mids-validator: unable to write report: {error}")
        return SETUP_ERROR

    print(terminal.render(report, str(report_directory)))
    return VALIDATION_ERROR if report.summary["error"] else 0
