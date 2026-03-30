from __future__ import annotations

import unittest

from condition_script import get_default_function_definitions, get_default_function_registry
from condition_script.autocomplete import (
    build_signature_hint_html,
    extract_signature_context,
    get_default_autocomplete_entries,
    get_script_autocomplete_suggestions,
)
from condition_script.types import build_script_autocomplete_entries


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

    def test_default_autocomplete_entries_match_default_function_catalog(self) -> None:
        self.assertEqual(
            get_default_autocomplete_entries(),
            build_script_autocomplete_entries(get_default_function_definitions()),
        )

    def test_autocomplete_catalog_includes_full_names_for_functions_parameters_and_operators(
        self,
    ) -> None:
        entry_map = {
            (entry.kind, entry.short_name): entry
            for entry in self.entries
        }

        self.assertEqual(
            entry_map[("function", "gk_vlt")].full_name,
            "Garman-Klass Volatility",
        )
        self.assertEqual(entry_map[("function", "mv_avg")].full_name, "Moving Average")
        self.assertEqual(
            entry_map[("function", "rel_trend_r2")].full_name,
            "Relative Trend R-Squared",
        )
        self.assertEqual(entry_map[("parameter", "window")].full_name, "Lookback Window")
        self.assertEqual(entry_map[("parameter", "price")].full_name, "Price Series")
        self.assertEqual(entry_map[("parameter", "source")].full_name, "Source Series")
        self.assertEqual(entry_map[("parameter", "volume")].full_name, "Volume Series")
        self.assertEqual(
            entry_map[("operator", "crosses")].full_name,
            "Crosses Above",
        )

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
            entry_map[("parameter", "source")].subtitle,
            "Parameter • Source Series",
        )
        self.assertEqual(
            entry_map[("operator", "crosses")].subtitle,
            "Operator • Crosses Above",
        )
        self.assertEqual(
            entry_map[("operator", "crosses")].insert_kind,
            "operator",
        )

    def test_autocomplete_only_includes_parameters_used_by_current_registry(self) -> None:
        parameter_names = {
            entry.short_name
            for entry in self.entries
            if entry.kind == "parameter"
        }

        self.assertIn("open", parameter_names)
        self.assertIn("high", parameter_names)
        self.assertIn("low", parameter_names)
        self.assertIn("close", parameter_names)
        self.assertIn("timestamp", parameter_names)
        self.assertNotIn("open_col", parameter_names)
        self.assertNotIn("close_col", parameter_names)
        self.assertNotIn("timestamp_col", parameter_names)

    def test_autocomplete_matches_on_short_name_prefix(self) -> None:
        suggestions = get_script_autocomplete_suggestions(self.entries, "vw")

        self.assertEqual([entry.short_name for entry in suggestions], ["vwap"])

    def test_autocomplete_includes_script_operators(self) -> None:
        suggestions = get_script_autocomplete_suggestions(self.entries, "cro")

        self.assertEqual([entry.short_name for entry in suggestions], ["crosses"])

    def test_autocomplete_includes_feature_script_names(self) -> None:
        suggestions = get_script_autocomplete_suggestions(self.entries, "gk")

        self.assertEqual([entry.short_name for entry in suggestions], ["gk_vlt"])

    def test_autocomplete_matches_on_full_name_words(self) -> None:
        suggestions = get_script_autocomplete_suggestions(self.entries, "moving")

        suggestion_names = [entry.short_name for entry in suggestions]

        self.assertEqual(suggestion_names[0], "moving_avg")
        self.assertIn("ma", suggestion_names)

    def test_autocomplete_is_limited_to_three_suggestions(self) -> None:
        suggestions = get_script_autocomplete_suggestions(self.entries, "r")

        self.assertEqual(len(suggestions), 3)

    def test_signature_context_tracks_current_argument(self) -> None:
        signature_context = extract_signature_context(
            "mv_avg(close, 20",
            len("mv_avg(close, 20"),
            self.function_definitions,
        )

        self.assertIsNotNone(signature_context)
        self.assertEqual(signature_context.function_definition.name, "mv_avg")
        self.assertEqual(signature_context.current_argument_index, 1)

    def test_signature_hint_bolds_active_argument(self) -> None:
        signature_context = extract_signature_context(
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
