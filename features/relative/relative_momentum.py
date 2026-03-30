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
    "rel_mom",
    "Relative Momentum",
    "relative",
    args=[
        feature_arg("rel_return", "Relative Return Column", "relative_return_source"),
        feature_arg("return", "Return Column", "return_source"),
        feature_arg(
            "benchmark_return",
            "Benchmark Return Column",
            "benchmark_return_source",
        ),
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
    ],
)


def calc_rel_momentum(
    dataframe: pd.DataFrame,
    rel_return_col: str,
    return_col: str,
    benchmark_return_col: str,
    window: int,
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    rel_return_series = numeric_column(dataframe, rel_return_col)
    return_series = numeric_column(dataframe, return_col)
    benchmark_return_series = numeric_column(dataframe, benchmark_return_col)
    tracking_volatility = (
        (return_series - benchmark_return_series)
        .rolling(resolved_window, min_periods=resolved_window_min_periods)
        .std()
        * np.sqrt(resolved_window)
    )
    return rel_return_series / tracking_volatility.replace(0.0, np.nan)


def add_rel_momentum(
    dataframe: pd.DataFrame,
    rel_return_col: str,
    return_col: str,
    benchmark_return_col: str,
    window: int,
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"{rel_return_col}_momentum"] = calc_rel_momentum(
        dataframe,
        rel_return_col=rel_return_col,
        return_col=return_col,
        benchmark_return_col=benchmark_return_col,
        window=window,
        min_periods=min_periods,
    )
