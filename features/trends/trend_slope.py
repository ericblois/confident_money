from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column, rolling_trend_stats


FEATURE_INFO = feature_info(
    "trend_slp",
    "Trend Slope",
    "trends",
    args=[
        feature_arg("col", "Source Column", "source"),
        feature_arg("window", "Lookback Periods", "periods"),
    ],
)


def calc_trend_slope(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
) -> pd.Series:
    slope, _ = rolling_trend_stats(numeric_column(dataframe, col), window)
    return slope


def add_trend_slope(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_trend_slope{window}"] = calc_trend_slope(
        dataframe,
        col=col,
        window=window,
    )
