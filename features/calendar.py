from __future__ import annotations

import pandas as pd
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import BDay

from ._shared import datetime_column, feature_arg, feature_info


FEATURE_INFOS = (
    feature_info(
        "dow",
        "Day of Week",
        "calendar",
        args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
    ),
    feature_info(
        "dom",
        "Day of Month",
        "calendar",
        args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
    ),
    feature_info(
        "doy",
        "Day of Year",
        "calendar",
        args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
    ),
    feature_info(
        "woy",
        "Week of Year",
        "calendar",
        args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
    ),
    feature_info(
        "moy",
        "Month of Year",
        "calendar",
        args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
    ),
    feature_info(
        "qtr",
        "Quarter",
        "calendar",
        args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
    ),
    feature_info(
        "hour",
        "Hour",
        "calendar",
        args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
    ),
    feature_info(
        "is_ms",
        "Is Month Start",
        "calendar",
        args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
    ),
    feature_info(
        "is_me",
        "Is Month End",
        "calendar",
        args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
    ),
    feature_info(
        "is_hol_adj",
        "Is Holiday Adjacent",
        "calendar",
        args=[feature_arg("timestamp", "Timestamp Column", "timestamp_source", "date")],
    ),
)


def calc_day_of_week(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.dayofweek.astype("Int64")


def add_day_of_week(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "day_of_week"] = calc_day_of_week(dataframe, timestamp_col)


def calc_day_of_month(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.day.astype("Int64")


def add_day_of_month(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "day_of_month"] = calc_day_of_month(dataframe, timestamp_col)


def calc_day_of_year(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.dayofyear.astype("Int64")


def add_day_of_year(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "day_of_year"] = calc_day_of_year(dataframe, timestamp_col)


def calc_week_of_year(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.isocalendar().week.astype("Int64")


def add_week_of_year(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "week_of_year"] = calc_week_of_year(dataframe, timestamp_col)


def calc_month_of_year(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.month.astype("Int64")


def add_month_of_year(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "month_of_year"] = calc_month_of_year(dataframe, timestamp_col)


def calc_quarter(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.quarter.astype("Int64")


def add_quarter(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "quarter"] = calc_quarter(dataframe, timestamp_col)


def calc_hour(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.hour.astype("Int64")


def add_hour(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "hour"] = calc_hour(dataframe, timestamp_col)


def calc_is_month_start(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.is_month_start.fillna(False).astype(int)


def add_is_month_start(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "is_month_start"] = calc_is_month_start(dataframe, timestamp_col)


def calc_is_month_end(dataframe: pd.DataFrame, timestamp_col: str = "date") -> pd.Series:
    return datetime_column(dataframe, timestamp_col).dt.is_month_end.fillna(False).astype(int)


def add_is_month_end(
    dataframe: pd.DataFrame,
    timestamp_col: str = "date",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "is_month_end"] = calc_is_month_end(dataframe, timestamp_col)


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


__all__ = [
    "FEATURE_INFOS",
    "add_day_of_month",
    "add_day_of_week",
    "add_day_of_year",
    "add_hour",
    "add_is_holiday_adjacent",
    "add_is_month_end",
    "add_is_month_start",
    "add_month_of_year",
    "add_quarter",
    "add_week_of_year",
    "calc_day_of_month",
    "calc_day_of_week",
    "calc_day_of_year",
    "calc_hour",
    "calc_is_holiday_adjacent",
    "calc_is_month_end",
    "calc_is_month_start",
    "calc_month_of_year",
    "calc_quarter",
    "calc_week_of_year",
]
