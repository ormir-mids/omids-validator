"""Tests for JSON report serialization and CLI output handling."""

import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from mids_validator.cli import main
from mids_validator.models import Finding, Severity, ValidationReport, ValidationRun
from mids_validator.reporters.json_report import as_dict


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
            [item["message"] for item in payload["findings_by_rule"]["MIDS-201"]["findings"]],
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
