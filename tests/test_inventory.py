"""Tests for dataset inventory navigation."""

import tempfile
import unittest
from pathlib import Path

from mids_validator.inventory import build_inventory


class DatasetInventoryTests(unittest.TestCase):
    """Test navigation through a built dataset inventory."""

    def test_subject_session_and_datatype_navigation(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            direct_datatype = root / "sub-01" / "mr-anat"
            session_datatype = root / "sub-02" / "ses-01" / "ct"
            direct_datatype.mkdir(parents=True)
            session_datatype.mkdir(parents=True)

            inventory = build_inventory(root)
            subjects = inventory.subject_directories()
            resolved_direct_datatype = inventory.root / "sub-01" / "mr-anat"
            resolved_session = inventory.root / "sub-02" / "ses-01"
            resolved_session_datatype = resolved_session / "ct"

            self.assertEqual(
                tuple(subject.name for subject in subjects),
                ("sub-01", "sub-02"),
            )
            self.assertEqual(
                inventory.datatype_directories(subjects[0]),
                (resolved_direct_datatype,),
            )
            self.assertEqual(
                inventory.session_directories(subjects[1]),
                (resolved_session,),
            )
            self.assertEqual(
                inventory.datatype_directories(subjects[1]),
                (resolved_session_datatype,),
            )
            self.assertEqual(
                inventory.relative_path(resolved_session_datatype),
                "sub-02/ses-01/ct",
            )

    def test_added_item_updates_children_without_mutating_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "sub-01").mkdir()
            inventory = build_inventory(root)
            participant_table = inventory.root / "participants.tsv"

            updated_inventory = inventory.with_added_item(participant_table)

            self.assertNotIn(participant_table, inventory.root_items)
            self.assertIn(participant_table, updated_inventory.root_items)
            self.assertEqual(
                updated_inventory.children(updated_inventory.root),
                updated_inventory.root_items,
            )


if __name__ == "__main__":
    unittest.main()
