from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column, positive_int


FEATURE_INFO = feature_info(
    "ma",
    "Moving Average",
    "trends",
    args=[
        feature_arg("col", "Source Column", "source"),
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("min_periods", "Minimum Periods", "min_periods", 1),
    ],
)


def calc_mv_avg(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int = 1,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = positive_int(min_periods, name="min_periods")
    return numeric_column(dataframe, col).rolling(
        window=resolved_window,
        min_periods=resolved_window_min_periods,
    ).mean()


def add_mv_avg(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int = 1,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_ma{window}"] = calc_mv_avg(
        dataframe,
        col=col,
        window=window,
        min_periods=min_periods,
    )
