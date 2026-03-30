from __future__ import annotations

import pandas as pd

from .._shared import (
    feature_arg,
    feature_info,
    numeric_column,
    positive_int,
    resolved_min_periods,
)


FEATURE_INFO = feature_info(
    "pct_rank",
    "Rolling Percentile Rank",
    "utils",
    args=[
        feature_arg("col", "Source Column", "source"),
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
    ],
)


def calc_percentile_rank(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    return (
        numeric_column(dataframe, col)
        .rolling(resolved_window, min_periods=resolved_window_min_periods)
        .rank(pct=True)
        .mul(100.0)
    )


def add_percentile_rank(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"{col}_pct_rank{window}"] = calc_percentile_rank(
        dataframe,
        col=col,
        window=window,
        min_periods=min_periods,
    )
