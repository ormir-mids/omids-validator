"""Tests for human-readable rule catalogue generation."""

import tempfile
import unittest
from pathlib import Path

from omids_validator.rules_document import (
    render_rules_markdown,
    write_rules_markdown,
)


class RulesDocumentTests(unittest.TestCase):
    def test_render_includes_catalogue_metadata_and_all_rule_layers(self) -> None:
        markdown = render_rules_markdown()

        self.assertIn("Generated from the packaged rules.json", markdown)
        self.assertIn("schema version 1.0", markdown)
        for layer in range(6):
            self.assertIn(f"## Layer {layer}:", markdown)

    def test_severity_definitions_match_project_conventions(self) -> None:
        markdown = render_rules_markdown()

        self.assertIn(
            "A convention violation likely to cause problems in downstream "
            "pipelines or prevent data and code from being interoperable",
            markdown,
        )
        self.assertIn(
            "A probable problem or important inconsistency that the user "
            "should review and probably fix.",
            markdown,
        )

    def test_rules_are_ordered_numerically(self) -> None:
        markdown = render_rules_markdown()

        self.assertLess(
            markdown.index("### MIDS-009"),
            markdown.index("### MIDS-101"),
        )
        self.assertLess(
            markdown.index("### MIDS-503"),
            markdown.index("### MIDS-504"),
        )

    def test_command_tool_and_review_guidance_are_distinct(self) -> None:
        markdown = render_rules_markdown()

        self.assertIn("**Tool:** `dcm2omids`", markdown)
        self.assertIn(
            "**Command:** `omids_validator DATASET --participants`",
            markdown,
        )
        self.assertIn("- **Response type:** review", markdown)

    def test_status_is_hidden_and_deferred_rules_are_excluded(self) -> None:
        markdown = render_rules_markdown()

        self.assertNotIn("**Status:**", markdown)
        self.assertNotIn("### MIDS-302", markdown)
        self.assertEqual(markdown.count("### MIDS-"), 31)

    def test_glossary_explains_dataset_structure_terms(self) -> None:
        markdown = render_rules_markdown()

        self.assertIn("## Glossary", markdown)
        self.assertIn("**Session directory:**", markdown)
        self.assertIn("**Datatype directory:**", markdown)
        self.assertIn("**Direct-datatype layout:**", markdown)

    def test_write_matches_rendered_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "rules.md"

            write_rules_markdown(path)

            self.assertEqual(
                path.read_text(encoding="utf-8"),
                render_rules_markdown(),
            )


if __name__ == "__main__":
    unittest.main()
