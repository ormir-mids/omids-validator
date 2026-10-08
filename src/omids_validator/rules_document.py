"""Turn the packaged rule catalogue into a readable Markdown document.

The command-line interface calls this module for ``omids_validator --rules``.
"""

from pathlib import Path

from omids_validator.models import Severity
from omids_validator.rule_catalog import (
    NEXT_STEP_KINDS,
    NextStep,
    RuleCatalog,
    load_rule_catalog,
)


LAYER_TITLES = {
    0: "Dataset structure",
    1: "File naming and relationships",
    2: "Sidecar files",
    3: "JSON metadata",
    4: "Optional image integrity and consistency",
    5: "Dataset-wide consistency and participants",
}

SEVERITY_DESCRIPTIONS = {
    Severity.ERROR: (
        "A convention violation likely to cause problems in downstream "
        "pipelines or prevent data and code from being interoperable between "
        "research groups. The user should fix it."
    ),
    Severity.WARNING: (
        "A probable problem or important inconsistency that the user should "
        "review and probably fix."
    ),
    Severity.INFO: "A non-blocking observation the user may appreciate knowing.",
}

GUIDANCE_DESCRIPTIONS = {
    "command": "an exact command is available",
    "tool": "a programmatic tool is available, with workflow-specific options",
    "manual": "a direct manual correction is available",
    "review": "the response depends on the dataset or study context",
    "none": "no action is normally required",
}

GLOSSARY = {
    "Dataset root": (
        "The top-level directory supplied to the validator. It contains "
        "`sub-<ID>` subject directories and, when present, `participants.tsv`."
    ),
    "Subject directory": (
        "A directory named `sub-<ID>` containing all imaging data for one "
        "participant."
    ),
    "Session directory": (
        "An optional directory named `ses-<ID>` inside a subject directory. "
        "It groups imaging data from one visit, time point, or session."
    ),
    "Datatype directory": (
        "A directory that groups images by imaging category. This validator "
        "currently recognizes `mr-anat`, `mr-quant`, `ct`, and `rx`."
    ),
    "Direct-datatype layout": (
        "A subject layout without session directories, where datatype "
        "directories occur immediately inside the subject directory."
    ),
    "NIfTI image": (
        "An imaging file with a `.nii` or `.nii.gz` extension."
    ),
    "JSON sidecar": (
        "A JSON metadata file stored beside an image. A primary sidecar has "
        "the same filename stem as its image."
    ),
    "Acquisition suffix": (
        "The final recognized acquisition label in an image filename, used "
        "to determine its datatype and metadata profile."
    ),
    "Participants table": (
        "The root-level `participants.tsv` file containing one "
        "`participant_id` row for each subject represented in the dataset."
    ),
}


def _rule_number(rule_id: str) -> int:
    """Return the numeric part of a validated rule ID."""

    return int(rule_id.rsplit("-", maxsplit=1)[1])


def _render_next_step(next_step: NextStep) -> str:
    """Render one guidance block with its optional command or tool."""

    lines = [f"**Recommended response:** {next_step.text}"]
    if next_step.command is not None:
        lines.extend(["", f"**Command:** `{next_step.command}`"])
    if next_step.tool is not None:
        lines.extend(["", f"**Tool:** `{next_step.tool}`"])
    return "\n".join(lines)


def _render_rule(rule_id: str, catalogue: RuleCatalog) -> str:
    """Render one validated rule definition."""

    rule = catalogue.get(rule_id)
    lines = [
        f"### {rule.rule_id} — {rule.title}",
        "",
        f"- **Severity:** {rule.severity.value.upper()}",
        f"- **Response type:** {rule.next_step.kind}",
        "",
        rule.description,
        "",
        _render_next_step(rule.next_step),
    ]
    return "\n".join(lines)


def render_rules_markdown(catalogue: RuleCatalog | None = None) -> str:
    """Return the complete human-readable rule catalogue."""

    selected_catalogue = catalogue or load_rule_catalog()
    lines = [
        (
            "<!-- Generated from the packaged rules.json catalogue. "
            "Do not edit directly. -->"
        ),
        "",
        "# OMIDS Validator Rules",
        "",
        "## Purpose",
        "",
        (
            "The OMIDS Validator evaluates finished ORMIR-MIDS datasets and "
            "reports structural, naming, sidecar, metadata, image-header, and "
            "dataset-wide consistency findings."
        ),
        "",
        (
            "This document is generated from the packaged `rules.json` "
            f"catalogue (schema version {selected_catalogue.schema_version})."
        ),
        "",
        "## Severity",
        "",
    ]

    for severity in Severity:
        lines.append(
            f"- **{severity.value.upper()}:** "
            f"{SEVERITY_DESCRIPTIONS[severity]}"
        )

    lines.extend(["", "## Response types", ""])
    for kind in NEXT_STEP_KINDS:
        lines.append(f"- **{kind}:** {GUIDANCE_DESCRIPTIONS[kind]}.")

    rule_ids_by_layer: dict[int, list[str]] = {}
    for rule_id, rule in selected_catalogue.rules.items():
        if rule.status != "active":
            continue
        rule_ids_by_layer.setdefault(rule.layer, []).append(rule_id)

    for layer in sorted(rule_ids_by_layer):
        title = LAYER_TITLES.get(layer, "Reserved")
        lines.extend(["", f"## Layer {layer}: {title}", ""])
        rule_ids = sorted(rule_ids_by_layer[layer], key=_rule_number)
        lines.append(
            "\n\n".join(
                _render_rule(rule_id, selected_catalogue)
                for rule_id in rule_ids
            )
        )

    lines.extend(["", "## Glossary", ""])
    for term, definition in GLOSSARY.items():
        lines.append(f"- **{term}:** {definition}")

    return "\n".join(lines) + "\n"


def write_rules_markdown(
    path: Path,
    catalogue: RuleCatalog | None = None,
) -> None:
    """Write the human-readable rule catalogue to ``path``."""

    path.write_text(
        render_rules_markdown(catalogue),
        encoding="utf-8",
    )
