from __future__ import annotations

import numpy as np
import pandas as pd

from .._shared import (
    feature_arg,
    feature_info,
    numeric_column,
    positive_int,
    resolved_min_periods,
    safe_log,
)


FEATURE_INFO = feature_info(
    "gk_vlt",
    "Garman-Klass Volatility",
    "volatility",
    args=[
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("open", "Open Column", "open_source", "open"),
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("close", "Close Column", "close_source", "close"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
        feature_arg(
            "annualization_factor",
            "Annualization Factor",
            "annualization_factor",
        ),
    ],
)


def calc_garman_klass_volatility(
    dataframe: pd.DataFrame,
    window: int,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    min_periods: int | None = None,
    annualization_factor: float | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    open_series = numeric_column(dataframe, open_col)
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    close_series = numeric_column(dataframe, close_col)
    high_low_term = safe_log(high_series / low_series).pow(2)
    close_open_term = safe_log(close_series / open_series).pow(2)
    rolling_variance = (
        (0.5 * high_low_term) - ((2.0 * np.log(2.0) - 1.0) * close_open_term)
    ).rolling(resolved_window, min_periods=resolved_window_min_periods).mean()
    volatility = np.sqrt(rolling_variance.clip(lower=0.0))
    if annualization_factor is not None:
        return volatility * np.sqrt(float(annualization_factor))
    return volatility


def add_garman_klass_volatility(
    dataframe: pd.DataFrame,
    window: int,
    open_col: str = "open",
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
    min_periods: int | None = None,
    annualization_factor: float | None = None,
) -> None:
    dataframe[output_col or f"gk_vlt{window}"] = calc_garman_klass_volatility(
        dataframe,
        window=window,
        open_col=open_col,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        min_periods=min_periods,
        annualization_factor=annualization_factor,
    )
