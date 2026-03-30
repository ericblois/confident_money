from __future__ import annotations

import pandas as pd

from .._shared import (
    feature_arg,
    feature_info,
    non_negative_int,
    numeric_column,
    offset_suffix,
)


FEATURE_INFO = feature_info(
    "vol",
    "Volume",
    "volume",
    args=[
        feature_arg("col", "Volume Column", "volume_source", "volume"),
    ],
)


def calc_volume(
    dataframe: pd.DataFrame,
    col: str = "volume",
    offset: int = 0,
) -> pd.Series:
    resolved_offset = non_negative_int(offset, name="offset")
    return numeric_column(dataframe, col).shift(resolved_offset)


def add_volume(
    dataframe: pd.DataFrame,
    col: str = "volume",
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_value{offset_suffix(offset)}"] = calc_volume(
        dataframe,
        col=col,
        offset=offset,
    )
