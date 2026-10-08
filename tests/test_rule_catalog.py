"""Tests for the authoritative machine-readable rule catalogue."""

import json
import unittest

from omids_validator.models import Severity
from omids_validator.rule_catalog import (
    RuleCatalogError,
    finding_for_rule,
    load_rule_catalog,
    parse_rule_catalog,
    validate_rule_catalog,
)


def _catalogue_with(rule: dict[str, object]) -> dict[str, object]:
    """Return the smallest valid catalogue shape around one test rule."""

    return {
        "schema_version": "1.0",
        "rules": {"MIDS-201": rule},
    }


def _valid_rule() -> dict[str, object]:
    return {
        "layer": 2,
        "status": "active",
        "title": "Missing primary JSON sidecar",
        "severity": "error",
        "description": "Every image requires a matching primary sidecar.",
        "next_step": {
            "kind": "tool",
            "tool": "dcm2omids",
            "text": "Reconvert the source DICOM data.",
        },
    }


class RuleCatalogTests(unittest.TestCase):
    def test_packaged_catalogue_contains_all_current_rules(self) -> None:
        catalogue = load_rule_catalog()

        self.assertEqual(catalogue.schema_version, "1.0")
        self.assertEqual(len(catalogue.rules), 32)
        self.assertEqual(catalogue.get("MIDS-201").severity, Severity.ERROR)
        self.assertEqual(catalogue.get("MIDS-201").next_step.tool, "dcm2omids")
        self.assertEqual(catalogue.get("MIDS-203").next_step.tool, "dcm2omids")
        self.assertEqual(catalogue.get("MIDS-302").status, "deferred")

    def test_participant_rules_have_one_fixed_severity_each(self) -> None:
        catalogue = load_rule_catalog()

        conflicting = catalogue.get("MIDS-501")
        absent = catalogue.get("MIDS-504")
        age_within_session = catalogue.get("MIDS-505")
        sex_within_subject = catalogue.get("MIDS-506")

        self.assertEqual(conflicting.severity, Severity.ERROR)
        self.assertEqual(
            conflicting.title,
            "Conflicting participants table filenames",
        )
        self.assertEqual(absent.severity, Severity.WARNING)
        self.assertEqual(absent.title, "Participants table is absent")
        self.assertEqual(
            absent.next_step.command,
            "omids_validator DATASET --participants",
        )
        self.assertEqual(age_within_session.severity, Severity.WARNING)
        self.assertEqual(
            age_within_session.title,
            "Patient age differs within an imaging session",
        )
        self.assertEqual(sex_within_subject.severity, Severity.INFO)
        self.assertEqual(
            sex_within_subject.title,
            "Patient sex differs within a subject",
        )

    def test_unknown_rule_id_has_a_clear_error(self) -> None:
        with self.assertRaisesRegex(
            RuleCatalogError,
            "does not define MIDS-999",
        ):
            load_rule_catalog().get("MIDS-999")

    def test_finding_uses_catalogue_title_and_severity(self) -> None:
        finding = finding_for_rule(
            "MIDS-201",
            message="A sidecar is missing.",
            path="sub-01/ct/image.nii.gz",
        )

        self.assertEqual(finding.rule_id, "MIDS-201")
        self.assertEqual(finding.title, "Missing primary JSON sidecar")
        self.assertEqual(finding.severity, Severity.ERROR)
        self.assertEqual(finding.message, "A sidecar is missing.")
        self.assertEqual(finding.path, "sub-01/ct/image.nii.gz")

    def test_finding_rejects_unknown_rule_id(self) -> None:
        with self.assertRaisesRegex(
            RuleCatalogError,
            "does not define MIDS-999",
        ):
            finding_for_rule("MIDS-999", message="Unknown rule.")

    def test_layer_must_match_rule_id(self) -> None:
        rule = _valid_rule()
        rule["layer"] = 3

        with self.assertRaisesRegex(
            RuleCatalogError,
            "layer must be 2",
        ):
            validate_rule_catalog(_catalogue_with(rule))

    def test_unexpected_rule_field_is_rejected(self) -> None:
        rule = _valid_rule()
        rule["severty"] = rule.pop("severity")

        with self.assertRaisesRegex(
            RuleCatalogError,
            "missing required field.*severity",
        ):
            validate_rule_catalog(_catalogue_with(rule))

    def test_command_guidance_requires_a_command(self) -> None:
        rule = _valid_rule()
        rule["next_step"] = {
            "kind": "command",
            "text": "Run the supported repair command.",
        }

        with self.assertRaisesRegex(
            RuleCatalogError,
            "missing required field.*command",
        ):
            validate_rule_catalog(_catalogue_with(rule))

    def test_duplicate_json_keys_are_rejected(self) -> None:
        rule_text = json.dumps(_valid_rule())
        text = (
            '{"schema_version":"1.0","rules":{'
            f'"MIDS-201":{rule_text},"MIDS-201":{rule_text}'
            "}}"
        )

        with self.assertRaisesRegex(
            RuleCatalogError,
            "repeats JSON key 'MIDS-201'",
        ):
            parse_rule_catalog(text)


if __name__ == "__main__":
    unittest.main()
