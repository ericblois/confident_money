from __future__ import annotations

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import BDay

from .._shared import datetime_column, feature_arg, feature_info


FEATURE_INFO = feature_info(
    "is_hol_adj",
    "Is Holiday Adjacent",
    "calendar",
    args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
)


def calc_is_holiday_adjacent(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
) -> pd.Series:
    timestamps = datetime_column(dataframe, timestamp_col).dt.normalize()
    valid_timestamps = timestamps.dropna()
    if valid_timestamps.empty:
        return pd.Series(0, index=dataframe.index, dtype=int)

    holiday_index = USFederalHolidayCalendar().holidays(
        start=valid_timestamps.min() - pd.Timedelta(days=7),
        end=valid_timestamps.max() + pd.Timedelta(days=7),
    )
    adjacent_holidays = {
        *pd.DatetimeIndex(holiday_index - BDay(1)).normalize(),
        *pd.DatetimeIndex(holiday_index + BDay(1)).normalize(),
    }
    return timestamps.isin(adjacent_holidays).fillna(False).astype(int)


def add_is_holiday_adjacent(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "is_holiday_adjacent"] = calc_is_holiday_adjacent(
        dataframe,
        timestamp_col=timestamp_col,
    )
