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
    "rs_vlt",
    "Rogers-Satchell Volatility",
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


def calc_rogers_satchell_volatility(
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
    log_high_open = safe_log(high_series / open_series)
    log_high_close = safe_log(high_series / close_series)
    log_low_open = safe_log(low_series / open_series)
    log_low_close = safe_log(low_series / close_series)
    rolling_variance = (
        (log_high_open * log_high_close) + (log_low_open * log_low_close)
    ).rolling(resolved_window, min_periods=resolved_window_min_periods).mean()
    volatility = np.sqrt(rolling_variance.clip(lower=0.0))
    if annualization_factor is not None:
        return volatility * np.sqrt(float(annualization_factor))
    return volatility


def add_rogers_satchell_volatility(
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
    dataframe[output_col or f"rs_vlt{window}"] = calc_rogers_satchell_volatility(
        dataframe,
        window=window,
        open_col=open_col,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        min_periods=min_periods,
        annualization_factor=annualization_factor,
    )
