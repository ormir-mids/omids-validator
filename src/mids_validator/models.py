"""Shared data structures used by validation and reporting."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Severity(str, Enum):
    """Allowed levels of attention for a validation finding.

    Inheriting from ``str`` means values serialize naturally as ``"error"``,
    ``"warning"``, and ``"info"`` in a future JSON report.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Finding:
    """One issue or observation produced by a validation rule.

    ``frozen=True`` prevents a finding from being accidentally changed after a
    rule returns it. Paths are stored relative to the dataset root whenever
    possible so reports remain portable between computers.
    """

    rule_id: str
    severity: Severity
    title: str
    message: str
    path: str | None = None


@dataclass(frozen=True)
class ValidationRun:
    """Context for one validation request."""

    timestamp: str
    inspect_images: bool
    participants_requested: bool


@dataclass(frozen=True)
class ValidationReport:
    """The single coordinator output consumed by future report renderers.

    This object contains no open files or filesystem handles. Report modules
    can therefore serialize or render it without running validation again.
    """

    schema_version: str
    validator_version: str
    dataset_root: str
    run: ValidationRun
    findings: tuple[Finding, ...]
    summary: dict[str, int]
    inventory: dict[str, Any]
    actions: tuple[dict[str, Any], ...] = ()

    def as_dict(self) -> dict[str, Any]:
        """Return a renderer-ready, JSON-compatible representation."""

        return {
            "schema_version": self.schema_version,
            "validator_version": self.validator_version,
            "dataset_root": self.dataset_root,
            "run": {
                "timestamp": self.run.timestamp,
                "inspect_images": self.run.inspect_images,
                "participants_requested": self.run.participants_requested,
            },
            "findings": [
                {
                    "rule_id": finding.rule_id,
                    "severity": finding.severity.value,
                    "title": finding.title,
                    "message": finding.message,
                    "path": finding.path,
                }
                for finding in self.findings
            ],
            "summary": dict(self.summary),
            "inventory": dict(self.inventory),
            "actions": [dict(action) for action in self.actions],
        }
