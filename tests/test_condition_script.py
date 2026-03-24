from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from condition_script import add_condition_column, evaluate_expression, parse_condition
from condition_script.types import BOOLEAN


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

    def test_quoted_source_arguments_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_condition("mv_avg('close', 2) > close")


if __name__ == "__main__":
    unittest.main()
