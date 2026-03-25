from __future__ import annotations

import numpy as np
import pandas as pd

from ._shared import (
    feature_arg,
    feature_info,
    numeric_column,
    positive_int,
    resolved_min_periods,
    wilder_mean,
)
from .trends import calc_ema


FEATURE_INFOS = (
    feature_info(
        "mom",
        "Momentum",
        "momentum",
        args=[
            feature_arg("return_col", "Return Column", "return_source"),
            feature_arg("volatility_col", "Volatility Column", "volatility_source"),
        ],
    ),
    feature_info(
        "rsi",
        "Relative Strength Index",
        "momentum",
        args=[
            feature_arg("col", "Source Column", "source", "close"),
            feature_arg("window", "Lookback Periods", "periods", 14),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
    feature_info(
        "stoch_k",
        "Stochastic %K",
        "momentum",
        args=[
            feature_arg("window", "Lookback Periods", "periods", 14),
            feature_arg("high_col", "High Column", "high_source", "high"),
            feature_arg("low_col", "Low Column", "low_source", "low"),
            feature_arg("close_col", "Close Column", "close_source", "close"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
    feature_info(
        "stoch_d",
        "Stochastic %D",
        "momentum",
        args=[
            feature_arg("window", "Lookback Periods", "periods", 14),
            feature_arg("signal_window", "Signal Periods", "signal_periods", 3),
            feature_arg("high_col", "High Column", "high_source", "high"),
            feature_arg("low_col", "Low Column", "low_source", "low"),
            feature_arg("close_col", "Close Column", "close_source", "close"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
            feature_arg("signal_min_periods", "Signal Minimum Periods", "min_periods", 1),
        ],
    ),
    feature_info(
        "macd",
        "MACD Line",
        "momentum",
        args=[
            feature_arg("col", "Source Column", "source", "close"),
            feature_arg("fast_span", "Fast Periods", "periods", 12),
            feature_arg("slow_span", "Slow Periods", "periods", 26),
            feature_arg("min_periods", "Minimum Periods", "min_periods", 1),
        ],
    ),
    feature_info(
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
    ),
    feature_info(
        "macd_hist",
        "MACD Histogram",
        "momentum",
        args=[
            feature_arg("col", "Source Column", "source", "close"),
            feature_arg("fast_span", "Fast Periods", "periods", 12),
            feature_arg("slow_span", "Slow Periods", "periods", 26),
            feature_arg("signal_span", "Signal Periods", "signal_periods", 9),
            feature_arg("min_periods", "Minimum Periods", "min_periods", 1),
        ],
    ),
    feature_info(
        "roc",
        "Rate of Change",
        "momentum",
        args=[
            feature_arg("col", "Source Column", "source", "close"),
            feature_arg("window", "Lookback Periods", "periods", 10),
        ],
    ),
    feature_info(
        "will_r",
        "Williams %R",
        "momentum",
        args=[
            feature_arg("window", "Lookback Periods", "periods", 14),
            feature_arg("high_col", "High Column", "high_source", "high"),
            feature_arg("low_col", "Low Column", "low_source", "low"),
            feature_arg("close_col", "Close Column", "close_source", "close"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
)


def calc_momentum(
    dataframe: pd.DataFrame,
    return_col: str,
    volatility_col: str,
) -> pd.Series:
    return_series = numeric_column(dataframe, return_col)
    volatility_series = numeric_column(dataframe, volatility_col)
    return return_series / volatility_series.replace(0.0, np.nan)


def add_momentum(
    dataframe: pd.DataFrame,
    return_col: str,
    volatility_col: str,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{return_col}_momentum"] = calc_momentum(
        dataframe,
        return_col=return_col,
        volatility_col=volatility_col,
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


def calc_stoch_k(
    dataframe: pd.DataFrame,
    window: int = 14,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
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
    rolling_high = high_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).max()
    rolling_low = low_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).min()
    return 100.0 * (close_series - rolling_low) / (rolling_high - rolling_low).replace(0.0, np.nan)


def add_stoch_k(
    dataframe: pd.DataFrame,
    window: int = 14,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"stoch_k{window}"] = calc_stoch_k(
        dataframe,
        window=window,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        min_periods=min_periods,
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


def calc_macd_hist(
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
    signal_series = calc_macd_signal(
        dataframe,
        col=col,
        fast_span=fast_span,
        slow_span=slow_span,
        signal_span=signal_span,
        min_periods=min_periods,
    )
    return macd_series - signal_series


def add_macd_hist(
    dataframe: pd.DataFrame,
    col: str = "close",
    fast_span: int = 12,
    slow_span: int = 26,
    signal_span: int = 9,
    output_col: str | None = None,
    min_periods: int = 1,
) -> None:
    dataframe[output_col or f"{col}_macd_hist{fast_span}_{slow_span}_{signal_span}"] = calc_macd_hist(
        dataframe,
        col=col,
        fast_span=fast_span,
        slow_span=slow_span,
        signal_span=signal_span,
        min_periods=min_periods,
    )


def calc_roc(
    dataframe: pd.DataFrame,
    col: str = "close",
    window: int = 10,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    source_series = numeric_column(dataframe, col)
    return 100.0 * (source_series / source_series.shift(resolved_window) - 1.0)


def add_roc(
    dataframe: pd.DataFrame,
    col: str = "close",
    window: int = 10,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_roc{window}"] = calc_roc(
        dataframe,
        col=col,
        window=window,
    )


def calc_williams_r(
    dataframe: pd.DataFrame,
    window: int = 14,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
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
    rolling_high = high_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).max()
    rolling_low = low_series.rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).min()
    return -100.0 * (rolling_high - close_series) / (rolling_high - rolling_low).replace(
        0.0,
        np.nan,
    )


def add_williams_r(
    dataframe: pd.DataFrame,
    window: int = 14,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"williams_r{window}"] = calc_williams_r(
        dataframe,
        window=window,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        min_periods=min_periods,
    )


__all__ = [
    "FEATURE_INFOS",
    "add_macd",
    "add_macd_hist",
    "add_macd_signal",
    "add_momentum",
    "add_roc",
    "add_rsi",
    "add_stoch_d",
    "add_stoch_k",
    "add_williams_r",
    "calc_macd",
    "calc_macd_hist",
    "calc_macd_signal",
    "calc_momentum",
    "calc_roc",
    "calc_rsi",
    "calc_stoch_d",
    "calc_stoch_k",
    "calc_williams_r",
]
