from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, wilder_mean
from .true_range import calc_true_range


FEATURE_INFO = feature_info(
    "atr",
    "Average True Range",
    "volatility",
    args=[
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("close", "Close Column", "close_source", "close"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
    ],
)


def calc_atr(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    min_periods: int | None = None,
) -> pd.Series:
    true_range = calc_true_range(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
    )
    return wilder_mean(true_range, window, min_periods=min_periods)


def add_atr(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"atr{window}"] = calc_atr(
        dataframe,
        window=window,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        min_periods=min_periods,
    )
