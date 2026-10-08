"""Tests for the self-contained HTML validation report."""

import unittest

from omids_validator.models import Finding, Severity, ValidationReport, ValidationRun
from omids_validator.reporters.html_report import render


def make_report(
    *,
    findings: tuple[Finding, ...] = (),
    summary: dict[str, int] | None = None,
    inventory: dict[str, object] | None = None,
) -> ValidationReport:
    """Build one compact report fixture."""

    return ValidationReport(
        schema_version="1.0",
        validator_version="test",
        dataset_root="/data/study",
        run=ValidationRun("now", False, False),
        findings=findings,
        summary=summary or {"error": 0, "warning": 0, "info": 0},
        inventory=inventory or {},
    )


class HtmlReportTests(unittest.TestCase):
    def test_render_produces_standalone_styled_document(self) -> None:
        html = render(make_report())

        self.assertTrue(html.startswith("<!doctype html>"))
        self.assertIn('<html lang="en">', html)
        self.assertIn("<style>", html)
        self.assertIn("No findings", html)
        self.assertIn('href="report.json"', html)
        self.assertNotIn("<script", html)
        self.assertNotIn("<link", html)

    def test_report_escapes_inventory_and_finding_text(self) -> None:
        dangerous = '<script>alert("x")</script> & data'
        report = make_report(
            findings=(
                Finding(
                    "MIDS-204",
                    Severity.INFO,
                    dangerous,
                    dangerous,
                    f"sub-01/{dangerous}.nii.gz",
                ),
            ),
            summary={"error": 0, "warning": 0, "info": 1},
            inventory={
                "subject_count": 1,
                "imaging_session_count": 1,
                "image_count": 1,
                "session_counts": {dangerous: 1},
                "images_by_datatype": {dangerous: 1},
                "coverage": [{"type": dangerous, "count": 1}],
            },
        )

        html = render(report)

        self.assertNotIn(dangerous, html)
        self.assertNotIn('<script>alert("x")</script>', html)
        self.assertIn("&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;", html)
        self.assertIn("&amp; data", html)

    def test_findings_follow_severity_and_numeric_rule_order(self) -> None:
        report = make_report(
            findings=(
                Finding("MIDS-101", Severity.WARNING, "Naming", "warning", "b"),
                Finding("MIDS-007", Severity.ERROR, "Structure", "error", "a"),
                Finding("MIDS-002", Severity.ERROR, "Structure", "error", "c"),
                Finding("MIDS-204", Severity.INFO, "Sidecars", "info", "d"),
            ),
            summary={"error": 2, "warning": 1, "info": 1},
        )

        html = render(report)

        self.assertLess(html.index("Errors"), html.index("Warnings"))
        self.assertLess(html.index("Warnings"), html.index("Informational findings"))
        self.assertLess(html.index("MIDS-002"), html.index("MIDS-007"))
        self.assertEqual(html.count("MIDS-002"), 2)

    def test_large_finding_group_uses_one_example_and_json_link(self) -> None:
        findings = tuple(
            Finding(
                "MIDS-204",
                Severity.INFO,
                "Optional sidecar is absent",
                "An optional sidecar is absent.",
                f"sub-{index:03d}/image.nii.gz",
            )
            for index in range(1, 12)
        )
        html = render(
            make_report(
                findings=findings,
                summary={"error": 0, "warning": 0, "info": 11},
            )
        )

        self.assertIn("sub-001/image.nii.gz", html)
        self.assertNotIn("sub-011/image.nii.gz", html)
        self.assertIn("complete list", html)
        self.assertIn('href="report.json"', html)

    def test_practical_next_steps_include_actionable_rules_once(self) -> None:
        report = make_report(
            findings=(
                Finding(
                    "MIDS-201",
                    Severity.ERROR,
                    "Missing primary JSON sidecar",
                    "Missing sidecar.",
                    "sub-01/ct/image.nii.gz",
                ),
                Finding(
                    "MIDS-201",
                    Severity.ERROR,
                    "Missing primary JSON sidecar",
                    "Another missing sidecar.",
                    "sub-02/ct/image.nii.gz",
                ),
                Finding(
                    "MIDS-204",
                    Severity.INFO,
                    "Optional patient JSON sidecar is absent",
                    "Optional sidecar is absent.",
                    "sub-01/ct/image.nii.gz",
                ),
            ),
            summary={"error": 2, "warning": 0, "info": 1},
        )

        html = render(report)
        next_steps = html[html.index("Practical next steps") :]

        self.assertEqual(next_steps.count("MIDS-201"), 1)
        self.assertNotIn("MIDS-204", next_steps)
        self.assertIn("dcm2omids", next_steps)


if __name__ == "__main__":
    unittest.main()
