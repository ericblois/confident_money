from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column


FEATURE_INFO = feature_info(
    "tr",
    "True Range",
    "volatility",
    args=[
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("close", "Close Column", "close_source", "close"),
    ],
)


def calc_true_range(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
) -> pd.Series:
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    prior_close = numeric_column(dataframe, close_col).shift(1)
    return pd.concat(
        [
            high_series - low_series,
            (high_series - prior_close).abs(),
            (low_series - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def add_true_range(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "true_range"] = calc_true_range(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
    )
