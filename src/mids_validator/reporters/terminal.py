"""Render a concise human-readable validation summary for the terminal."""

from mids_validator.models import ValidationReport


def render(report: ValidationReport, report_directory: str) -> str:
    """Return a short summary without rescanning the dataset."""

    summary = report.summary
    return (
        "Validation complete: "
        f"{summary['error']} error(s), "
        f"{summary['warning']} warning(s), "
        f"{summary['info']} info finding(s).\n"
        f"HTML report: {report_directory}/report.html\n"
        f"Markdown report: {report_directory}/report.md\n"
        f"JSON report: {report_directory}/report.json"
    )
