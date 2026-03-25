from __future__ import annotations

import unittest

import numpy as np
import pandas as pd

from features import (
    FEATURE_INFOS_BY_CATEGORY,
    FEATURE_INFOS_BY_SCRIPT,
    FeatureArgInfo,
    FeatureInfo,
    add_hourly_momentum_columns,
    calc_day_of_week,
    calc_garman_klass_volatility,
    calc_is_holiday_adjacent,
    calc_relative_volume_percentile,
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

    def test_hourly_momentum_transform_still_adds_expected_columns(self) -> None:
        transformed = add_hourly_momentum_columns(
            self.price_dataframe[["date", "close", "volume"]],
            market_dataframe=self.price_dataframe[["date", "close", "volume"]],
            lookback_days={"1d": 1},
            vwap_days=(1,),
        )

        self.assertIn("vwap_1d", transformed.columns)
        self.assertIn("momentum_1d", transformed.columns)
        self.assertIn("market_rel_momentum_1d", transformed.columns)


if __name__ == "__main__":
    unittest.main()
