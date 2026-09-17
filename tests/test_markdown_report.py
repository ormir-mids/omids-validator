"""Tests for the human-readable Markdown report sections."""

import unittest

from mids_validator.models import Finding, Severity, ValidationReport, ValidationRun
from mids_validator.reporters.markdown_report import (
    render_dataset_summary,
    render_findings,
    render_imaging_inventory,
    sort_rule_groups,
)


class MarkdownReportTests(unittest.TestCase):
    def test_dataset_summary_renders_inventory_and_session_counts(self) -> None:
        report = ValidationReport(
            schema_version="1.0",
            validator_version="test",
            dataset_root="/data/study",
            run=ValidationRun("now", False, False),
            findings=(),
            summary={"error": 0, "warning": 0, "info": 0},
            inventory={
                "subject_count": 3,
                "subject_session_unit_count": 5,
                "imaging_session_count": 5,
                "direct_data_subject_count": 1,
                "session_counts": {"ses-01": 2, "ses-02": 2},
                "image_count": 7,
                "images_by_datatype": {"ct": 5, "mr-anat": 2},
            },
        )

        markdown = render_dataset_summary(report)

        self.assertIn("| Subjects | 3 |", markdown)
        self.assertIn("| `ses-01` | 2 |", markdown)
        self.assertIn("| `ses-02` | 2 |", markdown)
        self.assertIn("| `ct` | 5 |", markdown)
        self.assertNotIn("Present in:", markdown)

    def test_imaging_inventory_renders_ranked_coverage_and_units(self) -> None:
        report = ValidationReport(
            schema_version="1.0",
            validator_version="test",
            dataset_root="/data/study",
            run=ValidationRun("now", False, False),
            findings=(),
            summary={"error": 0, "warning": 0, "info": 0},
            inventory={
                "subject_session_unit_count": 2,
                "imaging_session_count": 2,
                "coverage": [
                    {
                        "type": "ct / loc-mcp2_hrpqct",
                        "count": 2,
                        "image_count": 3,
                    }
                ],
                "imaging_units": [
                    {
                        "path": "sub-01/ses-01",
                        "session": "ses-01",
                        "image_count": 2,
                        "coverage_types": ["ct / loc-mcp2_hrpqct"],
                    }
                ],
            },
        )

        markdown = render_imaging_inventory(report)

        self.assertIn("| `ct / loc-mcp2_hrpqct` | 2 / 2 |", markdown)
        self.assertNotIn("| Image count |", markdown)
        self.assertNotIn("## Imaging-unit inventory", markdown)
        self.assertNotIn("| `sub-01/ses-01` | ses-01 | 2 |", markdown)
        self.assertNotIn("Present in:", markdown)

    def test_rule_groups_sort_by_severity_then_numeric_rule_id(self) -> None:
        report = ValidationReport(
            schema_version="1.0",
            validator_version="test",
            dataset_root="/data/study",
            run=ValidationRun("now", False, False),
            findings=(
                Finding("MIDS-101", Severity.WARNING, "Naming", "warning", "b"),
                Finding("MIDS-007", Severity.ERROR, "Structure", "error", "a"),
                Finding("MIDS-002", Severity.ERROR, "Structure", "error", "c"),
                Finding("MIDS-204", Severity.INFO, "Sidecars", "info", "d"),
            ),
            summary={"error": 2, "warning": 1, "info": 1},
            inventory={},
        )

        sorted_groups = sort_rule_groups(
            {
                rule_id: {
                    "severity": severity,
                    "title": title,
                    "findings": [finding],
                }
                for rule_id, severity, title, finding in (
                    ("MIDS-101", Severity.WARNING, "Naming", report.findings[0]),
                    ("MIDS-007", Severity.ERROR, "Structure", report.findings[1]),
                    ("MIDS-002", Severity.ERROR, "Structure", report.findings[2]),
                    ("MIDS-204", Severity.INFO, "Sidecars", report.findings[3]),
                )
            }
        )

        self.assertEqual(
            [rule_id for rule_id, _ in sorted_groups[Severity.ERROR]],
            ["MIDS-002", "MIDS-007"],
        )
        self.assertEqual(
            [rule_id for rule_id, _ in sorted_groups[Severity.WARNING]],
            ["MIDS-101"],
        )

    def test_findings_use_all_paths_for_small_groups_and_one_for_large_groups(
        self,
    ) -> None:
        findings = tuple(
            Finding(
                "MIDS-201",
                Severity.ERROR,
                "Missing sidecar",
                "A JSON sidecar is required.",
                f"sub-{index:03d}/image.nii.gz",
            )
            for index in range(1, 12)
        )
        report = ValidationReport(
            schema_version="1.0",
            validator_version="test",
            dataset_root="/data/study",
            run=ValidationRun("now", False, False),
            findings=findings,
            summary={"error": 11, "warning": 0, "info": 0},
            inventory={},
        )

        markdown = render_findings(report)

        self.assertIn("## Errors", markdown)
        self.assertIn("MIDS-201", markdown)
        self.assertIn("sub-001/image.nii.gz", markdown)
        self.assertNotIn("sub-011/image.nii.gz", markdown)
        self.assertIn("See [report.json](report.json)", markdown)


if __name__ == "__main__":
    unittest.main()
