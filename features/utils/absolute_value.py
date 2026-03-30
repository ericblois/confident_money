from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column


FEATURE_INFO = feature_info(
    "abs",
    "Absolute Value",
    "utils",
    args=[feature_arg("col", "Source Column", "source")],
)


def calc_abs(dataframe: pd.DataFrame, col: str) -> pd.Series:
    return numeric_column(dataframe, col).abs()


def add_abs(
    dataframe: pd.DataFrame,
    col: str,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"abs_{col}"] = calc_abs(dataframe, col)
