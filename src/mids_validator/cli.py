"""Command-line entry point for the validation coordinator."""

import argparse
from datetime import datetime
from pathlib import Path

from mids_validator.reporters import json_report, terminal
from mids_validator.rules_document import write_rules_markdown
from mids_validator.validator import validate


VALIDATION_ERROR = 1
SETUP_ERROR = 2
RULES_DOCUMENT_NAME = "MIDS_validator_rules.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a MIDS dataset or generate the rule catalogue."
    )
    parser.add_argument(
        "dataset",
        nargs="?",
        type=Path,
        help="dataset directory; omit when using --rules",
    )
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
        help=(
            "output directory; validation creates a timestamped child "
            "directory"
        ),
    )
    parser.add_argument(
        "--rules",
        action="store_true",
        help="write MIDS_validator_rules.md and exit without validating a dataset",
    )
    return parser


def _validate_arguments(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    """Require exactly one CLI mode and reject incompatible options."""

    if args.rules:
        incompatible: list[str] = []
        if args.dataset is not None:
            incompatible.append("DATASET")
        if args.participants:
            incompatible.append("--participants")
        if args.inspect_images:
            incompatible.append("--inspect-images")
        if incompatible:
            parser.error(
                "--rules cannot be combined with " + ", ".join(incompatible)
            )
        return

    if args.dataset is None:
        parser.error("DATASET is required unless --rules is supplied")


def _write_rules_document(output_directory: Path) -> Path:
    """Write the generated rules document and return its absolute path."""

    resolved_output = output_directory.expanduser().resolve()
    resolved_output.mkdir(parents=True, exist_ok=True)
    rules_path = resolved_output / RULES_DOCUMENT_NAME
    write_rules_markdown(rules_path)
    return rules_path


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
    """Run dataset validation or generate the rule catalogue document."""

    parser = build_parser()
    args = parser.parse_args(argv)
    _validate_arguments(parser, args)

    if args.rules:
        try:
            rules_path = _write_rules_document(args.output_dir)
        except (OSError, ValueError) as error:
            print(f"mids-validator: unable to write rules document: {error}")
            return SETUP_ERROR

        print(f"Rules document: {rules_path}")
        return 0

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
