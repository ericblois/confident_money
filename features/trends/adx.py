from __future__ import annotations

import numpy as np
import pandas as pd

from .._shared import (
    feature_arg,
    feature_info,
    numeric_column,
    positive_int,
    resolved_min_periods,
    wilder_mean,
)
from ..volatility import calc_true_range


FEATURE_INFO = feature_info(
    "adx",
    "Average Directional Index",
    "trends",
    args=[
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("close", "Close Column", "close_source", "close"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
    ],
)


def calc_adx(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    up_move = high_series.diff()
    down_move = -low_series.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)
    atr = wilder_mean(
        calc_true_range(
            dataframe,
            high_col=high_col,
            low_col=low_col,
            close_col=close_col,
        ),
        resolved_window,
        min_periods=resolved_window_min_periods,
    )
    plus_di = 100.0 * wilder_mean(
        plus_dm,
        resolved_window,
        min_periods=resolved_window_min_periods,
    ) / atr.replace(0.0, np.nan)
    minus_di = 100.0 * wilder_mean(
        minus_dm,
        resolved_window,
        min_periods=resolved_window_min_periods,
    ) / atr.replace(0.0, np.nan)
    directional_spread = (plus_di - minus_di).abs()
    directional_sum = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * directional_spread / directional_sum
    return wilder_mean(dx, resolved_window, min_periods=resolved_window_min_periods)


def add_adx(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"adx{window}"] = calc_adx(
        dataframe,
        window=window,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        min_periods=min_periods,
    )
