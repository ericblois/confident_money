from __future__ import annotations

import numpy as np
import pandas as pd

from ._shared import (
    feature_arg,
    feature_info,
    numeric_column,
    positive_int,
    resolved_min_periods,
    safe_log,
    wilder_mean,
)


FEATURE_INFOS = (
    feature_info(
        "tr",
        "True Range",
        "volatility",
        args=[
            feature_arg("high", "High Column", "high_source", "high"),
            feature_arg("low", "Low Column", "low_source", "low"),
            feature_arg("close", "Close Column", "close_source", "close"),
        ],
    ),
    feature_info(
        "atr",
        "Average True Range",
        "volatility",
        args=[
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("high", "High Column", "high_source", "high"),
            feature_arg("low", "Low Column", "low_source", "low"),
            feature_arg("close", "Close Column", "close_source", "close"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
    feature_info(
        "vlt",
        "Realized Volatility",
        "volatility",
        args=[
            feature_arg("col", "Source Column", "source"),
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
    feature_info(
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
    ),
    feature_info(
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
    ),
    feature_info(
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
    ),
)


def calc_true_range(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
) -> pd.Series:
    high_series = numeric_column(dataframe, high_col)
    low_series = numeric_column(dataframe, low_col)
    prior_close = numeric_column(dataframe, close_col).shift(1)
    return pd.concat(
        [
            high_series - low_series,
            (high_series - prior_close).abs(),
            (low_series - prior_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def add_true_range(
    dataframe: pd.DataFrame,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "true_range"] = calc_true_range(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
    )


def calc_atr(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    min_periods: int | None = None,
) -> pd.Series:
    true_range = calc_true_range(
        dataframe,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
    )
    return wilder_mean(true_range, window, min_periods=min_periods)


def add_atr(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"atr{window}"] = calc_atr(
        dataframe,
        window=window,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        min_periods=min_periods,
    )


def calc_realized_vol(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    source_series = numeric_column(dataframe, col)
    return (
        source_series.rolling(resolved_window, min_periods=resolved_window_min_periods).std()
        * np.sqrt(resolved_window)
    )


def add_realized_vol(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"{col}_realized_vol{window}"] = calc_realized_vol(
        dataframe,
        col=col,
        window=window,
        min_periods=min_periods,
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


__all__ = [
    "FEATURE_INFOS",
    "add_atr",
    "add_garman_klass_volatility",
    "add_parkinson_volatility",
    "add_realized_vol",
    "add_rogers_satchell_volatility",
    "add_true_range",
    "calc_atr",
    "calc_garman_klass_volatility",
    "calc_parkinson_volatility",
    "calc_realized_vol",
    "calc_rogers_satchell_volatility",
    "calc_true_range",
]
