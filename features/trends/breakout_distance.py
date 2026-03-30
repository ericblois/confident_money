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
    "brk_dist",
    "Breakout Distance",
    "trends",
    args=[
        feature_arg("col", "Source Column", "source"),
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
    ],
)


def calc_breakout_distance(
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
    source_series = numeric_column(dataframe, col)
    prior_window_high = source_series.shift(1).rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).max()
    return np.log(source_series / prior_window_high)


def add_breakout_distance(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"{col}_breakout_distance{window}"] = calc_breakout_distance(
        dataframe,
        col=col,
        window=window,
        min_periods=min_periods,
    )
