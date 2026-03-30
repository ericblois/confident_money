from __future__ import annotations

import numpy as np
import pandas as pd

from .._shared import (
    feature_arg,
    feature_info,
    numeric_column,
    positive_int,
    resolved_min_periods,
)
from ..core.typical_price import calc_typical_price


FEATURE_INFO = feature_info(
    "mfi",
    "Money Flow Index",
    "volume",
    args=[
        feature_arg("window", "Lookback Periods", "periods", 14),
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("close", "Close Column", "close_source", "close"),
        feature_arg("volume", "Volume Column", "volume_source", "volume"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
    ],
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
