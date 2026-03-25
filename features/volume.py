from __future__ import annotations

import numpy as np
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
from .core import calc_typical_price


FEATURE_INFOS = (
    feature_info(
        "vol",
        "Volume",
        "volume",
        args=[
            feature_arg("col", "Volume Column", "volume_source", "volume"),
        ],
    ),
    feature_info(
        "vwap",
        "Volume Weighted Average Price",
        "volume",
        args=[
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("price_col", "Price Column", "price_source", "close"),
            feature_arg("volume_col", "Volume Column", "volume_source", "volume"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
    feature_info(
        "obv",
        "On-Balance Volume",
        "volume",
        args=[
            feature_arg("close_col", "Close Column", "close_source", "close"),
            feature_arg("volume_col", "Volume Column", "volume_source", "volume"),
        ],
    ),
    feature_info(
        "adl",
        "Accumulation Distribution Line",
        "volume",
        args=[
            feature_arg("high_col", "High Column", "high_source", "high"),
            feature_arg("low_col", "Low Column", "low_source", "low"),
            feature_arg("close_col", "Close Column", "close_source", "close"),
            feature_arg("volume_col", "Volume Column", "volume_source", "volume"),
        ],
    ),
    feature_info(
        "cmf",
        "Chaikin Money Flow",
        "volume",
        args=[
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("high_col", "High Column", "high_source", "high"),
            feature_arg("low_col", "Low Column", "low_source", "low"),
            feature_arg("close_col", "Close Column", "close_source", "close"),
            feature_arg("volume_col", "Volume Column", "volume_source", "volume"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
    feature_info(
        "mfi",
        "Money Flow Index",
        "volume",
        args=[
            feature_arg("window", "Lookback Periods", "periods", 14),
            feature_arg("high_col", "High Column", "high_source", "high"),
            feature_arg("low_col", "Low Column", "low_source", "low"),
            feature_arg("close_col", "Close Column", "close_source", "close"),
            feature_arg("volume_col", "Volume Column", "volume_source", "volume"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
    feature_info(
        "rvol_pct",
        "Relative Volume Percentile",
        "volume",
        args=[
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("volume_col", "Volume Column", "volume_source", "volume"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
)


def calc_volume(
    dataframe: pd.DataFrame,
    col: str = "volume",
    offset: int = 0,
) -> pd.Series:
    resolved_offset = non_negative_int(offset, name="offset")
    return numeric_column(dataframe, col).shift(resolved_offset)


def add_volume(
    dataframe: pd.DataFrame,
    col: str = "volume",
    offset: int = 0,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_value{offset_suffix(offset)}"] = calc_volume(
        dataframe,
        col=col,
        offset=offset,
    )


def calc_vwap(
    dataframe: pd.DataFrame,
    window: int,
    price_col: str = "close",
    volume_col: str = "volume",
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    price_series = numeric_column(dataframe, price_col)
    volume_series = numeric_column(dataframe, volume_col)
    rolling_volume = volume_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).sum()
    return (
        (price_series * volume_series)
        .rolling(resolved_window, min_periods=resolved_window_min_periods)
        .sum()
        / rolling_volume.replace(0.0, np.nan)
    )


def add_vwap(
    dataframe: pd.DataFrame,
    window: int,
    price_col: str = "close",
    volume_col: str = "volume",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"{price_col}_vwap{window}"] = calc_vwap(
        dataframe,
        window=window,
        price_col=price_col,
        volume_col=volume_col,
        min_periods=min_periods,
    )


def calc_obv(
    dataframe: pd.DataFrame,
    close_col: str = "close",
    volume_col: str = "volume",
) -> pd.Series:
    close_delta = numeric_column(dataframe, close_col).diff()
    direction = close_delta.gt(0.0).astype(int) - close_delta.lt(0.0).astype(int)
    return (direction.fillna(0).astype(float) * numeric_column(dataframe, volume_col)).cumsum()


def add_obv(
    dataframe: pd.DataFrame,
    close_col: str = "close",
    volume_col: str = "volume",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "obv"] = calc_obv(
        dataframe,
        close_col=close_col,
        volume_col=volume_col,
    )


def calc_adl(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
) -> pd.Series:
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    close_series = numeric_column(dataframe, close_col)
    volume_series = numeric_column(dataframe, volume_col)
    money_flow_multiplier = (
        ((close_series - low_series) - (high_series - close_series))
        / (high_series - low_series).replace(0.0, np.nan)
    ).fillna(0.0)
    return (money_flow_multiplier * volume_series).cumsum()


def add_adl(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "adl"] = calc_adl(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        volume_col=volume_col,
    )


def calc_cmf(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    close_series = numeric_column(dataframe, close_col)
    volume_series = numeric_column(dataframe, volume_col)
    money_flow_multiplier = (
        ((close_series - low_series) - (high_series - close_series))
        / (high_series - low_series).replace(0.0, np.nan)
    ).fillna(0.0)
    money_flow_volume = money_flow_multiplier * volume_series
    return money_flow_volume.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).sum() / volume_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).sum().replace(
        0.0,
        np.nan,
    )


def add_cmf(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"cmf{window}"] = calc_cmf(
        dataframe,
        window=window,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        volume_col=volume_col,
        min_periods=min_periods,
    )


def calc_mfi(
    dataframe: pd.DataFrame,
    window: int = 14,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    typical_price = calc_typical_price(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
    )
    raw_money_flow = typical_price * numeric_column(dataframe, volume_col)
    typical_price_delta = typical_price.diff()
    positive_flow = raw_money_flow.where(typical_price_delta > 0.0, 0.0)
    negative_flow = raw_money_flow.where(typical_price_delta < 0.0, 0.0).abs()
    rolling_positive = positive_flow.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).sum()
    rolling_negative = negative_flow.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).sum()
    money_ratio = rolling_positive / rolling_negative.replace(0.0, np.nan)
    mfi = 100.0 - (100.0 / (1.0 + money_ratio))
    mfi = mfi.where(rolling_negative != 0.0, 100.0)
    mfi = mfi.where(~((rolling_positive == 0.0) & (rolling_negative == 0.0)), 50.0)
    return mfi


def add_mfi(
    dataframe: pd.DataFrame,
    window: int = 14,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    volume_col: str = "volume",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"mfi{window}"] = calc_mfi(
        dataframe,
        window=window,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        volume_col=volume_col,
        min_periods=min_periods,
    )


def calc_relative_volume_percentile(
    dataframe: pd.DataFrame,
    window: int,
    volume_col: str = "volume",
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    return (
        numeric_column(dataframe, volume_col)
        .rolling(resolved_window, min_periods=resolved_window_min_periods)
        .rank(pct=True)
        .mul(100.0)
    )


def add_relative_volume_percentile(
    dataframe: pd.DataFrame,
    window: int,
    volume_col: str = "volume",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[
        output_col or f"{volume_col}_rvol_pct{window}"
    ] = calc_relative_volume_percentile(
        dataframe,
        window=window,
        volume_col=volume_col,
        min_periods=min_periods,
    )


__all__ = [
    "FEATURE_INFOS",
    "add_adl",
    "add_cmf",
    "add_mfi",
    "add_obv",
    "add_relative_volume_percentile",
    "add_volume",
    "add_vwap",
    "calc_adl",
    "calc_cmf",
    "calc_mfi",
    "calc_obv",
    "calc_relative_volume_percentile",
    "calc_volume",
    "calc_vwap",
]
