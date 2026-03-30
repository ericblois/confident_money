from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column, safe_log


FEATURE_INFO = feature_info(
    "log",
    "Natural Log Value",
    "utils",
    args=[feature_arg("col", "Source Column", "source")],
)


def calc_log_value(dataframe: pd.DataFrame, col: str) -> pd.Series:
    return safe_log(numeric_column(dataframe, col))


def add_log_value(
    dataframe: pd.DataFrame,
    col: str,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"log_{col}"] = calc_log_value(dataframe, col)
