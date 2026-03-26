from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from features import (
    FEATURE_INFOS_BY_CATEGORY,
    FEATURE_INFOS_BY_SCRIPT,
    SCRIPT_FUNCTION_INFOS_BY_NAME,
    SCRIPT_PARAMETER_INFOS_BY_NAME,
    FeatureArgInfo,
    FeatureInfo,
    add_log_return,
    add_momentum,
    add_realized_vol,
    add_vwap,
    calc_day_of_week,
    calc_garman_klass_volatility,
    calc_is_holiday_adjacent,
    calc_log_value,
    calc_relative_volume_percentile,
    search_features,
)


class FeaturePackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.price_dataframe = pd.DataFrame(
            {
                "date": pd.date_range("2024-07-01 09:30:00", periods=12, freq="h"),
                "open": [100, 101, 102, 103, 104, 105, 106, 105, 107, 108, 109, 110],
                "high": [101, 102, 103, 104, 105, 106, 107, 107, 108, 109, 110, 111],
                "low": [99, 100, 101, 102, 103, 104, 105, 104, 106, 107, 108, 109],
                "close": [100.5, 101.5, 102.5, 103.5, 104.5, 105.5, 105.0, 106.5, 107.5, 108.5, 109.5, 110.5],
                "volume": [1000, 1100, 1200, 1300, 1400, 1500, 1450, 1600, 1700, 1800, 1900, 2000],
            }
        )

    def test_feature_registry_exposes_new_categories(self) -> None:
        self.assertIn("gk_vlt", FEATURE_INFOS_BY_SCRIPT)
        self.assertEqual(FEATURE_INFOS_BY_SCRIPT["rsi"].category, "momentum")
        self.assertIn("calendar", FEATURE_INFOS_BY_CATEGORY)
        self.assertIn("candles", FEATURE_INFOS_BY_CATEGORY)
        self.assertIsInstance(FEATURE_INFOS_BY_SCRIPT["rsi"], FeatureInfo)
        self.assertTrue(FEATURE_INFOS_BY_SCRIPT["rsi"].args)
        self.assertIsInstance(FEATURE_INFOS_BY_SCRIPT["rsi"].args[0], FeatureArgInfo)
        self.assertEqual(FEATURE_INFOS_BY_SCRIPT["rsi"].args[0].script_name, "col")
        self.assertEqual(FEATURE_INFOS_BY_SCRIPT["rsi"].args[0].arg_type, "source")
        self.assertEqual(FEATURE_INFOS_BY_SCRIPT["rsi"].args[0].default_value, "close")
        self.assertEqual(FEATURE_INFOS_BY_SCRIPT["rsi"].args[1].default_value, 14)
        self.assertEqual(FEATURE_INFOS_BY_SCRIPT["rsi"].offset_arg.script_name, "offset")
        self.assertEqual(FEATURE_INFOS_BY_SCRIPT["rsi"].offset_arg.default_value, 0)
        self.assertEqual(FEATURE_INFOS_BY_SCRIPT["rsi"].all_args[-1].script_name, "offset")
        self.assertNotIn("offset", {arg.script_name for arg in FEATURE_INFOS_BY_SCRIPT["rsi"].args})

    def test_script_function_metadata_reuses_feature_info(self) -> None:
        self.assertEqual(
            SCRIPT_FUNCTION_INFOS_BY_NAME["mv_avg"].full_name,
            FEATURE_INFOS_BY_SCRIPT["ma"].full_name,
        )
        self.assertEqual(
            SCRIPT_FUNCTION_INFOS_BY_NAME["realized_vol"].full_name,
            FEATURE_INFOS_BY_SCRIPT["vlt"].full_name,
        )
        self.assertEqual(
            SCRIPT_PARAMETER_INFOS_BY_NAME["window"].full_name,
            "Lookback Window",
        )
        self.assertEqual(
            SCRIPT_FUNCTION_INFOS_BY_NAME["rel_momentum"].signatures[-1][-1],
            "min_periods",
        )
        self.assertIn(
            ("open", "close"),
            SCRIPT_FUNCTION_INFOS_BY_NAME["body_pct"].signatures,
        )
        self.assertIn(
            ("window", "open", "high", "low", "close"),
            SCRIPT_FUNCTION_INFOS_BY_NAME["gk_vlt"].signatures,
        )
        self.assertIn(
            ("timestamp",),
            SCRIPT_FUNCTION_INFOS_BY_NAME["dow"].signatures,
        )

    def test_calendar_features_return_integer_values(self) -> None:
        calendar_dataframe = pd.DataFrame(
            {
                "date": pd.to_datetime(
                    ["2024-07-03 09:30:00", "2024-07-04 09:30:00", "2024-07-05 09:30:00"]
                )
            }
        )

        day_of_week = calc_day_of_week(calendar_dataframe)
        holiday_adjacent = calc_is_holiday_adjacent(calendar_dataframe)

        self.assertEqual(str(day_of_week.dtype), "Int64")
        self.assertListEqual(day_of_week.tolist(), [2, 3, 4])
        self.assertListEqual(holiday_adjacent.tolist(), [1, 0, 1])

    def test_garman_klass_and_relative_volume_features_produce_numeric_output(self) -> None:
        garman_klass = calc_garman_klass_volatility(self.price_dataframe, window=3)
        relative_volume = calc_relative_volume_percentile(self.price_dataframe, window=3)

        self.assertTrue(np.isfinite(garman_klass.iloc[-1]))
        self.assertGreaterEqual(relative_volume.iloc[-1], 0.0)
        self.assertLessEqual(relative_volume.iloc[-1], 100.0)

    def test_features_can_be_composed_for_multi_day_indicators(self) -> None:
        transformed = self.price_dataframe[["date", "close", "volume"]].copy()
        transformed["timestamp"] = transformed["date"]
        transformed["trading_day"] = transformed["timestamp"].dt.normalize()
        transformed["log_close"] = calc_log_value(transformed, "close")
        add_log_return(
            transformed,
            "log_close",
            1,
            output_col="log_return_1h",
        )
        add_log_return(
            transformed,
            "log_close",
            2,
            output_col="log_return_1d",
        )
        add_realized_vol(
            transformed,
            "log_return_1h",
            2,
            output_col="realized_vol_1d",
            min_periods=2,
        )
        add_momentum(
            transformed,
            "log_return_1d",
            "realized_vol_1d",
            output_col="momentum_1d",
        )
        add_vwap(
            transformed,
            2,
            output_col="vwap_1d",
            min_periods=2,
        )

        self.assertIn("vwap_1d", transformed.columns)
        self.assertIn("momentum_1d", transformed.columns)
        self.assertTrue(np.isfinite(transformed["momentum_1d"].iloc[-1]))

    def test_search_features_prioritizes_exact_script_name_matches(self) -> None:
        matches = search_features("rsi")

        self.assertEqual(matches[0].script_name, "rsi")
        self.assertLessEqual(len(matches), 3)

    def test_search_features_matches_full_name_words(self) -> None:
        matches = search_features("garman klass", n=5)

        self.assertTrue(matches)
        self.assertEqual(matches[0].script_name, "gk_vlt")

    def test_search_features_handles_empty_queries(self) -> None:
        self.assertEqual(search_features("   "), [])


if __name__ == "__main__":
    unittest.main()
