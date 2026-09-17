"""Render a self-contained HTML validation report.

The reporter consumes a completed :class:`ValidationReport`; it does not run
validation or inspect the dataset. All styles are embedded so the resulting
file can be opened locally without a network connection.
"""

from html import escape
from pathlib import Path
from typing import Any

from mids_validator.models import Finding, Severity, ValidationReport
from mids_validator.reporters.report_data import (
    ACTIONABLE_SEVERITIES,
    FINDING_EXAMPLE_THRESHOLD,
    SEVERITY_DESCRIPTIONS,
    SEVERITY_HEADINGS,
    SEVERITY_ORDER,
    group_findings,
    inventory_value,
    sort_rule_groups,
)
from mids_validator.rule_catalog import NextStep, load_rule_catalog


STYLES = """
:root {
  color-scheme: light;
  --background: #f3f6f8;
  --surface: #ffffff;
  --text: #17212b;
  --muted: #5b6773;
  --border: #d7dee5;
  --accent: #195f7a;
  --error: #a52a2a;
  --error-soft: #fff1f0;
  --warning: #8a5700;
  --warning-soft: #fff8e6;
  --info: #255e91;
  --info-soft: #eef6fc;
  --success: #216b45;
  --success-soft: #edf8f1;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  line-height: 1.55;
}

* { box-sizing: border-box; }

body {
  margin: 0;
  background: var(--background);
  color: var(--text);
}

a { color: var(--accent); }
a:hover { text-decoration-thickness: 2px; }

code {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 0.92em;
  overflow-wrap: anywhere;
}

.page-header {
  background: #153846;
  color: #ffffff;
  padding: 3.5rem 1.5rem 3rem;
}

.container {
  width: min(72rem, 100%);
  margin: 0 auto;
}

.eyebrow {
  margin: 0 0 0.35rem;
  color: #b9dce9;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.12em;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: clamp(2rem, 6vw, 3.25rem);
  line-height: 1.08;
}

.lede {
  max-width: 44rem;
  margin: 0.8rem 0 0;
  color: #d9e8ee;
  font-size: 1.05rem;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.8rem;
  margin-top: 2rem;
}

.summary-card {
  padding: 1rem 1.1rem;
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 0.65rem;
  background: rgba(255, 255, 255, 0.08);
}

.summary-number {
  display: block;
  font-size: 1.8rem;
  font-weight: 750;
  line-height: 1;
}

.summary-label {
  display: block;
  margin-top: 0.35rem;
  color: #d9e8ee;
}

main { padding: 2rem 1.5rem 4rem; }

.panel {
  margin-top: 1.25rem;
  padding: clamp(1.1rem, 3vw, 1.7rem);
  border: 1px solid var(--border);
  border-radius: 0.8rem;
  background: var(--surface);
  box-shadow: 0 0.2rem 0.8rem rgba(30, 50, 65, 0.05);
}

.panel > :first-child { margin-top: 0; }
.panel > :last-child { margin-bottom: 0; }

h2 {
  margin: 0 0 0.35rem;
  font-size: 1.45rem;
  line-height: 1.25;
}

h3 {
  margin: 1.6rem 0 0.5rem;
  font-size: 1.05rem;
}

.section-description {
  margin: 0 0 1.2rem;
  color: var(--muted);
}

.table-wrap { overflow-x: auto; }

table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  padding: 0.65rem 0.75rem;
  border-bottom: 1px solid var(--border);
  text-align: left;
  vertical-align: top;
}

th {
  color: var(--muted);
  font-size: 0.78rem;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

td:last-child, th:last-child { text-align: right; }

.severity-section {
  border-top: 0.35rem solid var(--info);
}

.severity-section.error { border-top-color: var(--error); }
.severity-section.warning { border-top-color: var(--warning); }
.severity-section.info { border-top-color: var(--info); }

.rule-group {
  margin-top: 1rem;
  padding: 1rem 1.1rem;
  border: 1px solid var(--border);
  border-left-width: 0.3rem;
  border-radius: 0.55rem;
  background: #fbfcfd;
}

.rule-group.error {
  border-left-color: var(--error);
  background: var(--error-soft);
}

.rule-group.warning {
  border-left-color: var(--warning);
  background: var(--warning-soft);
}

.rule-group.info {
  border-left-color: var(--info);
  background: var(--info-soft);
}

.rule-heading {
  margin: 0;
  font-size: 1rem;
}

.finding-count {
  margin: 0.2rem 0 0.8rem;
  color: var(--muted);
  font-size: 0.9rem;
}

.finding-list {
  margin: 0;
  padding-left: 1.25rem;
}

.finding-list li + li { margin-top: 0.55rem; }
.finding-message { color: var(--muted); }

.representative-path {
  display: block;
  margin-top: 0.35rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--border);
  border-radius: 0.35rem;
  background: var(--surface);
}

.guidance-group {
  margin-top: 1.4rem;
  padding-top: 1.2rem;
  border-top: 1px solid var(--border);
}

.guidance-item + .guidance-item { margin-top: 1.2rem; }
.guidance-item h4 { margin: 0 0 0.35rem; }
.guidance-item p { margin: 0.3rem 0; }

.success-panel {
  border-color: #b8dec7;
  background: var(--success-soft);
}

.report-footer {
  margin-top: 2rem;
  color: var(--muted);
  font-size: 0.9rem;
  text-align: center;
}

@media (max-width: 38rem) {
  .summary-grid { grid-template-columns: 1fr; }
  .page-header { padding-top: 2.5rem; }
}

@media print {
  :root { --background: #ffffff; }
  .page-header { padding: 1.5rem 0; background: #ffffff; color: #000000; }
  .page-header .eyebrow, .page-header .lede { color: #333333; }
  main { padding: 0; }
  .panel, .rule-group { break-inside: avoid; box-shadow: none; }
  .summary-card { border-color: #999999; background: #ffffff; color: #000000; }
  .summary-label { color: #333333; }
}
""".strip()


def _text(value: object) -> str:
    """Return escaped HTML text for one report value."""

    return escape(str(value), quote=True)


def _render_table(headers: tuple[str, str], rows: list[tuple[object, object]]) -> str:
    """Render a two-column table with escaped cell contents."""

    body = "\n".join(
        f"<tr><td>{_text(label)}</td><td>{_text(value)}</td></tr>"
        for label, value in rows
    )
    return (
        '<div class="table-wrap">\n'
        "<table>\n"
        f"<thead><tr><th>{_text(headers[0])}</th>"
        f"<th>{_text(headers[1])}</th></tr></thead>\n"
        f"<tbody>\n{body}\n</tbody>\n"
        "</table>\n"
        "</div>"
    )


def render_dataset_summary(report: ValidationReport) -> str:
    """Render inherited dataset facts and image counts."""

    subject_count = inventory_value(report, "subject_count", "unknown")
    imaging_session_count = inventory_value(
        report, "imaging_session_count", "unknown"
    )
    image_count = inventory_value(report, "image_count", "unknown")
    session_counts = inventory_value(report, "session_counts", {})
    images_by_datatype = inventory_value(report, "images_by_datatype", {})

    summary_table = _render_table(
        ("Measure", "Value"),
        [
            ("Subjects", subject_count),
            ("Imaging sessions", imaging_session_count),
            ("NIfTI images", image_count),
        ],
    )

    if session_counts:
        session_table = _render_table(
            ("Session name", "Imaging sessions"),
            list(session_counts.items()),
        )
    else:
        session_table = "<p>No session directories were found.</p>"

    if images_by_datatype:
        datatype_table = _render_table(
            ("Datatype", "Images"),
            list(images_by_datatype.items()),
        )
    else:
        datatype_table = "<p>No recognized NIfTI images were found.</p>"

    return "\n".join(
        (
            '<section class="panel" aria-labelledby="dataset-summary">',
            '<h2 id="dataset-summary">Dataset summary</h2>',
            summary_table,
            "<h3>Sessions</h3>",
            session_table,
            "<h3>Images by datatype</h3>",
            datatype_table,
            "</section>",
        )
    )


def render_imaging_inventory(report: ValidationReport) -> str:
    """Render normalized image coverage."""

    coverage = inventory_value(report, "coverage", [])
    imaging_session_count = inventory_value(
        report, "imaging_session_count", "unknown"
    )
    rows = [
        (item["type"], f"{item['count']} / {imaging_session_count}")
        for item in coverage
    ]
    if not rows:
        rows = [("No recognized image types", 0)]

    return "\n".join(
        (
            '<section class="panel" aria-labelledby="imaging-coverage">',
            '<h2 id="imaging-coverage">Imaging coverage</h2>',
            (
                '<p class="section-description">Each imaging session is '
                "counted once per coverage type.</p>"
            ),
            _render_table(("Coverage type", "Count"), rows),
            "</section>",
        )
    )


def _render_path(finding: Finding) -> str:
    """Render one escaped path or a dataset-level placeholder."""

    if finding.path is None:
        return '<span class="finding-path">(dataset-level finding)</span>'
    return f"<code>{_text(finding.path)}</code>"


def render_rule_group(
    rule_id: str,
    group: dict[str, Any],
    *,
    example_threshold: int = FINDING_EXAMPLE_THRESHOLD,
) -> str:
    """Render one rule group with all or representative paths."""

    severity: Severity = group["severity"]
    findings: list[Finding] = sorted(
        group["findings"],
        key=lambda finding: (finding.path or "", finding.message),
    )
    count = len(findings)
    parts = [
        f'<article class="rule-group {severity.value}">',
        (
            f'<h3 class="rule-heading">{_text(rule_id)} '
            f"&mdash; {_text(group['title'])}</h3>"
        ),
        f'<p class="finding-count">{count} finding(s).</p>',
    ]

    if count <= example_threshold:
        parts.append('<ul class="finding-list">')
        for finding in findings:
            message = ""
            if finding.message:
                message = (
                    f' <span class="finding-message">&mdash; '
                    f"{_text(finding.message)}</span>"
                )
            parts.append(f"<li>{_render_path(finding)}{message}</li>")
        parts.append("</ul>")
    else:
        example = findings[0]
        parts.extend(
            (
                "<p><strong>Representative finding:</strong> "
                f"{_text(example.message)}</p>",
                "<p><strong>Representative path:</strong>"
                f'<code class="representative-path">'
                f"{_text(example.path or '(dataset-level finding)')}</code></p>",
                (
                    '<p>See <a href="report.json">report.json</a> for the '
                    "complete list.</p>"
                ),
            )
        )

    parts.append("</article>")
    return "\n".join(parts)


def render_findings(report: ValidationReport) -> str:
    """Render findings by severity and numeric rule order."""

    sorted_groups = sort_rule_groups(group_findings(report))
    sections: list[str] = []
    for severity in SEVERITY_ORDER:
        groups = sorted_groups[severity]
        if not groups:
            continue

        parts = [
            (
                f'<section class="panel severity-section {severity.value}" '
                f'aria-labelledby="{severity.value}-findings">'
            ),
            (
                f'<h2 id="{severity.value}-findings">'
                f"{_text(SEVERITY_HEADINGS[severity])}</h2>"
            ),
            (
                '<p class="section-description">'
                f"{_text(SEVERITY_DESCRIPTIONS[severity])}</p>"
            ),
        ]
        parts.extend(
            render_rule_group(rule_id, group) for rule_id, group in groups
        )
        parts.append("</section>")
        sections.append("\n".join(parts))

    if not sections:
        return "\n".join(
            (
                '<section class="panel success-panel" '
                'aria-labelledby="no-findings">',
                '<h2 id="no-findings">No findings</h2>',
                "<p>The validator did not record any errors, warnings, or "
                "informational findings.</p>",
                "</section>",
            )
        )

    return "\n".join(sections)


def _render_recommended_response(next_step: NextStep) -> str:
    """Render one escaped catalogue response with optional command and tool."""

    parts = [
        "<p><strong>Recommended response:</strong> "
        f"{_text(next_step.text)}</p>"
    ]
    if next_step.command is not None:
        parts.append(
            f"<p><strong>Command:</strong> <code>"
            f"{_text(next_step.command)}</code></p>"
        )
    if next_step.tool is not None:
        parts.append(
            f"<p><strong>Tool:</strong> <code>{_text(next_step.tool)}</code></p>"
        )
    return "\n".join(parts)


def render_practical_next_steps(report: ValidationReport) -> str:
    """Render catalogue guidance for triggered errors and warnings."""

    sorted_groups = sort_rule_groups(group_findings(report))
    if not any(sorted_groups[severity] for severity in ACTIONABLE_SEVERITIES):
        return ""

    catalogue = load_rule_catalog()
    parts = [
        '<section class="panel" aria-labelledby="next-steps">',
        '<h2 id="next-steps">Practical next steps</h2>',
        (
            '<p class="section-description">The guidance below is generated '
            "from the rules triggered in this validation. Review the affected "
            "paths and messages in the findings sections above before making "
            "changes.</p>"
        ),
    ]

    for severity in ACTIONABLE_SEVERITIES:
        groups = sorted_groups[severity]
        if not groups:
            continue

        parts.extend(
            (
                '<div class="guidance-group">',
                f"<h3>{_text(SEVERITY_HEADINGS[severity])}</h3>",
            )
        )
        for rule_id, _group in groups:
            rule = catalogue.get(rule_id)
            parts.extend(
                (
                    '<div class="guidance-item">',
                    f"<h4>{_text(rule.rule_id)} &mdash; "
                    f"{_text(rule.title)}</h4>",
                    _render_recommended_response(rule.next_step),
                    "</div>",
                )
            )
        parts.append("</div>")

    parts.append("</section>")
    return "\n".join(parts)


def render(report: ValidationReport) -> str:
    """Render a complete standalone HTML document."""

    summary_cards = "\n".join(
        (
            f'<div class="summary-card {severity.value}">'
            f'<span class="summary-number">'
            f"{_text(report.summary.get(severity.value, 0))}</span>"
            f'<span class="summary-label">'
            f"{_text(SEVERITY_HEADINGS[severity])}</span></div>"
        )
        for severity in SEVERITY_ORDER
    )
    sections = [
        render_dataset_summary(report),
        render_imaging_inventory(report),
        render_findings(report),
    ]
    practical_next_steps = render_practical_next_steps(report)
    if practical_next_steps:
        sections.append(practical_next_steps)

    body = "\n".join(sections)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>MIDS Validator Report</title>
  <style>
{STYLES}
  </style>
</head>
<body>
  <header class="page-header">
    <div class="container">
      <p class="eyebrow">MIDS validator</p>
      <h1>Validation report</h1>
      <p class="lede">A human-readable summary of dataset contents and
        validation findings.</p>
      <div class="summary-grid" aria-label="Finding summary">
{summary_cards}
      </div>
    </div>
  </header>
  <main class="container">
{body}
    <p class="report-footer">Complete structured results are available in
      <a href="report.json">report.json</a>.</p>
  </main>
</body>
</html>
"""


def write(report: ValidationReport, path: Path) -> None:
    """Write ``report`` as a self-contained UTF-8 HTML document."""

    path.write_text(render(report), encoding="utf-8")
