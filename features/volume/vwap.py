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
    "vwap",
    "Volume Weighted Average Price",
    "volume",
    args=[
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("price", "Price Column", "price_source", "close"),
        feature_arg("volume", "Volume Column", "volume_source", "volume"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
    ],
)


def calc_vwap(
    dataframe: pd.DataFrame,
    window: int,
    price_col: str = "close",
    volume_col: str = "volume",
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    price_series = numeric_column(dataframe, price_col)
    volume_series = numeric_column(dataframe, volume_col)
    rolling_volume = volume_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).sum()
    return (
        (price_series * volume_series)
        .rolling(resolved_window, min_periods=resolved_window_min_periods)
        .sum()
        / rolling_volume.replace(0.0, np.nan)
    )


def add_vwap(
    dataframe: pd.DataFrame,
    window: int,
    price_col: str = "close",
    volume_col: str = "volume",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"{price_col}_vwap{window}"] = calc_vwap(
        dataframe,
        window=window,
        price_col=price_col,
        volume_col=volume_col,
        min_periods=min_periods,
    )
