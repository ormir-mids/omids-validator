"""Tests for the human-readable Markdown report sections."""

import unittest

from omids_validator.models import Finding, Severity, ValidationReport, ValidationRun
from omids_validator.reporters.markdown_report import (
    render,
    render_dataset_summary,
    render_findings,
    render_imaging_inventory,
    render_practical_next_steps,
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

    def test_practical_next_steps_use_catalogue_guidance_in_finding_order(
        self,
    ) -> None:
        report = ValidationReport(
            schema_version="1.0",
            validator_version="test",
            dataset_root="/data/study",
            run=ValidationRun("now", False, False),
            findings=(
                Finding(
                    "MIDS-503",
                    Severity.WARNING,
                    "Participant inventory mismatch",
                    "A subject is absent from the table.",
                    "participants.tsv",
                ),
                Finding(
                    "MIDS-201",
                    Severity.ERROR,
                    "Missing primary JSON sidecar",
                    "A sidecar is missing.",
                    "sub-02/ct/image.nii.gz",
                ),
                Finding(
                    "MIDS-201",
                    Severity.ERROR,
                    "Missing primary JSON sidecar",
                    "Another sidecar is missing.",
                    "sub-01/ct/image.nii.gz",
                ),
                Finding(
                    "MIDS-402",
                    Severity.WARNING,
                    "Acquisition dimension outlier",
                    "Image dimensions differ.",
                    "sub-01/ct/outlier.nii.gz",
                ),
                Finding(
                    "MIDS-204",
                    Severity.INFO,
                    "Optional patient JSON sidecar is absent",
                    "An optional sidecar is absent.",
                    "sub-01/ct/image.nii.gz",
                ),
            ),
            summary={"error": 2, "warning": 2, "info": 1},
            inventory={},
        )

        markdown = render_practical_next_steps(report)

        self.assertIn("## Practical next steps", markdown)
        self.assertLess(
            markdown.index("### Errors"),
            markdown.index("### Warnings"),
        )
        self.assertLess(markdown.index("MIDS-402"), markdown.index("MIDS-503"))
        self.assertEqual(markdown.count("#### MIDS-201"), 1)
        self.assertIn("**Tool:** `dcm2omids`", markdown)
        self.assertIn(
            "**Command:** `omids_validator DATASET --participants`",
            markdown,
        )
        self.assertNotIn("MIDS-204", markdown)
        self.assertNotIn("A sidecar is missing.", markdown)
        self.assertNotIn("sub-02/ct/image.nii.gz", markdown)

    def test_info_only_report_omits_practical_next_steps(self) -> None:
        report = ValidationReport(
            schema_version="1.0",
            validator_version="test",
            dataset_root="/data/study",
            run=ValidationRun("now", False, False),
            findings=(
                Finding(
                    "MIDS-204",
                    Severity.INFO,
                    "Optional patient JSON sidecar is absent",
                    "An optional sidecar is absent.",
                    "sub-01/ct/image.nii.gz",
                ),
            ),
            summary={"error": 0, "warning": 0, "info": 1},
            inventory={},
        )

        self.assertEqual(render_practical_next_steps(report), "")
        self.assertNotIn("## Practical next steps", render(report))


if __name__ == "__main__":
    unittest.main()
