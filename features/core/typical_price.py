from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, non_negative_int, numeric_column, offset_suffix


FEATURE_INFO = feature_info(
    "typ_px",
    "Typical Price",
    "core",
    args=[
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("close", "Close Column", "close_source", "close"),
    ],
)


def calc_typical_price(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    offset: int = 0,
) -> pd.Series:
    resolved_offset = non_negative_int(offset, name="offset")
    high_series = numeric_column(dataframe, high_col).shift(resolved_offset)
    low_series = numeric_column(dataframe, low_col).shift(resolved_offset)
    close_series = numeric_column(dataframe, close_col).shift(resolved_offset)
    return (high_series + low_series + close_series) / 3.0


def add_typical_price(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"typical_price{offset_suffix(offset)}"] = calc_typical_price(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        offset=offset,
    )
