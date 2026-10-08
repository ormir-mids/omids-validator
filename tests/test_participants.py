"""Tests for safe participant-table creation and population."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from omids_validator.inventory import build_inventory
from omids_validator.participants import create_or_populate_participants
from omids_validator.validator import validate


def _write_patient_json(
    root: Path,
    relative_path: str,
    contents: dict[str, object],
) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(contents), encoding="utf-8")


class ParticipantWorkflowTests(unittest.TestCase):
    """Verify explicit participant-table mutations and their boundaries."""

    def test_creates_example_headers_and_blank_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sub-02").mkdir()
            (root / "sub-01").mkdir()

            action = create_or_populate_participants(build_inventory(root))

            self.assertEqual(action["operation"], "created")
            self.assertEqual(
                (root / "participants.tsv").read_text(encoding="utf-8"),
                "participant_id\tage\tsex\tgroup\n"
                "sub-01\t\t\t\n"
                "sub-02\t\t\t\n",
            )

    def test_populates_missing_ids_without_changing_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sub-01").mkdir()
            (root / "sub-02").mkdir()
            table = root / "participants.tsv"
            table.write_text(
                "participant_id\tage\tsex\tgroup\nsub-01\t34\tF\tcontrol\n",
                encoding="utf-8",
            )

            action = create_or_populate_participants(build_inventory(root))

            self.assertEqual(action["operation"], "populated")
            self.assertEqual(
                table.read_text(encoding="utf-8"),
                "participant_id\tage\tsex\tgroup\n"
                "sub-01\t34\tF\tcontrol\n"
                "sub-02\t\t\t\n",
            )

    def test_malformed_table_is_not_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sub-01").mkdir()
            table = root / "participants.tsv"
            original = "age\n34\n"
            table.write_text(original, encoding="utf-8")

            action = create_or_populate_participants(build_inventory(root))

            self.assertEqual(action["operation"], "skipped")
            self.assertEqual(table.read_text(encoding="utf-8"), original)

    def test_case_variant_table_is_not_overwritten_on_case_insensitive_filesystem(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sub-01").mkdir()
            table = root / "Participants.tsv"
            original = "participant_id\nsub-01\n"
            table.write_text(original, encoding="utf-8")

            action = create_or_populate_participants(build_inventory(root))

            # On a case-sensitive filesystem this operation creates the exact
            # file. On macOS's default case-insensitive filesystem, exclusive
            # creation safely reports the unavoidable name collision.
            self.assertIn(action["operation"], {"created", "skipped"})
            self.assertEqual(table.read_text(encoding="utf-8"), original)

    def test_coordinator_runs_layer_5_after_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sub-01").mkdir()

            report = validate(root, participants_requested=True, timestamp="now")

            self.assertEqual(report.actions[0]["operation"], "created")
            participant_rule_ids = {
                finding.rule_id
                for finding in report.findings
                if finding.rule_id.startswith("MIDS-5")
            }
            self.assertNotIn("MIDS-501", participant_rule_ids)
            self.assertNotIn("MIDS-504", participant_rule_ids)

    def test_new_table_uses_youngest_age_and_consistent_sex(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/ses-02/mr-anat/sub-01_scan_patient.json",
                {"Age": "025Y", "Sex": "F"},
            )
            _write_patient_json(
                root,
                "sub-01/ses-01/mr-anat/sub-01_scan_patient.json",
                {"Age": "024Y", "Sex": "F"},
            )

            action = create_or_populate_participants(build_inventory(root))

            self.assertEqual(action["operation"], "created")
            self.assertEqual(action["filled_demographic_cells"], 2)
            self.assertEqual(
                (root / "participants.tsv").read_text(encoding="utf-8"),
                "participant_id\tage\tsex\tgroup\nsub-01\t024Y\tF\t\n",
            )

    def test_youngest_age_comparison_handles_dicom_age_units(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/ses-01/mr-anat/sub-01_scan_patient.json",
                {"Age": "001Y"},
            )
            _write_patient_json(
                root,
                "sub-01/ses-02/mr-anat/sub-01_scan_patient.json",
                {"Age": "011M"},
            )

            create_or_populate_participants(build_inventory(root))

            self.assertIn(
                "sub-01\t011M\t\t",
                (root / "participants.tsv").read_text(encoding="utf-8"),
            )

    def test_conflicting_sex_is_not_written(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/ses-01/mr-anat/sub-01_scan_patient.json",
                {"Sex": "F"},
            )
            _write_patient_json(
                root,
                "sub-01/ses-02/mr-anat/sub-01_scan_patient.json",
                {"Sex": "M"},
            )

            create_or_populate_participants(build_inventory(root))

            self.assertEqual(
                (root / "participants.tsv").read_text(encoding="utf-8"),
                "participant_id\tage\tsex\tgroup\nsub-01\t\t\t\n",
            )

    def test_existing_nonblank_demographics_are_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/mr-anat/sub-01_scan_patient.json",
                {"Age": "024Y", "Sex": "F"},
            )
            table = root / "participants.tsv"
            table.write_text(
                "participant_id\tage\tsex\tgroup\n"
                "sub-01\t099Y\tRecorded\tcontrol\n",
                encoding="utf-8",
            )

            action = create_or_populate_participants(build_inventory(root))

            self.assertEqual(action["operation"], "unchanged")
            self.assertIn(
                "sub-01\t099Y\tRecorded\tcontrol",
                table.read_text(encoding="utf-8"),
            )

    def test_fills_blank_cells_and_adds_missing_demographic_columns(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/mr-anat/sub-01_scan_patient.json",
                {"Age": "024Y", "Sex": "F"},
            )
            table = root / "participants.tsv"
            table.write_text(
                "participant_id\tgroup\nsub-01\tcontrol\n",
                encoding="utf-8",
            )

            action = create_or_populate_participants(build_inventory(root))

            self.assertEqual(action["operation"], "populated")
            self.assertEqual(action["added_columns"], ["age", "sex"])
            self.assertEqual(action["filled_demographic_cells"], 2)
            self.assertEqual(
                table.read_text(encoding="utf-8"),
                "participant_id\tgroup\tage\tsex\nsub-01\tcontrol\t024Y\tF\n",
            )

    def test_invalid_age_string_is_not_used_for_youngest_age(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/mr-anat/sub-01_scan_patient.json",
                {"Age": "twenty-five"},
            )

            create_or_populate_participants(build_inventory(root))

            self.assertEqual(
                (root / "participants.tsv").read_text(encoding="utf-8"),
                "participant_id\tage\tsex\tgroup\nsub-01\t\t\t\n",
            )

    def test_existing_table_adds_only_columns_with_usable_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/mr-anat/sub-01_scan_patient.json",
                {"Age": "024Y"},
            )
            table = root / "participants.tsv"
            table.write_text("participant_id\nsub-01\n", encoding="utf-8")

            action = create_or_populate_participants(build_inventory(root))

            self.assertEqual(action["added_columns"], ["age"])
            self.assertEqual(
                table.read_text(encoding="utf-8"),
                "participant_id\tage\nsub-01\t024Y\n",
            )

    def test_coordinator_reuses_one_patient_metadata_collection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            _write_patient_json(
                root,
                "sub-01/mr-anat/sub-01_scan_patient.json",
                {"Age": "024Y", "Sex": "F"},
            )

            with (
                patch(
                    "omids_validator.participants.collect_patient_metadata",
                    side_effect=AssertionError("participant update recollected JSON"),
                ),
                patch(
                    "omids_validator.rules.layer5_dataset.collect_patient_metadata",
                    side_effect=AssertionError("Layer 5 recollected JSON"),
                ),
            ):
                report = validate(
                    root,
                    participants_requested=True,
                    timestamp="now",
                )

            self.assertEqual(report.actions[0]["filled_demographic_cells"], 2)
