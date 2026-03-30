from __future__ import annotations

import numpy as np
import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column


FEATURE_INFO = feature_info(
    "clv",
    "Close Location Value",
    "candles",
    args=[
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("close", "Close Column", "close_source", "close"),
    ],
)


def calc_close_location(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
) -> pd.Series:
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    close_series = numeric_column(dataframe, close_col)
    return (close_series - low_series) / (high_series - low_series).replace(0.0, np.nan)


def add_close_location(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "close_location"] = calc_close_location(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
    )
