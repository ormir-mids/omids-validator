"""Tests for safe participant-table creation and population."""

import tempfile
import unittest
from pathlib import Path

from mids_validator.inventory import build_inventory
from mids_validator.participants import create_or_populate_participants
from mids_validator.validator import validate


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
            self.assertNotIn("MIDS-501", {finding.rule_id for finding in report.findings})
