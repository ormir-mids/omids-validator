"""Load the rule definitions used by validation, reports, and documentation.

Layer functions use ``finding_for_rule`` to give every finding the title,
severity, and guidance recorded in the packaged ``rules.json`` catalogue.
"""

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from types import MappingProxyType
from typing import Any, Mapping

from omids_validator.models import Finding, Severity


CATALOG_SCHEMA_VERSION = "1.0"
RULE_ID_PATTERN = re.compile(r"^MIDS-([0-9])([0-9]{2})$")
RULE_STATUSES = frozenset({"active", "deferred"})
NEXT_STEP_KINDS = ("command", "tool", "manual", "review", "none")


class RuleCatalogError(ValueError):
    """Raised when the packaged rule catalogue is internally inconsistent."""


@dataclass(frozen=True)
class NextStep:
    """One rule-level practical response."""

    kind: str
    text: str
    command: str | None = None
    tool: str | None = None


@dataclass(frozen=True)
class RuleDefinition:
    """Static definition shared by validation findings and documentation."""

    rule_id: str
    layer: int
    status: str
    title: str
    severity: Severity
    description: str
    next_step: NextStep


@dataclass(frozen=True)
class RuleCatalog:
    """Validated rule definitions from one catalogue schema version."""

    schema_version: str
    rules: Mapping[str, RuleDefinition]

    def get(self, rule_id: str) -> RuleDefinition:
        """Return one rule definition or raise a catalogue-specific error."""

        try:
            return self.rules[rule_id]
        except KeyError as error:
            raise RuleCatalogError(
                f"Rule catalogue does not define {rule_id}."
            ) from error


def _require_object(value: object, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise RuleCatalogError(f"{location} must be a JSON object.")
    return value


def _require_exact_fields(
    value: dict[str, Any],
    *,
    required: set[str],
    location: str,
) -> None:
    missing = sorted(required - value.keys())
    unexpected = sorted(value.keys() - required)
    if missing:
        raise RuleCatalogError(
            f"{location} is missing required field(s): {', '.join(missing)}."
        )
    if unexpected:
        raise RuleCatalogError(
            f"{location} has unexpected field(s): {', '.join(unexpected)}."
        )


def _require_nonempty_string(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RuleCatalogError(f"{location} must be a non-empty string.")
    return value


def _parse_next_step(value: object, rule_id: str) -> NextStep:
    location = f"{rule_id}.next_step"
    step = _require_object(value, location)
    kind = _require_nonempty_string(step.get("kind"), f"{location}.kind")
    if kind not in NEXT_STEP_KINDS:
        allowed = ", ".join(NEXT_STEP_KINDS)
        raise RuleCatalogError(
            f"{location}.kind must be one of: {allowed}."
        )

    required_fields = {"kind", "text"}
    if kind == "command":
        required_fields.add("command")
    elif kind == "tool":
        required_fields.add("tool")
    _require_exact_fields(step, required=required_fields, location=location)

    text = _require_nonempty_string(step["text"], f"{location}.text")
    command = None
    tool = None
    if kind == "command":
        command = _require_nonempty_string(
            step["command"], f"{location}.command"
        )
    elif kind == "tool":
        tool = _require_nonempty_string(step["tool"], f"{location}.tool")

    return NextStep(kind=kind, text=text, command=command, tool=tool)


def _parse_rule(rule_id: str, value: object) -> RuleDefinition:
    if not isinstance(rule_id, str):
        raise RuleCatalogError("Rule catalogue IDs must be strings.")

    match = RULE_ID_PATTERN.fullmatch(rule_id)
    if match is None:
        raise RuleCatalogError(
            f"Rule ID {rule_id!r} must match MIDS- followed by three digits."
        )

    location = f"rules.{rule_id}"
    rule = _require_object(value, location)
    _require_exact_fields(
        rule,
        required={
            "layer",
            "status",
            "title",
            "severity",
            "description",
            "next_step",
        },
        location=location,
    )

    layer = rule["layer"]
    if not isinstance(layer, int) or isinstance(layer, bool):
        raise RuleCatalogError(f"{location}.layer must be an integer.")
    expected_layer = int(match.group(1))
    if layer != expected_layer:
        raise RuleCatalogError(
            f"{location}.layer must be {expected_layer} to match {rule_id}."
        )

    status = _require_nonempty_string(rule["status"], f"{location}.status")
    if status not in RULE_STATUSES:
        allowed = ", ".join(sorted(RULE_STATUSES))
        raise RuleCatalogError(
            f"{location}.status must be one of: {allowed}."
        )

    severity_value = _require_nonempty_string(
        rule["severity"], f"{location}.severity"
    )
    try:
        severity = Severity(severity_value)
    except ValueError as error:
        allowed = ", ".join(severity.value for severity in Severity)
        raise RuleCatalogError(
            f"{location}.severity must be one of: {allowed}."
        ) from error

    return RuleDefinition(
        rule_id=rule_id,
        layer=layer,
        status=status,
        title=_require_nonempty_string(rule["title"], f"{location}.title"),
        severity=severity,
        description=_require_nonempty_string(
            rule["description"], f"{location}.description"
        ),
        next_step=_parse_next_step(rule["next_step"], rule_id),
    )


def validate_rule_catalog(value: object) -> RuleCatalog:
    """Validate decoded catalogue data and return immutable definitions."""

    catalogue = _require_object(value, "Rule catalogue")
    _require_exact_fields(
        catalogue,
        required={"schema_version", "rules"},
        location="Rule catalogue",
    )

    schema_version = _require_nonempty_string(
        catalogue["schema_version"], "Rule catalogue.schema_version"
    )
    if schema_version != CATALOG_SCHEMA_VERSION:
        raise RuleCatalogError(
            "Unsupported rule catalogue schema version "
            f"{schema_version!r}; expected {CATALOG_SCHEMA_VERSION!r}."
        )

    raw_rules = _require_object(catalogue["rules"], "Rule catalogue.rules")
    if not raw_rules:
        raise RuleCatalogError("Rule catalogue.rules must not be empty.")

    definitions = {
        rule_id: _parse_rule(rule_id, rule)
        for rule_id, rule in raw_rules.items()
    }
    return RuleCatalog(
        schema_version=schema_version,
        rules=MappingProxyType(definitions),
    )


def _object_without_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RuleCatalogError(f"Rule catalogue repeats JSON key {key!r}.")
        result[key] = value
    return result


def parse_rule_catalog(text: str) -> RuleCatalog:
    """Decode and validate rule-catalogue JSON text."""

    try:
        value = json.loads(text, object_pairs_hook=_object_without_duplicate_keys)
    except json.JSONDecodeError as error:
        raise RuleCatalogError(
            f"Rule catalogue is not valid JSON: {error.msg}."
        ) from error
    return validate_rule_catalog(value)


@lru_cache(maxsize=1)
def load_rule_catalog() -> RuleCatalog:
    """Load and validate the packaged rule catalogue once."""

    catalogue_path = files("omids_validator").joinpath("data", "rules.json")
    try:
        text = catalogue_path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuleCatalogError(
            f"Rule catalogue could not be read: {error}."
        ) from error
    return parse_rule_catalog(text)


def finding_for_rule(
    rule_id: str,
    *,
    message: str,
    path: str | None = None,
) -> Finding:
    """Create a finding using the catalogue title and severity."""

    rule = load_rule_catalog().get(rule_id)
    return Finding(
        rule_id=rule.rule_id,
        severity=rule.severity,
        title=rule.title,
        message=message,
        path=path,
    )
