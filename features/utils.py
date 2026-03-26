from __future__ import annotations

import numpy as np
import pandas as pd

from ._shared import (
    feature_arg,
    feature_info,
    numeric_column,
    positive_int,
    resolved_min_periods,
    safe_log,
)


FEATURE_INFOS = (
    feature_info(
        "abs",
        "Absolute Value",
        "utils",
        args=[feature_arg("col", "Source Column", "source")],
    ),
    feature_info(
        "log",
        "Natural Log Value",
        "utils",
        args=[feature_arg("col", "Source Column", "source")],
    ),
    feature_info(
        "dist",
        "Log Distance Between Series",
        "utils",
        args=[
            feature_arg("col", "Source Column", "source"),
            feature_arg("reference", "Reference Column", "reference_source"),
        ],
    ),
    feature_info(
        "z",
        "Rolling Z-Score",
        "utils",
        args=[
            feature_arg("col", "Source Column", "source"),
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
            feature_arg("ddof", "Degrees of Freedom", "degrees_of_freedom", 0),
        ],
    ),
    feature_info(
        "pct_rank",
        "Rolling Percentile Rank",
        "utils",
        args=[
            feature_arg("col", "Source Column", "source"),
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
)


def calc_abs(dataframe: pd.DataFrame, col: str) -> pd.Series:
    return numeric_column(dataframe, col).abs()


def add_abs(
    dataframe: pd.DataFrame,
    col: str,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"abs_{col}"] = calc_abs(dataframe, col)


def calc_log_value(dataframe: pd.DataFrame, col: str) -> pd.Series:
    return safe_log(numeric_column(dataframe, col))


def add_log_value(
    dataframe: pd.DataFrame,
    col: str,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"log_{col}"] = calc_log_value(dataframe, col)


def calc_distance_to_col(
    dataframe: pd.DataFrame,
    col: str,
    reference_col: str,
) -> pd.Series:
    source_series = numeric_column(dataframe, col)
    reference_series = numeric_column(dataframe, reference_col)
    return np.log(source_series / reference_series)


def add_distance_to_col(
    dataframe: pd.DataFrame,
    col: str,
    reference_col: str,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_distance_to_{reference_col}"] = calc_distance_to_col(
        dataframe,
        col=col,
        reference_col=reference_col,
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


__all__ = [
    "FEATURE_INFOS",
    "add_abs",
    "add_distance_to_col",
    "add_log_value",
    "add_percentile_rank",
    "add_z_score",
    "calc_abs",
    "calc_distance_to_col",
    "calc_log_value",
    "calc_percentile_rank",
    "calc_z_score",
]
