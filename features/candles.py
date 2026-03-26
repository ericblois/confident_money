from __future__ import annotations

import numpy as np
import pandas as pd

from ._shared import feature_arg, feature_info, numeric_column


FEATURE_INFOS = (
    feature_info(
        "body_pct",
        "Candle Body Percent",
        "candles",
        args=[
            feature_arg("open", "Open Column", "open_source", "open"),
            feature_arg("close", "Close Column", "close_source", "close"),
        ],
    ),
    feature_info(
        "up_wick",
        "Upper Wick Ratio",
        "candles",
        args=[
            feature_arg("open", "Open Column", "open_source", "open"),
            feature_arg("high", "High Column", "high_source", "high"),
            feature_arg("low", "Low Column", "low_source", "low"),
            feature_arg("close", "Close Column", "close_source", "close"),
        ],
    ),
    feature_info(
        "low_wick",
        "Lower Wick Ratio",
        "candles",
        args=[
            feature_arg("open", "Open Column", "open_source", "open"),
            feature_arg("high", "High Column", "high_source", "high"),
            feature_arg("low", "Low Column", "low_source", "low"),
            feature_arg("close", "Close Column", "close_source", "close"),
        ],
    ),
    feature_info(
        "clv",
        "Close Location Value",
        "candles",
        args=[
            feature_arg("high", "High Column", "high_source", "high"),
            feature_arg("low", "Low Column", "low_source", "low"),
            feature_arg("close", "Close Column", "close_source", "close"),
        ],
    ),
)


def calc_body_pct(
    dataframe: pd.DataFrame,
    open_col: str = "open",
    close_col: str = "close",
) -> pd.Series:
    open_series = numeric_column(dataframe, open_col)
    close_series = numeric_column(dataframe, close_col)
    return (close_series - open_series) / open_series.replace(0.0, np.nan)


def add_body_pct(
    dataframe: pd.DataFrame,
    open_col: str = "open",
    close_col: str = "close",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "body_pct"] = calc_body_pct(
        dataframe,
        open_col=open_col,
        close_col=close_col,
    )


def calc_upper_wick_ratio(
    dataframe: pd.DataFrame,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
) -> pd.Series:
    open_series = numeric_column(dataframe, open_col)
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    close_series = numeric_column(dataframe, close_col)
    candle_range = high_series - low_series
    return (high_series - pd.concat([open_series, close_series], axis=1).max(axis=1)) / candle_range.replace(
        0.0,
        np.nan,
    )


def add_upper_wick_ratio(
    dataframe: pd.DataFrame,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "upper_wick_ratio"] = calc_upper_wick_ratio(
        dataframe,
        open_col=open_col,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
    )


def calc_lower_wick_ratio(
    dataframe: pd.DataFrame,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
) -> pd.Series:
    open_series = numeric_column(dataframe, open_col)
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    close_series = numeric_column(dataframe, close_col)
    candle_range = high_series - low_series
    return (pd.concat([open_series, close_series], axis=1).min(axis=1) - low_series) / candle_range.replace(
        0.0,
        np.nan,
    )


def add_lower_wick_ratio(
    dataframe: pd.DataFrame,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "lower_wick_ratio"] = calc_lower_wick_ratio(
        dataframe,
        open_col=open_col,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
    )


def calc_close_location(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
) -> pd.Series:
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    close_series = numeric_column(dataframe, close_col)
    return (close_series - low_series) / (high_series - low_series).replace(0.0, np.nan)


def add_close_location(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "close_location"] = calc_close_location(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
    )


__all__ = [
    "FEATURE_INFOS",
    "add_body_pct",
    "add_close_location",
    "add_lower_wick_ratio",
    "add_upper_wick_ratio",
    "calc_body_pct",
    "calc_close_location",
    "calc_lower_wick_ratio",
    "calc_upper_wick_ratio",
]
