from __future__ import annotations

import numpy as np
import pandas as pd

from .._shared import (
    feature_arg,
    feature_info,
    numeric_column,
    positive_int,
    resolved_min_periods,
    wilder_mean,
)


FEATURE_INFO = feature_info(
    "rsi",
    "Relative Strength Index",
    "momentum",
    args=[
        feature_arg("col", "Source Column", "source", "close"),
        feature_arg("window", "Lookback Periods", "periods", 14),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
    ],
)


def calc_rsi(
    dataframe: pd.DataFrame,
    col: str = "close",
    window: int = 14,
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    delta = numeric_column(dataframe, col).diff()
    gains = delta.clip(lower=0.0)
    losses = -delta.clip(upper=0.0)
    average_gain = wilder_mean(gains, resolved_window, min_periods=resolved_window_min_periods)
    average_loss = wilder_mean(losses, resolved_window, min_periods=resolved_window_min_periods)
    relative_strength = average_gain / average_loss.replace(0.0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + relative_strength))
    rsi = rsi.where(average_loss != 0.0, 100.0)
    rsi = rsi.where(~((average_gain == 0.0) & (average_loss == 0.0)), 50.0)
    return rsi


def add_rsi(
    dataframe: pd.DataFrame,
    col: str = "close",
    window: int = 14,
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"{col}_rsi{window}"] = calc_rsi(
        dataframe,
        col=col,
        window=window,
        min_periods=min_periods,
    )
