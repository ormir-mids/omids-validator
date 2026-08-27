"""Shared data structures used by validation and reporting."""

from dataclasses import dataclass
from enum import Enum


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
