from __future__ import annotations

import pandas as pd

from .._shared import datetime_column, feature_arg, feature_info


FEATURE_INFO = feature_info(
    "moy",
    "Month of Year",
    "calendar",
    args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
)


def calc_month_of_year(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.month.astype("Int64")


def add_month_of_year(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "month_of_year"] = calc_month_of_year(dataframe, timestamp_col)
