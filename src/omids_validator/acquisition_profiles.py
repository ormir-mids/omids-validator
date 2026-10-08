"""Load the scan-type definitions used by Layers 1 and 3.

The definitions connect recognized filename suffixes with their allowed folders
and required JSON metadata fields.
"""

import json
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from omids_validator.file_types import nifti_stem
from omids_validator.inventory import VALID_DATATYPE_DIRECTORIES


METADATA_SCHEMA_VERSION = "0.1"
REQUIREMENT_STATUSES = frozenset({"mandatory", "optional", "proposed", "draft"})
PROFILE_FIELDS = frozenset(
    {
        "imaging_method",
        "folders",
        "suffixes",
        "image_dimensions",
        "dimension_labels",
        "json_fields",
        "inherits_json_fields_from",
        "profile_notes",
        "profile_status",
        "suffix_status",
    }
)
REQUIRED_PROFILE_FIELDS = frozenset(
    {
        "imaging_method",
        "folders",
        "suffixes",
        "image_dimensions",
        "dimension_labels",
        "json_fields",
    }
)
JSON_FIELD_FIELDS = frozenset(
    {
        "name",
        "requirement_status",
        "unit",
        "expected_json_type",
        "expected_value",
        "allowed_values",
        "transcription_note",
    }
)
REQUIRED_JSON_FIELD_FIELDS = frozenset({"name", "requirement_status", "unit"})


class MetadataRequirementsError(ValueError):
    """Raised when the packaged metadata requirements are inconsistent."""


def _require_object(value: object, location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise MetadataRequirementsError(f"{location} must be a JSON object.")
    return value


def _require_nonempty_string(value: object, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MetadataRequirementsError(f"{location} must be a non-empty string.")
    return value


def _require_string_list(
    value: object,
    location: str,
    *,
    allow_empty: bool,
) -> list[str]:
    if not isinstance(value, list):
        raise MetadataRequirementsError(f"{location} must be a JSON array.")
    if not allow_empty and not value:
        raise MetadataRequirementsError(f"{location} must not be empty.")

    strings: list[str] = []
    for index, item in enumerate(value):
        strings.append(_require_nonempty_string(item, f"{location}[{index}]"))
    return strings


def _require_known_fields(
    value: dict[str, Any],
    *,
    required: frozenset[str],
    allowed: frozenset[str],
    location: str,
) -> None:
    missing = sorted(required - value.keys())
    unexpected = sorted(value.keys() - allowed)
    if missing:
        raise MetadataRequirementsError(
            f"{location} is missing required field(s): {', '.join(missing)}."
        )
    if unexpected:
        raise MetadataRequirementsError(
            f"{location} has unexpected field(s): {', '.join(unexpected)}."
        )


def _validate_json_field(
    value: object,
    *,
    profile_name: str,
    index: int,
) -> str:
    location = f"profiles.{profile_name}.json_fields[{index}]"
    field = _require_object(value, location)
    _require_known_fields(
        field,
        required=REQUIRED_JSON_FIELD_FIELDS,
        allowed=JSON_FIELD_FIELDS,
        location=location,
    )

    field_name = _require_nonempty_string(field["name"], f"{location}.name")
    requirement_status = _require_nonempty_string(
        field["requirement_status"],
        f"{location}.requirement_status",
    )
    if requirement_status not in REQUIREMENT_STATUSES:
        allowed_statuses = ", ".join(sorted(REQUIREMENT_STATUSES))
        raise MetadataRequirementsError(
            f"{location}.requirement_status must be one of: {allowed_statuses}."
        )

    unit = field["unit"]
    if unit is not None:
        _require_nonempty_string(unit, f"{location}.unit")

    for optional_string in (
        "expected_json_type",
        "expected_value",
        "transcription_note",
    ):
        if optional_string in field:
            _require_nonempty_string(
                field[optional_string],
                f"{location}.{optional_string}",
            )

    if "allowed_values" in field:
        _require_string_list(
            field["allowed_values"],
            f"{location}.allowed_values",
            allow_empty=False,
        )

    return field_name


def _validate_profile(profile_name: str, value: object) -> dict[str, Any]:
    location = f"profiles.{profile_name}"
    profile = _require_object(value, location)
    _require_known_fields(
        profile,
        required=REQUIRED_PROFILE_FIELDS,
        allowed=PROFILE_FIELDS,
        location=location,
    )

    _require_nonempty_string(profile["imaging_method"], f"{location}.imaging_method")
    folders = _require_string_list(
        profile["folders"],
        f"{location}.folders",
        allow_empty=False,
    )
    unsupported_folders = sorted(set(folders) - VALID_DATATYPE_DIRECTORIES)
    if unsupported_folders:
        raise MetadataRequirementsError(
            f"{location}.folders contains unsupported value(s): "
            + ", ".join(unsupported_folders)
            + "."
        )

    _require_string_list(
        profile["suffixes"],
        f"{location}.suffixes",
        allow_empty=True,
    )

    image_dimensions = profile["image_dimensions"]
    if not isinstance(image_dimensions, list) or not image_dimensions:
        raise MetadataRequirementsError(
            f"{location}.image_dimensions must be a non-empty JSON array."
        )
    for index, dimension in enumerate(image_dimensions):
        if (
            not isinstance(dimension, int)
            or isinstance(dimension, bool)
            or dimension <= 0
        ):
            raise MetadataRequirementsError(
                f"{location}.image_dimensions[{index}] must be a positive integer."
            )

    _require_string_list(
        profile["dimension_labels"],
        f"{location}.dimension_labels",
        allow_empty=False,
    )

    json_fields = profile["json_fields"]
    if not isinstance(json_fields, list):
        raise MetadataRequirementsError(
            f"{location}.json_fields must be a JSON array."
        )
    field_names: set[str] = set()
    for index, field in enumerate(json_fields):
        field_name = _validate_json_field(
            field,
            profile_name=profile_name,
            index=index,
        )
        if field_name in field_names:
            raise MetadataRequirementsError(
                f"{location}.json_fields repeats field {field_name!r}."
            )
        field_names.add(field_name)

    for optional_string in (
        "inherits_json_fields_from",
        "profile_status",
        "suffix_status",
    ):
        if optional_string in profile:
            _require_nonempty_string(
                profile[optional_string],
                f"{location}.{optional_string}",
            )

    if "profile_notes" in profile:
        _require_string_list(
            profile["profile_notes"],
            f"{location}.profile_notes",
            allow_empty=False,
        )

    return profile


def _validate_profile_relationships(profiles: dict[str, dict[str, Any]]) -> None:
    suffix_owners: dict[str, str] = {}
    for profile_name, profile in profiles.items():
        for suffix in profile["suffixes"]:
            normalized_suffix = suffix.casefold()
            existing_owner = suffix_owners.get(normalized_suffix)
            if existing_owner is not None:
                raise MetadataRequirementsError(
                    f"Suffix {suffix!r} is assigned to both {existing_owner!r} "
                    f"and {profile_name!r}."
                )
            suffix_owners[normalized_suffix] = profile_name

    visited: set[str] = set()
    visiting: set[str] = set()

    def visit(profile_name: str) -> None:
        if profile_name in visited:
            return
        if profile_name in visiting:
            raise MetadataRequirementsError(
                f"Profile inheritance contains a cycle at {profile_name!r}."
            )

        visiting.add(profile_name)
        parent_name = profiles[profile_name].get("inherits_json_fields_from")
        if parent_name is not None:
            if parent_name not in profiles:
                raise MetadataRequirementsError(
                    f"Profile {profile_name!r} inherits from unknown profile "
                    f"{parent_name!r}."
                )
            visit(parent_name)
        visiting.remove(profile_name)
        visited.add(profile_name)

    for profile_name in profiles:
        visit(profile_name)


def validate_metadata_requirements(value: object) -> dict[str, Any]:
    """Validate decoded metadata requirements and return the original mapping."""

    requirements = _require_object(value, "Metadata requirements")
    top_level_fields = frozenset(
        {"schema_version", "status", "source", "notes", "profiles", "shared_semantics"}
    )
    _require_known_fields(
        requirements,
        required=top_level_fields,
        allowed=top_level_fields,
        location="Metadata requirements",
    )

    schema_version = _require_nonempty_string(
        requirements["schema_version"],
        "Metadata requirements.schema_version",
    )
    if schema_version != METADATA_SCHEMA_VERSION:
        raise MetadataRequirementsError(
            "Unsupported metadata-requirements schema version "
            f"{schema_version!r}; expected {METADATA_SCHEMA_VERSION!r}."
        )

    _require_nonempty_string(requirements["status"], "Metadata requirements.status")
    _require_nonempty_string(requirements["source"], "Metadata requirements.source")
    _require_string_list(
        requirements["notes"],
        "Metadata requirements.notes",
        allow_empty=True,
    )
    _require_object(
        requirements["shared_semantics"],
        "Metadata requirements.shared_semantics",
    )

    raw_profiles = _require_object(
        requirements["profiles"],
        "Metadata requirements.profiles",
    )
    if not raw_profiles:
        raise MetadataRequirementsError(
            "Metadata requirements.profiles must not be empty."
        )

    profiles: dict[str, dict[str, Any]] = {}
    for profile_name, profile in raw_profiles.items():
        normalized_name = _require_nonempty_string(
            profile_name,
            "Metadata requirements profile name",
        )
        profiles[normalized_name] = _validate_profile(normalized_name, profile)

    _validate_profile_relationships(profiles)
    return requirements


def _object_without_duplicate_keys(
    pairs: list[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise MetadataRequirementsError(
                f"Metadata requirements repeat JSON key {key!r}."
            )
        result[key] = value
    return result


def parse_metadata_requirements(text: str) -> dict[str, Any]:
    """Decode and validate metadata-requirements JSON text."""

    try:
        value = json.loads(text, object_pairs_hook=_object_without_duplicate_keys)
    except json.JSONDecodeError as error:
        raise MetadataRequirementsError(
            f"Metadata requirements are not valid JSON: {error.msg}."
        ) from error
    return validate_metadata_requirements(value)


@lru_cache(maxsize=1)
def load_metadata_requirements() -> dict[str, Any]:
    """Load and validate the packaged metadata-requirements catalogue once."""

    requirements_path = files("omids_validator").joinpath(
        "data",
        "metadata_requirements.json",
    )
    try:
        text = requirements_path.read_text(encoding="utf-8")
    except OSError as error:
        raise MetadataRequirementsError(
            f"Metadata requirements could not be read: {error}."
        ) from error
    return parse_metadata_requirements(text)


def acquisition_profiles() -> dict[str, dict[str, Any]]:
    """Return the acquisition profiles from the requirements catalogue."""

    return load_metadata_requirements()["profiles"]


@lru_cache(maxsize=1)
def _suffix_to_profile_name() -> dict[str, str]:
    """Return case-folded recognized suffixes mapped to profile names."""

    suffix_map: dict[str, str] = {}

    for profile_name, profile in acquisition_profiles().items():
        for suffix in profile.get("suffixes", []):
            normalized_suffix = suffix.casefold()
            if normalized_suffix in suffix_map:
                raise ValueError(
                    f"Acquisition suffix is assigned twice: {suffix}"
                )
            suffix_map[normalized_suffix] = profile_name

    return suffix_map


def image_suffix(image_path: Path) -> str | None:
    """Return a recognized compound suffix or the final filename component."""

    image_stem = nifti_stem(image_path)
    if image_stem is None:
        return None

    normalized_stem = image_stem.casefold()
    recognized_suffixes = sorted(
        _suffix_to_profile_name(),
        key=len,
        reverse=True,
    )

    for recognized_suffix in recognized_suffixes:
        if normalized_stem.endswith(f"_{recognized_suffix}"):
            return recognized_suffix

    if "_" not in image_stem:
        return None

    return image_stem.rsplit("_", maxsplit=1)[-1]


def acquisition_profile_for_suffix(
    suffix: str,
) -> dict[str, Any] | None:
    """Return the recognized acquisition profile for a suffix, if any."""

    profile_name = _suffix_to_profile_name().get(suffix.casefold())
    if profile_name is None:
        return None

    return acquisition_profiles()[profile_name]


@lru_cache(maxsize=None)
def _resolved_metadata_fields(
    profile_name: str,
) -> tuple[dict[str, Any], ...]:
    """Return inherited fields with child definitions overriding parents."""

    profile = acquisition_profiles()[profile_name]
    fields_by_name: dict[str, dict[str, Any]] = {}
    parent_name = profile.get("inherits_json_fields_from")

    if parent_name is not None:
        for field in _resolved_metadata_fields(parent_name):
            fields_by_name[field["name"]] = field

    for field in profile.get("json_fields", []):
        fields_by_name[field["name"]] = field

    return tuple(fields_by_name.values())


def metadata_fields_for_suffix(
    suffix: str,
) -> tuple[dict[str, Any], ...] | None:
    """Return resolved metadata fields for a recognized image suffix."""

    profile_name = _suffix_to_profile_name().get(suffix.casefold())
    if profile_name is None:
        return None

    return _resolved_metadata_fields(profile_name)
