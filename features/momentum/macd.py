from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, positive_int
from ..trends.ema import calc_ema


FEATURE_INFO = feature_info(
    "macd",
    "MACD Line",
    "momentum",
    args=[
        feature_arg("col", "Source Column", "source", "close"),
        feature_arg("fast_span", "Fast Periods", "periods", 12),
        feature_arg("slow_span", "Slow Periods", "periods", 26),
        feature_arg("min_periods", "Minimum Periods", "min_periods", 1),
    ],
)


def calc_macd(
    dataframe: pd.DataFrame,
    col: str = "close",
    fast_span: int = 12,
    slow_span: int = 26,
    min_periods: int = 1,
) -> pd.Series:
    resolved_fast_span = positive_int(fast_span, name="fast_span")
    resolved_slow_span = positive_int(slow_span, name="slow_span")
    if resolved_fast_span >= resolved_slow_span:
        raise ValueError("fast_span must be smaller than slow_span.")

    fast_ema = calc_ema(dataframe, col, span=resolved_fast_span, min_periods=min_periods)
    slow_ema = calc_ema(dataframe, col, span=resolved_slow_span, min_periods=min_periods)
    return fast_ema - slow_ema


def add_macd(
    dataframe: pd.DataFrame,
    col: str = "close",
    fast_span: int = 12,
    slow_span: int = 26,
    output_col: str | None = None,
    min_periods: int = 1,
) -> None:
    dataframe[output_col or f"{col}_macd{fast_span}_{slow_span}"] = calc_macd(
        dataframe,
        col=col,
        fast_span=fast_span,
        slow_span=slow_span,
        min_periods=min_periods,
    )
