"""Command-line entry point for the validation coordinator."""

import argparse
import json
from pathlib import Path

from mids_validator.validator import validate


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
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run validation and emit the normalized report input as JSON."""

    args = build_parser().parse_args(argv)
    report = validate(
        args.dataset,
        inspect_images=args.inspect_images,
        participants_requested=args.participants,
    )
    print(json.dumps(report.as_dict(), indent=2, sort_keys=True))
    return 1 if report.summary["error"] else 0
