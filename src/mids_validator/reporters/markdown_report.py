"""Render the human-readable Markdown validation report.

The report is assembled from small section renderers.  Each renderer receives
the completed :class:`ValidationReport` and returns Markdown text; it does not
run validation or inspect the dataset again.
"""

from pathlib import Path
from typing import Any

from mids_validator.models import Finding, Severity, ValidationReport


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


def _inventory_value(report: ValidationReport, key: str, default: object) -> object:
    """Read one optional inventory fact without hiding its default."""

    return report.inventory.get(key, default)


def _rule_number(rule_id: str) -> int:
    """Return the numeric portion of a rule ID for numeric sorting."""

    return int(rule_id.rsplit("-", 1)[1])


def _group_findings(report: ValidationReport) -> dict[str, dict[str, Any]]:
    """Group findings by rule in the same shape used by the JSON reporter."""

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
    """Sort rule groups by severity, then numeric rule ID.

    Lists are used for the ordered result because ordering is presentation
    logic, not part of the JSON data model.
    """

    groups_by_severity: dict[Severity, list[tuple[str, dict[str, Any]]]] = {
        severity: [] for severity in SEVERITY_ORDER
    }
    for rule_id, group in groups_by_rule.items():
        groups_by_severity[group["severity"]].append((rule_id, group))

    for severity in SEVERITY_ORDER:
        groups_by_severity[severity].sort(
            key=lambda item: (_rule_number(item[0]), item[0])
        )

    return groups_by_severity


def _render_path(finding: Finding) -> str:
    """Render one finding path, or a dataset-level placeholder."""

    return f"`{finding.path}`" if finding.path else "(dataset-level finding)"


def render_rule_group(
    rule_id: str,
    group: dict[str, Any],
    *,
    example_threshold: int = FINDING_EXAMPLE_THRESHOLD,
) -> str:
    """Render one rule group with all or representative paths."""

    findings: list[Finding] = sorted(
        group["findings"],
        key=lambda finding: (finding.path or "", finding.message),
    )
    count = len(findings)
    lines = [
        f"### {rule_id} — {group['title']}",
        "",
        f"{count} finding(s).",
        "",
    ]

    if count <= example_threshold:
        lines.append("Affected paths:")
        lines.extend(
            f"- {_render_path(finding)}"
            + (f" — {finding.message}" if finding.message else "")
            for finding in findings
        )
    else:
        example = findings[0]
        lines.extend(
            [
                "Representative finding:",
                "",
                f"Message: {example.message}",
                "",
                "Representative path:",
                "```text",
                example.path or "(dataset-level finding)",
                "```",
                "",
                "See [report.json](report.json) for the complete list.",
            ]
        )

    return "\n".join(lines)


def render_severity_section(
    severity: Severity,
    groups: list[tuple[str, dict[str, Any]]],
) -> str:
    """Render one severity heading and its ordered rule groups."""

    sections = [
        f"## {SEVERITY_HEADINGS[severity]}",
        SEVERITY_DESCRIPTIONS[severity],
    ]
    sections.extend(
        render_rule_group(rule_id, group) for rule_id, group in groups
    )
    return "\n\n".join(sections)


def render_findings(report: ValidationReport) -> str:
    """Render findings by severity and numeric rule order."""

    sorted_groups = sort_rule_groups(_group_findings(report))
    sections = [
        render_severity_section(severity, sorted_groups[severity])
        for severity in SEVERITY_ORDER
        if sorted_groups[severity]
    ]
    return "\n\n".join(sections)


def render_dataset_summary(report: ValidationReport) -> str:
    """Render the first report section: inherited dataset facts."""

    subject_count = _inventory_value(report, "subject_count", "unknown")
    imaging_session_count = _inventory_value(
        report, "imaging_session_count", "unknown"
    )
    image_count = _inventory_value(report, "image_count", "unknown")
    images_by_datatype = _inventory_value(
        report, "images_by_datatype", {}
    )
    session_counts = _inventory_value(report, "session_counts", {})

    lines = [
        "## Dataset summary",
        "",
        "| Measure | Value |",
        "| --- | ---: |",
        f"| Subjects | {subject_count} |",
        f"| Imaging sessions | {imaging_session_count} |",
        f"| NIfTI images | {image_count} |",
        "",
        "### Sessions",
        "",
    ]

    if session_counts:
        lines.extend(
            [
                "| Session name | Imaging sessions |",
                "| --- | ---: |",
            ]
        )
        lines.extend(
            f"| `{name}` | {count} |"
            for name, count in session_counts.items()
        )
    else:
        lines.append("No session directories were found.")

    lines.extend(["", "### Images by datatype", ""])
    if images_by_datatype:
        lines.extend(["| Datatype | Images |", "| --- | ---: |"])
        lines.extend(
            f"| `{datatype}` | {count} |"
            for datatype, count in images_by_datatype.items()
        )
    else:
        lines.append("No recognized NIfTI images were found.")

    return "\n".join(lines)


def render_imaging_inventory(report: ValidationReport) -> str:
    """Render normalized image coverage."""

    coverage = _inventory_value(report, "coverage", [])
    imaging_session_count = _inventory_value(
        report, "imaging_session_count", "unknown"
    )

    lines = [
        "## Imaging coverage",
        "",
        "Each imaging session is counted once per coverage type.",
        "",
        "| Coverage type | Count |",
        "| --- | ---: |",
    ]
    if coverage:
        lines.extend(
            f"| `{item['type']}` | {item['count']} / {imaging_session_count} |"
            for item in coverage
        )
    else:
        lines.append("| No recognized image types | 0 |")

    return "\n".join(lines)


def render_imaging_unit_inventory(report: ValidationReport) -> str:
    """Render the deferred subject/session-level image inventory."""

    units = _inventory_value(report, "imaging_units", [])

    lines = [
        "## Imaging-unit inventory",
        "",
        "| Imaging unit | Session | Images | Coverage types |",
        "| --- | --- | ---: | --- |",
    ]
    lines.extend(
        [
            *(
                f"| `{unit['path']}` | "
                f"{unit['session'] or 'direct data'} | "
                f"{unit['image_count']} | "
                f"{', '.join(f'`{item}`' for item in unit['coverage_types']) or 'none'} |"
                for unit in units
            )
        ]
    )
    if not units:
        lines.append("| No imaging units found | — | 0 | none |")

    return "\n".join(lines)


def render(report: ValidationReport) -> str:
    """Render the currently implemented Markdown report sections."""

    return "\n\n".join(
        (
            "# MIDS Validator Report",
            render_dataset_summary(report),
            render_imaging_inventory(report),
            render_findings(report),
            # Deferred until the unit-level inventory is more useful:
            # render_imaging_unit_inventory(report),
        )
    ) + "\n"


def write(report: ValidationReport, path: Path) -> None:
    """Write a Markdown report to ``path``."""

    path.write_text(render(report), encoding="utf-8")
