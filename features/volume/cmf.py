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
    "cmf",
    "Chaikin Money Flow",
    "volume",
    args=[
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("close", "Close Column", "close_source", "close"),
        feature_arg("volume", "Volume Column", "volume_source", "volume"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
    ],
)


def calc_cmf(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    close_series = numeric_column(dataframe, close_col)
    volume_series = numeric_column(dataframe, volume_col)
    money_flow_multiplier = (
        ((close_series - low_series) - (high_series - close_series))
        / (high_series - low_series).replace(0.0, np.nan)
    ).fillna(0.0)
    money_flow_volume = money_flow_multiplier * volume_series
    return money_flow_volume.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).sum() / volume_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).sum().replace(
        0.0,
        np.nan,
    )


def add_cmf(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"cmf{window}"] = calc_cmf(
        dataframe,
        window=window,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        volume_col=volume_col,
        min_periods=min_periods,
    )
