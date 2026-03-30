from __future__ import annotations

import numpy as np
import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column


FEATURE_INFO = feature_info(
    "low_wick",
    "Lower Wick Ratio",
    "candles",
    args=[
        feature_arg("open", "Open Column", "open_source", "open"),
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("close", "Close Column", "close_source", "close"),
    ],
)


def calc_lower_wick_ratio(
    dataframe: pd.DataFrame,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
) -> pd.Series:
    open_series = numeric_column(dataframe, open_col)
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    close_series = numeric_column(dataframe, close_col)
    candle_range = high_series - low_series
    return (pd.concat([open_series, close_series], axis=1).min(axis=1) - low_series) / candle_range.replace(
        0.0,
        np.nan,
    )


def add_lower_wick_ratio(
    dataframe: pd.DataFrame,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "lower_wick_ratio"] = calc_lower_wick_ratio(
        dataframe,
        open_col=open_col,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
    )
