"""Shared presentation data for human-readable validation reports."""

from typing import Any

from omids_validator.models import Severity, ValidationReport


FINDING_EXAMPLE_THRESHOLD = 10
SEVERITY_ORDER = (Severity.ERROR, Severity.WARNING, Severity.INFO)
SEVERITY_HEADINGS = {
    Severity.ERROR: "Errors",
    Severity.WARNING: "Warnings",
    Severity.INFO: "Informational findings",
}
SEVERITY_DESCRIPTIONS = {
    Severity.ERROR: (
        "Convention violations likely to cause downstream pipeline or "
        "interoperability problems. These should be fixed."
    ),
    Severity.WARNING: (
        "Probable problems or important inconsistencies that should be "
        "reviewed."
    ),
    Severity.INFO: "Non-blocking observations recorded by the validator.",
}
ACTIONABLE_SEVERITIES = (Severity.ERROR, Severity.WARNING)


def inventory_value(
    report: ValidationReport,
    key: str,
    default: object,
) -> object:
    """Read one optional inventory fact without hiding its default."""

    return report.inventory.get(key, default)


def rule_number(rule_id: str) -> int:
    """Return the numeric portion of a rule ID for numeric sorting."""

    return int(rule_id.rsplit("-", 1)[1])


def group_findings(report: ValidationReport) -> dict[str, dict[str, Any]]:
    """Group findings by rule for human-readable presentation."""

    groups: dict[str, dict[str, Any]] = {}
    for finding in report.findings:
        group = groups.setdefault(
            finding.rule_id,
            {
                "severity": finding.severity,
                "title": finding.title,
                "findings": [],
            },
        )
        group["findings"].append(finding)

    return groups


def sort_rule_groups(
    groups_by_rule: dict[str, dict[str, Any]],
) -> dict[Severity, list[tuple[str, dict[str, Any]]]]:
    """Sort rule groups by severity, then numeric rule ID."""

    groups_by_severity: dict[Severity, list[tuple[str, dict[str, Any]]]] = {
        severity: [] for severity in SEVERITY_ORDER
    }
    for rule_id, group in groups_by_rule.items():
        groups_by_severity[group["severity"]].append((rule_id, group))

    for severity in SEVERITY_ORDER:
        groups_by_severity[severity].sort(
            key=lambda item: (rule_number(item[0]), item[0])
        )

    return groups_by_severity
