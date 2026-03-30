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
    "rvol_pct",
    "Relative Volume Percentile",
    "volume",
    args=[
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("volume", "Volume Column", "volume_source", "volume"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
    ],
)


def calc_relative_volume_percentile(
    dataframe: pd.DataFrame,
    window: int,
    volume_col: str = "volume",
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    return (
        numeric_column(dataframe, volume_col)
        .rolling(resolved_window, min_periods=resolved_window_min_periods)
        .rank(pct=True)
        .mul(100.0)
    )


def add_relative_volume_percentile(
    dataframe: pd.DataFrame,
    window: int,
    volume_col: str = "volume",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[
        output_col or f"{volume_col}_rvol_pct{window}"
    ] = calc_relative_volume_percentile(
        dataframe,
        window=window,
        volume_col=volume_col,
        min_periods=min_periods,
    )
