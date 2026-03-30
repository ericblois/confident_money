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
    "pk_vlt",
    "Parkinson Volatility",
    "volatility",
    args=[
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("high", "High Column", "high_source", "high"),
        feature_arg("low", "Low Column", "low_source", "low"),
        feature_arg("min_periods", "Minimum Periods", "min_periods"),
        feature_arg(
            "annualization_factor",
            "Annualization Factor",
            "annualization_factor",
        ),
    ],
)


def calc_parkinson_volatility(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    min_periods: int | None = None,
    annualization_factor: float | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    high_low_log_range = safe_log(numeric_column(dataframe, high_col) / numeric_column(dataframe, low_col))
    rolling_variance = (
        high_low_log_range.pow(2)
        .rolling(resolved_window, min_periods=resolved_window_min_periods)
        .mean()
        / (4.0 * np.log(2.0))
    )
    volatility = np.sqrt(rolling_variance.clip(lower=0.0))
    if annualization_factor is not None:
        return volatility * np.sqrt(float(annualization_factor))
    return volatility


def add_parkinson_volatility(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    output_col: str | None = None,
    min_periods: int | None = None,
    annualization_factor: float | None = None,
) -> None:
    dataframe[output_col or f"pk_vlt{window}"] = calc_parkinson_volatility(
        dataframe,
        window=window,
        high_col=high_col,
        low_col=low_col,
        min_periods=min_periods,
        annualization_factor=annualization_factor,
    )
