from __future__ import annotations

import pandas as pd

from .._shared import datetime_column, feature_arg, feature_info


FEATURE_INFO = feature_info(
    "qtr",
    "Quarter",
    "calendar",
    args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
)


def calc_quarter(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.quarter.astype("Int64")


def add_quarter(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "quarter"] = calc_quarter(dataframe, timestamp_col)
