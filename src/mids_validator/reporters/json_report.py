"""Serialize the machine-readable JSON validation report.

The reporter consumes a completed :class:`ValidationReport`; it does not run
validation or inspect the filesystem.
"""

import json
from pathlib import Path
from typing import Any

from mids_validator.models import ValidationReport


def as_dict(report: ValidationReport) -> dict[str, Any]:
    """Return the stable, grouped JSON representation of ``report``."""

    findings_by_rule: dict[str, dict[str, Any]] = {}
    for finding in report.findings:
        group = findings_by_rule.setdefault(
            finding.rule_id,
            {
                "severity": finding.severity.value,
                "title": finding.title,
                "count": 0,
                "paths": [],
                "findings": [],
            },
        )
        group["count"] += 1
        if finding.path is not None:
            group["paths"].append(finding.path)
        group["findings"].append(
            {
                "message": finding.message,
                "path": finding.path,
                "severity": finding.severity.value,
                "title": finding.title,
            }
        )

    for group in findings_by_rule.values():
        severities = sorted({item["severity"] for item in group["findings"]})
        titles = sorted({item["title"] for item in group["findings"]})
        group["severity"] = severities[0] if len(severities) == 1 else "mixed"
        group["title"] = titles[0] if len(titles) == 1 else "mixed"
        group["paths"].sort()
        group["findings"].sort(
            key=lambda item: (
                item["path"] or "",
                item["message"],
                item["severity"],
                item["title"],
            )
        )

    return {
        "schema_version": report.schema_version,
        "validator_version": report.validator_version,
        "dataset_root": report.dataset_root,
        "run": {
            "timestamp": report.run.timestamp,
            "inspect_images": report.run.inspect_images,
            "participants_requested": report.run.participants_requested,
        },
        "summary": dict(report.summary),
        "findings_by_rule": dict(sorted(findings_by_rule.items())),
        "actions": [dict(action) for action in report.actions],
        "inventory": dict(report.inventory),
    }


def write(report: ValidationReport, path: Path) -> None:
    """Write ``report`` as indented UTF-8 JSON to ``path``."""

    path.write_text(
        json.dumps(as_dict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
