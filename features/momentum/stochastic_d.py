from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, positive_int
from .stochastic_k import calc_stoch_k


FEATURE_INFO = feature_info(
    "stoch_d",
    "Stochastic %D",
    "momentum",
    args=[
        feature_arg("window", "Lookback Periods", "periods", 14),
        feature_arg("signal_window", "Signal Periods", "signal_periods", 3),
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("close", "Close Column", "close_source", "close"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
        feature_arg("signal_min_periods", "Signal Minimum Periods", "min_periods", 1),
    ],
)


def calc_stoch_d(
    dataframe: pd.DataFrame,
    window: int = 14,
    signal_window: int = 3,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    min_periods: int | None = None,
    signal_min_periods: int = 1,
) -> pd.Series:
    resolved_signal_window = positive_int(signal_window, name="signal_window")
    resolved_signal_min_periods = positive_int(signal_min_periods, name="signal_min_periods")
    stoch_k = calc_stoch_k(
        dataframe,
        window=window,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        min_periods=min_periods,
    )
    return stoch_k.rolling(
        resolved_signal_window,
        min_periods=resolved_signal_min_periods,
    ).mean()


def add_stoch_d(
    dataframe: pd.DataFrame,
    window: int = 14,
    signal_window: int = 3,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
    min_periods: int | None = None,
    signal_min_periods: int = 1,
) -> None:
    dataframe[output_col or f"stoch_d{window}_{signal_window}"] = calc_stoch_d(
        dataframe,
        window=window,
        signal_window=signal_window,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        min_periods=min_periods,
        signal_min_periods=signal_min_periods,
    )
