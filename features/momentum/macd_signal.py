from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info
from ..trends.ema import calc_ema
from .macd import calc_macd


FEATURE_INFO = feature_info(
    "macd_sig",
    "MACD Signal",
    "momentum",
    args=[
        feature_arg("col", "Source Column", "source", "close"),
        feature_arg("fast_span", "Fast Periods", "periods", 12),
        feature_arg("slow_span", "Slow Periods", "periods", 26),
        feature_arg("signal_span", "Signal Periods", "signal_periods", 9),
        feature_arg("min_periods", "Minimum Periods", "min_periods", 1),
    ],
)


def calc_macd_signal(
    dataframe: pd.DataFrame,
    col: str = "close",
    fast_span: int = 12,
    slow_span: int = 26,
    signal_span: int = 9,
    min_periods: int = 1,
) -> pd.Series:
    macd_series = calc_macd(
        dataframe,
        col=col,
        fast_span=fast_span,
        slow_span=slow_span,
        min_periods=min_periods,
    )
    temp_dataframe = pd.DataFrame({"macd": macd_series}, index=dataframe.index)
    return calc_ema(
        temp_dataframe,
        "macd",
        span=signal_span,
        min_periods=min_periods,
    )


def add_macd_signal(
    dataframe: pd.DataFrame,
    col: str = "close",
    fast_span: int = 12,
    slow_span: int = 26,
    signal_span: int = 9,
    output_col: str | None = None,
    min_periods: int = 1,
) -> None:
    dataframe[output_col or f"{col}_macd_signal{fast_span}_{slow_span}_{signal_span}"] = calc_macd_signal(
        dataframe,
        col=col,
        fast_span=fast_span,
        slow_span=slow_span,
        signal_span=signal_span,
        min_periods=min_periods,
    )
