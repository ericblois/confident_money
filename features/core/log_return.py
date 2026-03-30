from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, offset_suffix, positive_int
from .price import calc_price


FEATURE_INFO = feature_info(
    "log_ret",
    "Log Return",
    "core",
    args=[
        feature_arg("col", "Source Column", "source", "close"),
        feature_arg("window", "Lookback Periods", "periods", 1),
    ],
)


def calc_log_return(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    offset: int = 0,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    source_series = calc_price(dataframe, price_col=col, offset=offset)
    return source_series.diff(resolved_window)


def add_log_return(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
    offset: int = 0,
) -> None:
    dataframe[output_col or f"{col}_log_return{window}{offset_suffix(offset)}"] = calc_log_return(
        dataframe,
        col=col,
        window=window,
        offset=offset,
    )
