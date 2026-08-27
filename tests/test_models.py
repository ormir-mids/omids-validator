"""Tests for shared finding and report data structures."""

import unittest

from mids_validator.models import Finding, Severity


class FindingTests(unittest.TestCase):
    def test_severity_values_are_json_friendly_strings(self) -> None:
        self.assertEqual(Severity.ERROR.value, "error")
        self.assertEqual(Severity.WARNING.value, "warning")
        self.assertEqual(Severity.INFO.value, "info")

    def test_finding_stores_the_standard_fields(self) -> None:
        finding = Finding(
            rule_id="MIDS-009",
            severity=Severity.WARNING,
            title="Operating-system artifact present",
            message="Remove the file before sharing data.",
            path=".DS_Store",
        )

        self.assertEqual(finding.rule_id, "MIDS-009")
        self.assertEqual(finding.path, ".DS_Store")


if __name__ == "__main__":
    unittest.main()
