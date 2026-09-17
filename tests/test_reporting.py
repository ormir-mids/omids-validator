"""Tests for JSON report serialization and CLI output handling."""

import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path

from mids_validator.cli import RULES_DOCUMENT_NAME, main
from mids_validator.models import Finding, Severity, ValidationReport, ValidationRun
from mids_validator.reporters.json_report import as_dict
from mids_validator.rules_document import render_rules_markdown


class ReportingTests(unittest.TestCase):
    def test_json_groups_findings_and_preserves_message_variants(self) -> None:
        report = ValidationReport(
            schema_version="1.0",
            validator_version="test",
            dataset_root="/data/study",
            run=ValidationRun("now", False, False),
            findings=(
                Finding(
                    "MIDS-201",
                    Severity.ERROR,
                    "Missing primary JSON sidecar",
                    "Missing sidecar",
                    "sub-01/image.nii.gz",
                ),
                Finding(
                    "MIDS-201",
                    Severity.ERROR,
                    "Missing primary JSON sidecar",
                    "Another missing sidecar",
                    "sub-02/image.nii.gz",
                ),
            ),
            summary={"error": 2, "warning": 0, "info": 0},
            inventory={},
        )

        payload = as_dict(report)

        self.assertEqual(payload["findings_by_rule"]["MIDS-201"]["count"], 2)
        self.assertEqual(
            payload["findings_by_rule"]["MIDS-201"]["paths"],
            ["sub-01/image.nii.gz", "sub-02/image.nii.gz"],
        )
        self.assertEqual(
            [
                item["message"]
                for item in payload["findings_by_rule"]["MIDS-201"]["findings"]
            ],
            ["Missing sidecar", "Another missing sidecar"],
        )
        self.assertNotIn("/data/study/sub-01/image.nii.gz", json.dumps(payload))

    def test_cli_writes_report_under_output_directory(self) -> None:
        dataset = Path(__file__).parents[1] / "sample_data" / "mids"
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "test_reports"
            stdout = StringIO()
            with redirect_stdout(stdout):
                result = main([str(dataset), "-o", str(output)])

            self.assertEqual(result, 0)
            report_directories = sorted(output.glob("mids_reports_*"))
            self.assertEqual(len(report_directories), 1)
            report_path = report_directories[0] / "report.json"
            self.assertTrue(report_path.is_file())
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["schema_version"], "1.0")
            self.assertIn("JSON report:", stdout.getvalue())

    def test_rules_mode_writes_named_document_and_prints_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "documentation"
            expected_path = (output / RULES_DOCUMENT_NAME).resolve()
            stdout = StringIO()

            with redirect_stdout(stdout):
                result = main(["--rules", "-o", str(output)])

            self.assertEqual(result, 0)
            self.assertEqual(
                expected_path.read_text(encoding="utf-8"),
                render_rules_markdown(),
            )
            self.assertEqual(
                stdout.getvalue(),
                f"Rules document: {expected_path}\n",
            )
            self.assertEqual(list(output.glob("mids_reports_*")), [])

    def test_rules_mode_replaces_existing_generated_document(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory)
            rules_path = output / RULES_DOCUMENT_NAME
            rules_path.write_text("stale content", encoding="utf-8")

            with redirect_stdout(StringIO()):
                result = main(["--rules", "-o", str(output)])

            self.assertEqual(result, 0)
            self.assertEqual(
                rules_path.read_text(encoding="utf-8"),
                render_rules_markdown(),
            )

    def test_rules_mode_rejects_dataset_and_validation_options(self) -> None:
        invalid_arguments = (
            ["dataset", "--rules"],
            ["--rules", "--participants"],
            ["--rules", "--inspect-images"],
        )

        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with redirect_stderr(StringIO()):
                    with self.assertRaises(SystemExit) as context:
                        main(arguments)

                self.assertEqual(context.exception.code, 2)

    def test_cli_requires_dataset_outside_rules_mode(self) -> None:
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as context:
                main([])

        self.assertEqual(context.exception.code, 2)

    def test_rules_mode_returns_setup_error_when_output_is_not_a_directory(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "not-a-directory"
            output.write_text("occupied", encoding="utf-8")
            stdout = StringIO()

            with redirect_stdout(stdout):
                result = main(["--rules", "-o", str(output)])

            self.assertEqual(result, 2)
            self.assertIn("unable to write rules document", stdout.getvalue())
