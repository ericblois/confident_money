from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, non_negative_int, numeric_column, offset_suffix


FEATURE_INFO = feature_info(
    "px",
    "Price",
    "core",
    args=[
        feature_arg("price", "Price Column", "price_source", "close"),
    ],
)


def calc_price(
    dataframe: pd.DataFrame,
    price_col: str = "close",
    offset: int = 0,
) -> pd.Series:
    resolved_offset = non_negative_int(offset, name="offset")
    return numeric_column(dataframe, price_col).shift(resolved_offset)


def add_price(
    dataframe: pd.DataFrame,
    price_col: str = "close",
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{price_col}_value{offset_suffix(offset)}"] = calc_price(
        dataframe,
        price_col=price_col,
        offset=offset,
    )
