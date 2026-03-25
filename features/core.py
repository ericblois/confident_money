from __future__ import annotations

import pandas as pd

from ._shared import (
    feature_arg,
    feature_info,
    non_negative_int,
    numeric_column,
    offset_suffix,
    positive_int,
    resolved_min_periods,
)


FEATURE_INFOS = (
    feature_info(
        "px",
        "Price",
        "core",
        args=[
            feature_arg("price_col", "Price Column", "price_source", "close"),
        ],
    ),
    feature_info(
        "ret",
        "Simple Return",
        "core",
        args=[
            feature_arg("col", "Source Column", "source", "close"),
            feature_arg("window", "Lookback Periods", "periods", 1),
        ],
    ),
    feature_info(
        "log_ret",
        "Log Return",
        "core",
        args=[
            feature_arg("col", "Source Column", "source", "close"),
            feature_arg("window", "Lookback Periods", "periods", 1),
        ],
    ),
    feature_info(
        "roll_hi",
        "Rolling High",
        "core",
        args=[
            feature_arg("col", "Source Column", "source", "high"),
            feature_arg("window", "Lookback Periods", "periods", 20),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
    feature_info(
        "roll_lo",
        "Rolling Low",
        "core",
        args=[
            feature_arg("col", "Source Column", "source", "low"),
            feature_arg("window", "Lookback Periods", "periods", 20),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
    feature_info(
        "typ_px",
        "Typical Price",
        "core",
        args=[
            feature_arg("high_col", "High Column", "high_source", "high"),
            feature_arg("low_col", "Low Column", "low_source", "low"),
            feature_arg("close_col", "Close Column", "close_source", "close"),
        ],
    ),
    feature_info(
        "med_px",
        "Median Price",
        "core",
        args=[
            feature_arg("high_col", "High Column", "high_source", "high"),
            feature_arg("low_col", "Low Column", "low_source", "low"),
        ],
    ),
)


def calc_price(
    dataframe: pd.DataFrame,
    price_col: str = "close",
    offset: int = 0,
) -> pd.Series:
    resolved_offset = non_negative_int(offset, name="offset")
    return numeric_column(dataframe, price_col).shift(resolved_offset)


def add_price(
    dataframe: pd.DataFrame,
    price_col: str = "close",
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{price_col}_value{offset_suffix(offset)}"] = calc_price(
        dataframe,
        price_col=price_col,
        offset=offset,
    )


def calc_return(
    dataframe: pd.DataFrame,
    col: str = "close",
    window: int = 1,
    offset: int = 0,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    source_series = calc_price(dataframe, price_col=col, offset=offset)
    return source_series / source_series.shift(resolved_window) - 1.0


def add_return(
    dataframe: pd.DataFrame,
    col: str = "close",
    window: int = 1,
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_return{window}{offset_suffix(offset)}"] = calc_return(
        dataframe,
        col=col,
        window=window,
        offset=offset,
    )


def calc_log_return(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    offset: int = 0,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    source_series = calc_price(dataframe, price_col=col, offset=offset)
    return source_series.diff(resolved_window)


def add_log_return(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
    offset: int = 0,
) -> None:
    dataframe[output_col or f"{col}_log_return{window}{offset_suffix(offset)}"] = calc_log_return(
        dataframe,
        col=col,
        window=window,
        offset=offset,
    )


def calc_rolling_high(
    dataframe: pd.DataFrame,
    col: str = "high",
    window: int = 20,
    min_periods: int | None = None,
    offset: int = 0,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    source_series = calc_price(dataframe, price_col=col, offset=offset)
    return source_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).max()


def add_rolling_high(
    dataframe: pd.DataFrame,
    col: str = "high",
    window: int = 20,
    min_periods: int | None = None,
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_rolling_high{window}{offset_suffix(offset)}"] = calc_rolling_high(
        dataframe,
        col=col,
        window=window,
        min_periods=min_periods,
        offset=offset,
    )


def calc_rolling_low(
    dataframe: pd.DataFrame,
    col: str = "low",
    window: int = 20,
    min_periods: int | None = None,
    offset: int = 0,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    source_series = calc_price(dataframe, price_col=col, offset=offset)
    return source_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).min()


def add_rolling_low(
    dataframe: pd.DataFrame,
    col: str = "low",
    window: int = 20,
    min_periods: int | None = None,
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_rolling_low{window}{offset_suffix(offset)}"] = calc_rolling_low(
        dataframe,
        col=col,
        window=window,
        min_periods=min_periods,
        offset=offset,
    )


def calc_typical_price(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    offset: int = 0,
) -> pd.Series:
    resolved_offset = non_negative_int(offset, name="offset")
    high_series = numeric_column(dataframe, high_col).shift(resolved_offset)
    low_series = numeric_column(dataframe, low_col).shift(resolved_offset)
    close_series = numeric_column(dataframe, close_col).shift(resolved_offset)
    return (high_series + low_series + close_series) / 3.0


def add_typical_price(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"typical_price{offset_suffix(offset)}"] = calc_typical_price(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        offset=offset,
    )


def calc_median_price(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    offset: int = 0,
) -> pd.Series:
    resolved_offset = non_negative_int(offset, name="offset")
    high_series = numeric_column(dataframe, high_col).shift(resolved_offset)
    low_series = numeric_column(dataframe, low_col).shift(resolved_offset)
    return (high_series + low_series) / 2.0


def add_median_price(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"median_price{offset_suffix(offset)}"] = calc_median_price(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        offset=offset,
    )


__all__ = [
    "FEATURE_INFOS",
    "add_log_return",
    "add_median_price",
    "add_price",
    "add_return",
    "add_rolling_high",
    "add_rolling_low",
    "add_typical_price",
    "calc_log_return",
    "calc_median_price",
    "calc_price",
    "calc_return",
    "calc_rolling_high",
    "calc_rolling_low",
    "calc_typical_price",
]
