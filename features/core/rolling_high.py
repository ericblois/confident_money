from __future__ import annotations

import pandas as pd

from .._shared import (
    feature_arg,
    feature_info,
    offset_suffix,
    positive_int,
    resolved_min_periods,
)
from .price import calc_price


FEATURE_INFO = feature_info(
    "roll_hi",
    "Rolling High",
    "core",
    args=[
        feature_arg("col", "Source Column", "source", "high"),
        feature_arg("window", "Lookback Periods", "periods", 20),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
    ],
)


def calc_rolling_high(
    dataframe: pd.DataFrame,
    col: str = "high",
    window: int = 20,
    min_periods: int | None = None,
    offset: int = 0,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    source_series = calc_price(dataframe, price_col=col, offset=offset)
    return source_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).max()


def add_rolling_high(
    dataframe: pd.DataFrame,
    col: str = "high",
    window: int = 20,
    min_periods: int | None = None,
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_rolling_high{window}{offset_suffix(offset)}"] = calc_rolling_high(
        dataframe,
        col=col,
        window=window,
        min_periods=min_periods,
        offset=offset,
    )
