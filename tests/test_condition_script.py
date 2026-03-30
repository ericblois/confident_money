from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from condition_script import (
    add_condition_column,
    collect_script_feature_calls,
    evaluate_expression,
    parse_condition,
)
from condition_script.types import BOOLEAN
from features import (
    calc_body_pct,
    calc_breakout_distance,
    calc_distance_to_col,
    calc_ema,
    calc_garman_klass_volatility,
)


class ConditionScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.dataframe = pd.DataFrame(
            {
                "close": [10.0, 11.0, 12.0, 13.0, 12.0, 11.0],
                "volume": [1000.0, 900.0, 800.0, 700.0, 600.0, 500.0],
                "open": [9.5, 10.5, 11.5, 12.5, 12.5, 11.5],
                "high": [10.5, 11.5, 12.5, 13.5, 12.5, 11.5],
                "low": [9.0, 10.0, 11.0, 12.0, 11.5, 10.5],
            }
        )

    def test_parse_condition_returns_boolean_expression(self) -> None:
        expression = parse_condition(
            "mv_avg(close, 2) > mv_avg(close, 3) and (close > 11 or volume < 750)"
        )

        self.assertIs(expression.value_type, BOOLEAN)

    def test_crosses_operator_returns_boolean_expression(self) -> None:
        expression = parse_condition("close crosses ema(close, 3)")

        self.assertIs(expression.value_type, BOOLEAN)

    def test_add_condition_column_matches_expected_mask(self) -> None:
        script = "mv_avg(close, 2) > mv_avg(close, 3) and (close > 11 or volume < 750)"

        result = add_condition_column(self.dataframe, script)

        expected = (
            (
                self.dataframe["close"].rolling(window=2, min_periods=1).mean()
                > self.dataframe["close"].rolling(window=3, min_periods=1).mean()
            )
            & ((self.dataframe["close"] > 11) | (self.dataframe["volume"] < 750))
        ).fillna(False)

        pd.testing.assert_series_equal(
            result["condition"],
            expected.astype(bool).rename("condition"),
        )

    def test_nested_functions_evaluate_like_pandas(self) -> None:
        result = evaluate_expression(self.dataframe, "mv_avg(vlt(3), 2)")

        expected = (
            np.log(self.dataframe["close"])
            .diff()
            .rolling(window=3, min_periods=3)
            .std()
            .mul(np.sqrt(3))
            .rolling(window=2, min_periods=1)
            .mean()
        )

        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_crosses_operator_only_triggers_on_the_cross_above_bar(self) -> None:
        result = add_condition_column(self.dataframe, "close crosses ema(close, 3)")
        ema = calc_ema(self.dataframe, "close", span=3)
        expected = (
            self.dataframe["close"].gt(ema)
            & self.dataframe["close"].shift(1).le(ema.shift(1))
        ).fillna(False)

        pd.testing.assert_series_equal(
            result["condition"],
            expected.astype(bool).rename("condition"),
        )

    def test_feature_script_functions_are_available_in_conditions(self) -> None:
        result = evaluate_expression(self.dataframe, "gk_vlt(3)")
        expected = calc_garman_klass_volatility(self.dataframe, 3)

        pd.testing.assert_series_equal(result, expected, check_names=False)

    def test_feature_functions_accept_clean_column_argument_names(self) -> None:
        result = evaluate_expression(self.dataframe, "body_pct(open, close)")

        pd.testing.assert_series_equal(
            result,
            calc_body_pct(self.dataframe, "open", "close"),
            check_names=False,
        )

    def test_aliases_delegate_to_feature_calculators(self) -> None:
        distance = evaluate_expression(self.dataframe, "distance(close, open)")
        breakout_distance = evaluate_expression(self.dataframe, "breakout_distance(close, 3)")

        pd.testing.assert_series_equal(
            distance,
            calc_distance_to_col(self.dataframe, "close", "open"),
            check_names=False,
        )
        pd.testing.assert_series_equal(
            breakout_distance,
            calc_breakout_distance(self.dataframe, "close", 3),
            check_names=False,
        )

    def test_quoted_source_arguments_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_condition("mv_avg('close', 2) > close")

    def test_collect_script_feature_calls_tracks_nested_and_parameterized_calls(self) -> None:
        feature_calls = collect_script_feature_calls(
            "mv_avg(vlt(3), 2) > vlt(3) and vwap(20) > vwap(60)"
        )

        self.assertEqual(
            [feature_call.rendered_call for feature_call in feature_calls],
            ["vlt(3)", "mv_avg(vlt(3), 2)", "vwap(20)", "vwap(60)"],
        )
        self.assertEqual(
            [feature_call.feature_name for feature_call in feature_calls],
            ["vlt", "ma", "vwap", "vwap"],
        )


if __name__ == "__main__":
    unittest.main()
