"""Load acquisition profiles and interpret MIDS image suffixes."""

import json
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from mids_validator.file_types import nifti_stem


@lru_cache(maxsize=1)
def load_metadata_requirements() -> dict[str, Any]:
    """Load the packaged metadata-requirements catalogue once."""

    requirements_path = files("mids_validator").joinpath(
        "data",
        "metadata_requirements.json",
    )
    with requirements_path.open(encoding="utf-8") as requirements_file:
        return json.load(requirements_file)


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
