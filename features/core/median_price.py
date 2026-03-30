from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, non_negative_int, numeric_column, offset_suffix


FEATURE_INFO = feature_info(
    "med_px",
    "Median Price",
    "core",
    args=[
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
    ],
)


def calc_median_price(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    offset: int = 0,
) -> pd.Series:
    resolved_offset = non_negative_int(offset, name="offset")
    high_series = numeric_column(dataframe, high_col).shift(resolved_offset)
    low_series = numeric_column(dataframe, low_col).shift(resolved_offset)
    return (high_series + low_series) / 2.0


def add_median_price(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"median_price{offset_suffix(offset)}"] = calc_median_price(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        offset=offset,
    )
