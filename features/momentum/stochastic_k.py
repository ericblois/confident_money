from __future__ import annotations

import numpy as np
import pandas as pd

from .._shared import (
    feature_arg,
    feature_info,
    numeric_column,
    positive_int,
    resolved_min_periods,
)


FEATURE_INFO = feature_info(
    "stoch_k",
    "Stochastic %K",
    "momentum",
    args=[
        feature_arg("window", "Lookback Periods", "periods", 14),
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("close", "Close Column", "close_source", "close"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
    ],
)


def calc_stoch_k(
    dataframe: pd.DataFrame,
    window: int = 14,
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
    close_series = numeric_column(dataframe, close_col)
    rolling_high = high_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).max()
    rolling_low = low_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).min()
    return 100.0 * (close_series - rolling_low) / (rolling_high - rolling_low).replace(0.0, np.nan)


def add_stoch_k(
    dataframe: pd.DataFrame,
    window: int = 14,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"stoch_k{window}"] = calc_stoch_k(
        dataframe,
        window=window,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        min_periods=min_periods,
    )
