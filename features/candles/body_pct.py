from __future__ import annotations

import numpy as np
import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column


FEATURE_INFO = feature_info(
    "body_pct",
    "Candle Body Percent",
    "candles",
    args=[
        feature_arg("open", "Open Column", "open_source", "open"),
        feature_arg("close", "Close Column", "close_source", "close"),
    ],
)


def calc_body_pct(
    dataframe: pd.DataFrame,
    open_col: str = "open",
    close_col: str = "close",
) -> pd.Series:
    open_series = numeric_column(dataframe, open_col)
    close_series = numeric_column(dataframe, close_col)
    return (close_series - open_series) / open_series.replace(0.0, np.nan)


def add_body_pct(
    dataframe: pd.DataFrame,
    open_col: str = "open",
    close_col: str = "close",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "body_pct"] = calc_body_pct(
        dataframe,
        open_col=open_col,
        close_col=close_col,
    )
