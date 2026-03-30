from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column, positive_int


FEATURE_INFO = feature_info(
    "roc",
    "Rate of Change",
    "momentum",
    args=[
        feature_arg("col", "Source Column", "source", "close"),
        feature_arg("window", "Lookback Periods", "periods", 10),
    ],
)


def calc_roc(
    dataframe: pd.DataFrame,
    col: str = "close",
    window: int = 10,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    source_series = numeric_column(dataframe, col)
    return 100.0 * (source_series / source_series.shift(resolved_window) - 1.0)


def add_roc(
    dataframe: pd.DataFrame,
    col: str = "close",
    window: int = 10,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_roc{window}"] = calc_roc(
        dataframe,
        col=col,
        window=window,
    )
