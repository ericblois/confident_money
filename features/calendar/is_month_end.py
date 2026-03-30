from __future__ import annotations

import pandas as pd

from .._shared import datetime_column, feature_arg, feature_info


FEATURE_INFO = feature_info(
    "is_me",
    "Is Month End",
    "calendar",
    args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
)


def calc_is_month_end(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.is_month_end.fillna(False).astype(int)


def add_is_month_end(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "is_month_end"] = calc_is_month_end(dataframe, timestamp_col)
