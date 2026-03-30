from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, offset_suffix, positive_int
from .price import calc_price


FEATURE_INFO = feature_info(
    "ret",
    "Simple Return",
    "core",
    args=[
        feature_arg("col", "Source Column", "source", "close"),
        feature_arg("window", "Lookback Periods", "periods", 1),
    ],
)


def calc_return(
    dataframe: pd.DataFrame,
    col: str = "close",
    window: int = 1,
    offset: int = 0,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    source_series = calc_price(dataframe, price_col=col, offset=offset)
    return source_series / source_series.shift(resolved_window) - 1.0


def add_return(
    dataframe: pd.DataFrame,
    col: str = "close",
    window: int = 1,
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_return{window}{offset_suffix(offset)}"] = calc_return(
        dataframe,
        col=col,
        window=window,
        offset=offset,
    )
