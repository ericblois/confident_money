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
    "z",
    "Rolling Z-Score",
    "utils",
    args=[
        feature_arg("col", "Source Column", "source"),
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
        feature_arg("ddof", "Degrees of Freedom", "degrees_of_freedom", 0),
    ],
)


def calc_z_score(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int | None = None,
    ddof: int = 0,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    source_series = numeric_column(dataframe, col)
    rolling_mean = source_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).mean()
    rolling_std = source_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).std(ddof=ddof)
    return (source_series - rolling_mean) / rolling_std.replace(0.0, np.nan)


def add_z_score(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
    min_periods: int | None = None,
    ddof: int = 0,
) -> None:
    dataframe[output_col or f"{col}_zscore{window}"] = calc_z_score(
        dataframe,
        col=col,
        window=window,
        min_periods=min_periods,
        ddof=ddof,
    )
