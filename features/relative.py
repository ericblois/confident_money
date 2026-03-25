from __future__ import annotations

import numpy as np
import pandas as pd

from ._shared import (
    feature_arg,
    feature_info,
    numeric_column,
    positive_int,
    resolved_min_periods,
    rolling_trend_stats,
)


FEATURE_INFOS = (
    feature_info(
        "rel_ret",
        "Relative Return",
        "relative",
        args=[
            feature_arg("return_col", "Return Column", "return_source"),
            feature_arg("benchmark_col", "Benchmark Column", "benchmark_source"),
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("benchmark_is_return", "Benchmark Is Return", "boolean_flag", False),
        ],
    ),
    feature_info(
        "rel_mom",
        "Relative Momentum",
        "relative",
        args=[
            feature_arg("rel_return_col", "Relative Return Column", "relative_return_source"),
            feature_arg("return_col", "Return Column", "return_source"),
            feature_arg(
                "benchmark_return_col",
                "Benchmark Return Column",
                "benchmark_return_source",
            ),
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
    feature_info(
        "rel_trend_slp",
        "Relative Trend Slope",
        "relative",
        args=[
            feature_arg("col", "Source Column", "source"),
            feature_arg("benchmark_col", "Benchmark Column", "benchmark_source"),
            feature_arg("window", "Lookback Periods", "periods"),
        ],
    ),
    feature_info(
        "rel_trend_r2",
        "Relative Trend R-Squared",
        "relative",
        args=[
            feature_arg("col", "Source Column", "source"),
            feature_arg("benchmark_col", "Benchmark Column", "benchmark_source"),
            feature_arg("window", "Lookback Periods", "periods"),
        ],
    ),
)


def calc_rel_return(
    dataframe: pd.DataFrame,
    return_col: str,
    benchmark_col: str,
    window: int,
    benchmark_is_return: bool = False,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    return_series = numeric_column(dataframe, return_col)
    benchmark_series = numeric_column(dataframe, benchmark_col)
    if benchmark_is_return:
        return return_series - benchmark_series
    return return_series - benchmark_series.diff(resolved_window)


def add_rel_return(
    dataframe: pd.DataFrame,
    return_col: str,
    benchmark_col: str,
    window: int,
    output_col: str | None = None,
    benchmark_is_return: bool = False,
) -> None:
    dataframe[output_col or f"{return_col}_rel_to_{benchmark_col}"] = calc_rel_return(
        dataframe,
        return_col=return_col,
        benchmark_col=benchmark_col,
        window=window,
        benchmark_is_return=benchmark_is_return,
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


def calc_rel_trend_r2(
    dataframe: pd.DataFrame,
    col: str,
    benchmark_col: str,
    window: int,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    source_series = numeric_column(dataframe, col)
    benchmark_series = numeric_column(dataframe, benchmark_col)
    _, r_squared = rolling_trend_stats(source_series - benchmark_series, resolved_window)
    return r_squared


def add_rel_trend_r2(
    dataframe: pd.DataFrame,
    col: str,
    benchmark_col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_rel_trend_r2{window}"] = calc_rel_trend_r2(
        dataframe,
        col=col,
        benchmark_col=benchmark_col,
        window=window,
    )


__all__ = [
    "FEATURE_INFOS",
    "add_rel_momentum",
    "add_rel_return",
    "add_rel_trend_r2",
    "add_rel_trend_slope",
    "calc_rel_momentum",
    "calc_rel_return",
    "calc_rel_trend_r2",
    "calc_rel_trend_slope",
]
