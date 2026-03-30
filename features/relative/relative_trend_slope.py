from __future__ import annotations

import pandas as pd

from .._shared import (
    feature_arg,
    feature_info,
    numeric_column,
    positive_int,
    rolling_trend_stats,
)


FEATURE_INFO = feature_info(
    "rel_trend_slp",
    "Relative Trend Slope",
    "relative",
    args=[
        feature_arg("col", "Source Column", "source"),
        feature_arg("benchmark", "Benchmark Column", "benchmark_source"),
        feature_arg("window", "Lookback Periods", "periods"),
    ],
)


def calc_rel_trend_slope(
    dataframe: pd.DataFrame,
    col: str,
    benchmark_col: str,
    window: int,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    source_series = numeric_column(dataframe, col)
    benchmark_series = numeric_column(dataframe, benchmark_col)
    slope, _ = rolling_trend_stats(source_series - benchmark_series, resolved_window)
    return slope


def add_rel_trend_slope(
    dataframe: pd.DataFrame,
    col: str,
    benchmark_col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_rel_trend_slope{window}"] = calc_rel_trend_slope(
        dataframe,
        col=col,
        benchmark_col=benchmark_col,
        window=window,
    )
