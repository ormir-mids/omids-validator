"""Read patient age and sex once for Layer 5 and participant updates.

The collector uses paths already present in ``DatasetInventory``. It preserves
the source strings and does not report unreadable JSON because Layer 2 already
handles sidecar readability findings.
"""

import json
import re
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

from omids_validator.inventory import DatasetInventory


DICOM_AGE_PATTERN = re.compile(r"^(?P<number>[0-9]{3})(?P<unit>[DWMY])$")
DICOM_AGE_UNIT_DAYS = {
    "D": Fraction(1),
    "W": Fraction(7),
    "M": Fraction(365, 12),
    "Y": Fraction(365),
}


@dataclass(frozen=True)
class PatientMetadataObservation:
    """Usable demographic strings read from one patient JSON sidecar."""

    path: Path
    subject_id: str
    session_id: str | None
    age: str | None
    sex: str | None


@dataclass(frozen=True)
class PatientMetadataCollection:
    """Patient metadata collected during one pass through the sidecars."""

    observations: tuple[PatientMetadataObservation, ...]

    def for_subject(
        self,
        subject_id: str,
    ) -> tuple[PatientMetadataObservation, ...]:
        """Return observations belonging to one subject."""

        return tuple(
            observation
            for observation in self.observations
            if observation.subject_id == subject_id
        )


def _nonempty_string(value: object) -> str | None:
    """Return a source string when it contains non-whitespace text."""

    if not isinstance(value, str) or not value.strip():
        return None
    return value


def collect_patient_metadata(
    inventory: DatasetInventory,
) -> PatientMetadataCollection:
    """Read each discovered patient JSON sidecar at most once."""

    observations: list[PatientMetadataObservation] = []
    for subject_directory in inventory.subject_directories():
        session_directories = set(
            inventory.session_directories(subject_directory)
        )
        for datatype_directory in inventory.datatype_directories(
            subject_directory
        ):
            session_id = (
                datatype_directory.parent.name
                if datatype_directory.parent in session_directories
                else None
            )
            for path in inventory.children(datatype_directory):
                if not (
                    path.is_file()
                    and path.name.casefold().endswith("_patient.json")
                ):
                    continue

                try:
                    with path.open(encoding="utf-8") as json_file:
                        contents = json.load(json_file)
                except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                    continue

                if not isinstance(contents, dict):
                    continue
                age = _nonempty_string(contents.get("Age"))
                sex = _nonempty_string(contents.get("Sex"))
                if age is None and sex is None:
                    continue

                observations.append(
                    PatientMetadataObservation(
                        path=path,
                        subject_id=subject_directory.name,
                        session_id=session_id,
                        age=age,
                        sex=sex,
                    )
                )

    return PatientMetadataCollection(observations=tuple(observations))


def youngest_age_for_subject(
    collection: PatientMetadataCollection,
    subject_id: str,
) -> str | None:
    """Return the youngest valid DICOM age while preserving its source text."""

    ranked_ages: list[tuple[Fraction, str]] = []
    for observation in collection.for_subject(subject_id):
        if observation.age is None:
            continue
        match = DICOM_AGE_PATTERN.fullmatch(observation.age)
        if match is None:
            continue
        number = int(match.group("number"))
        age_in_days = number * DICOM_AGE_UNIT_DAYS[match.group("unit")]
        ranked_ages.append((age_in_days, observation.age))

    if not ranked_ages:
        return None
    return min(ranked_ages, key=lambda item: item[0])[1]


def consistent_sex_for_subject(
    collection: PatientMetadataCollection,
    subject_id: str,
) -> str | None:
    """Return the source sex string only when all observations agree."""

    observed_values = {
        observation.sex
        for observation in collection.for_subject(subject_id)
        if observation.sex is not None
    }
    if len(observed_values) != 1:
        return None
    return next(iter(observed_values))
