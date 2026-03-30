from __future__ import annotations

import pandas as pd

from .._shared import datetime_column, feature_arg, feature_info


FEATURE_INFO = feature_info(
    "dow",
    "Day of Week",
    "calendar",
    args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
)


def calc_day_of_week(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.dayofweek.astype("Int64")


def add_day_of_week(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "day_of_week"] = calc_day_of_week(dataframe, timestamp_col)
