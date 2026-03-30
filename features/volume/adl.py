from __future__ import annotations

import numpy as np
import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column


FEATURE_INFO = feature_info(
    "adl",
    "Accumulation Distribution Line",
    "volume",
    args=[
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("close", "Close Column", "close_source", "close"),
        feature_arg("volume", "Volume Column", "volume_source", "volume"),
    ],
)


def calc_adl(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
) -> pd.Series:
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    close_series = numeric_column(dataframe, close_col)
    volume_series = numeric_column(dataframe, volume_col)
    money_flow_multiplier = (
        ((close_series - low_series) - (high_series - close_series))
        / (high_series - low_series).replace(0.0, np.nan)
    ).fillna(0.0)
    return (money_flow_multiplier * volume_series).cumsum()


def add_adl(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "adl"] = calc_adl(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        volume_col=volume_col,
    )
