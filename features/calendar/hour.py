from __future__ import annotations

import pandas as pd

from .._shared import datetime_column, feature_arg, feature_info


FEATURE_INFO = feature_info(
    "hour",
    "Hour",
    "calendar",
    args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
)


def calc_hour(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.hour.astype("Int64")


def add_hour(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "hour"] = calc_hour(dataframe, timestamp_col)
