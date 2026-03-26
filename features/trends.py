from __future__ import annotations

import numpy as np
import pandas as pd

from ._shared import (
    feature_arg,
    feature_info,
    numeric_column,
    positive_int,
    resolved_min_periods,
    rolling_trend_stats,
    wilder_mean,
)
from .volatility import calc_true_range


FEATURE_INFOS = (
    feature_info(
        "ma",
        "Moving Average",
        "trends",
        args=[
            feature_arg("col", "Source Column", "source"),
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("min_periods", "Minimum Periods", "min_periods", 1),
        ],
    ),
    feature_info(
        "ema",
        "Exponential Moving Average",
        "trends",
        args=[
            feature_arg("col", "Source Column", "source"),
            feature_arg("span", "Span Periods", "periods"),
            feature_arg("min_periods", "Minimum Periods", "min_periods", 1),
            feature_arg("adjust", "Adjust", "boolean_flag", False),
        ],
    ),
    feature_info(
        "trend_slp",
        "Trend Slope",
        "trends",
        args=[
            feature_arg("col", "Source Column", "source"),
            feature_arg("window", "Lookback Periods", "periods"),
        ],
    ),
    feature_info(
        "trend_r2",
        "Trend R-Squared",
        "trends",
        args=[
            feature_arg("col", "Source Column", "source"),
            feature_arg("window", "Lookback Periods", "periods"),
        ],
    ),
    feature_info(
        "adx",
        "Average Directional Index",
        "trends",
        args=[
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("high", "High Column", "high_source", "high"),
            feature_arg("low", "Low Column", "low_source", "low"),
            feature_arg("close", "Close Column", "close_source", "close"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
    feature_info(
        "brk_dist",
        "Breakout Distance",
        "trends",
        args=[
            feature_arg("col", "Source Column", "source"),
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
    feature_info(
        "rng_pos",
        "Range Position",
        "trends",
        args=[
            feature_arg("col", "Source Column", "source"),
            feature_arg("window", "Lookback Periods", "periods"),
            feature_arg("min_periods", "Minimum Periods", "min_periods"),
        ],
    ),
)


def calc_mv_avg(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int = 1,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = positive_int(min_periods, name="min_periods")
    return numeric_column(dataframe, col).rolling(
        window=resolved_window,
        min_periods=resolved_window_min_periods,
    ).mean()


def add_mv_avg(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int = 1,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_ma{window}"] = calc_mv_avg(
        dataframe,
        col=col,
        window=window,
        min_periods=min_periods,
    )


def calc_ema(
    dataframe: pd.DataFrame,
    col: str,
    span: int,
    min_periods: int = 1,
    adjust: bool = False,
) -> pd.Series:
    resolved_span = positive_int(span, name="span")
    resolved_span_min_periods = positive_int(min_periods, name="min_periods")
    return numeric_column(dataframe, col).ewm(
        span=resolved_span,
        adjust=adjust,
        min_periods=resolved_span_min_periods,
    ).mean()


def add_ema(
    dataframe: pd.DataFrame,
    col: str,
    span: int,
    output_col: str | None = None,
    min_periods: int = 1,
    adjust: bool = False,
) -> None:
    dataframe[output_col or f"{col}_ema{span}"] = calc_ema(
        dataframe,
        col=col,
        span=span,
        min_periods=min_periods,
        adjust=adjust,
    )


def calc_trend_slope(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
) -> pd.Series:
    slope, _ = rolling_trend_stats(numeric_column(dataframe, col), window)
    return slope


def add_trend_slope(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_trend_slope{window}"] = calc_trend_slope(
        dataframe,
        col=col,
        window=window,
    )


def calc_trend_r2(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
) -> pd.Series:
    _, r_squared = rolling_trend_stats(numeric_column(dataframe, col), window)
    return r_squared


def add_trend_r2(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_trend_r2{window}"] = calc_trend_r2(
        dataframe,
        col=col,
        window=window,
    )


def calc_adx(
    dataframe: pd.DataFrame,
    window: int,
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
    up_move = high_series.diff()
    down_move = -low_series.diff()
    plus_dm = up_move.where((up_move > down_move) & (up_move > 0.0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0.0), 0.0)
    atr = wilder_mean(
        calc_true_range(
            dataframe,
            high_col=high_col,
            low_col=low_col,
            close_col=close_col,
        ),
        resolved_window,
        min_periods=resolved_window_min_periods,
    )
    plus_di = 100.0 * wilder_mean(
        plus_dm,
        resolved_window,
        min_periods=resolved_window_min_periods,
    ) / atr.replace(0.0, np.nan)
    minus_di = 100.0 * wilder_mean(
        minus_dm,
        resolved_window,
        min_periods=resolved_window_min_periods,
    ) / atr.replace(0.0, np.nan)
    directional_spread = (plus_di - minus_di).abs()
    directional_sum = (plus_di + minus_di).replace(0.0, np.nan)
    dx = 100.0 * directional_spread / directional_sum
    return wilder_mean(dx, resolved_window, min_periods=resolved_window_min_periods)


def add_adx(
    dataframe: pd.DataFrame,
    window: int,
    high_col: str = "high",
    low_col: str = "low",
    close_col: str = "close",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"adx{window}"] = calc_adx(
        dataframe,
        window=window,
        high_col=high_col,
        low_col=low_col,
        close_col=close_col,
        min_periods=min_periods,
    )


def calc_breakout_distance(
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
    prior_window_high = source_series.shift(1).rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).max()
    return np.log(source_series / prior_window_high)


def add_breakout_distance(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"{col}_breakout_distance{window}"] = calc_breakout_distance(
        dataframe,
        col=col,
        window=window,
        min_periods=min_periods,
    )


def calc_range_position(
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
    prior_window_high = source_series.shift(1).rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).max()
    prior_window_low = source_series.shift(1).rolling(
        resolved_window,
        min_periods=resolved_window_min_periods,
    ).min()
    return (source_series - prior_window_low) / (
        prior_window_high - prior_window_low
    ).replace(0.0, np.nan)


def add_range_position(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"{col}_range_position{window}"] = calc_range_position(
        dataframe,
        col=col,
        window=window,
        min_periods=min_periods,
    )


__all__ = [
    "FEATURE_INFOS",
    "add_adx",
    "add_breakout_distance",
    "add_ema",
    "add_mv_avg",
    "add_range_position",
    "add_trend_r2",
    "add_trend_slope",
    "calc_adx",
    "calc_breakout_distance",
    "calc_ema",
    "calc_mv_avg",
    "calc_range_position",
    "calc_trend_r2",
    "calc_trend_slope",
]
