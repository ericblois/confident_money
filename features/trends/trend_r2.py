from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column, rolling_trend_stats


FEATURE_INFO = feature_info(
    "trend_r2",
    "Trend R-Squared",
    "trends",
    args=[
        feature_arg("col", "Source Column", "source"),
        feature_arg("window", "Lookback Periods", "periods"),
    ],
)


def calc_trend_r2(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
) -> pd.Series:
    _, r_squared = rolling_trend_stats(numeric_column(dataframe, col), window)
    return r_squared


def add_trend_r2(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_trend_r2{window}"] = calc_trend_r2(
        dataframe,
        col=col,
        window=window,
    )
