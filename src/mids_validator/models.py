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
