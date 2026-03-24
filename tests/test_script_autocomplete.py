from __future__ import annotations

import unittest

from condition_script import get_default_function_registry
from condition_script.types import build_script_autocomplete_entries
from gui.script_box import (
    _extract_signature_context,
    build_signature_hint_html,
    get_script_autocomplete_suggestions,
)


class ScriptAutocompleteTests(unittest.TestCase):
    def setUp(self) -> None:
        function_registry = get_default_function_registry()
        self.function_definitions = {
            name: runtime_function.definition
            for name, runtime_function in function_registry.items()
        }
        self.entries = build_script_autocomplete_entries(
            self.function_definitions.values()
        )

    def test_autocomplete_catalog_includes_full_names_for_functions_and_parameters(self) -> None:
        entry_map = {
            (entry.kind, entry.short_name): entry
            for entry in self.entries
        }

        self.assertEqual(entry_map[("function", "mv_avg")].full_name, "Moving Average")
        self.assertEqual(
            entry_map[("function", "rel_trend_r2")].full_name,
            "Relative Trend R-Squared",
        )
        self.assertEqual(entry_map[("parameter", "window")].full_name, "Lookback Window")
        self.assertEqual(entry_map[("parameter", "price")].full_name, "Price Series")
        self.assertEqual(entry_map[("parameter", "open")].full_name, "Opening Price")
        self.assertEqual(entry_map[("parameter", "high")].full_name, "High Price")
        self.assertEqual(entry_map[("parameter", "low")].full_name, "Low Price")
        self.assertEqual(entry_map[("parameter", "close")].full_name, "Closing Price")

    def test_autocomplete_entries_expose_kind_in_subtitle(self) -> None:
        entry_map = {
            (entry.kind, entry.short_name): entry
            for entry in self.entries
        }

        self.assertEqual(
            entry_map[("function", "mv_avg")].subtitle,
            "Function • Moving Average",
        )
        self.assertEqual(
            entry_map[("parameter", "close")].subtitle,
            "Parameter • Closing Price",
        )

    def test_autocomplete_matches_on_short_name_prefix(self) -> None:
        suggestions = get_script_autocomplete_suggestions(self.entries, "vw")

        self.assertEqual([entry.short_name for entry in suggestions], ["vwap"])

    def test_autocomplete_matches_on_full_name_words(self) -> None:
        suggestions = get_script_autocomplete_suggestions(self.entries, "moving")

        self.assertEqual(
            [entry.short_name for entry in suggestions[:2]],
            ["moving_avg", "mv_avg"],
        )

    def test_autocomplete_is_limited_to_three_suggestions(self) -> None:
        suggestions = get_script_autocomplete_suggestions(self.entries, "r")

        self.assertEqual(len(suggestions), 3)

    def test_signature_context_tracks_current_argument(self) -> None:
        signature_context = _extract_signature_context(
            "mv_avg(close, 20",
            len("mv_avg(close, 20"),
            self.function_definitions,
        )

        self.assertIsNotNone(signature_context)
        self.assertEqual(signature_context.function_definition.name, "mv_avg")
        self.assertEqual(signature_context.current_argument_index, 1)

    def test_signature_hint_bolds_active_argument(self) -> None:
        signature_context = _extract_signature_context(
            "vwap(close, volume, ",
            len("vwap(close, volume, "),
            self.function_definitions,
        )

        self.assertIsNotNone(signature_context)
        hint_html = build_signature_hint_html(signature_context)
        self.assertIn("<b>volume</b>", hint_html)
        self.assertIn("vwap", hint_html)


if __name__ == "__main__":
    unittest.main()
