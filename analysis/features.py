from __future__ import annotations

import numpy as np
import pandas as pd


def calc_log_value(dataframe: pd.DataFrame, col: str) -> pd.Series:
    """Return the natural log of a numeric dataframe column."""
    source_series = _numeric_column(dataframe, col)
    return np.log(source_series.where(source_series > 0))


def add_log_value(
    dataframe: pd.DataFrame,
    col: str,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"log_{col}"] = calc_log_value(dataframe, col)


def calc_mv_avg(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int = 1,
) -> pd.Series:
    """Return a rolling moving average based on an existing dataframe column."""
    resolved_window = _positive_int(window, name="window")
    resolved_min_periods = _positive_int(min_periods, name="min_periods")
    source_series = _numeric_column(dataframe, col)
    return source_series.rolling(
        window=resolved_window,
        min_periods=resolved_min_periods,
    ).mean()


def add_mv_avg(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int = 1,
) -> None:
    dataframe[f"{col}_ma{window}"] = calc_mv_avg(
        dataframe,
        col,
        window,
        min_periods=min_periods,
    )


def calc_vwap(
    dataframe: pd.DataFrame,
    window: int,
    price_col: str = "close",
    volume_col: str = "volume",
    min_periods: int | None = None,
) -> pd.Series:
    """Return a rolling volume-weighted average price series."""
    resolved_window = _positive_int(window, name="window")
    resolved_min_periods = _resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    price_series = _numeric_column(dataframe, price_col)
    volume_series = _numeric_column(dataframe, volume_col)
    rolling_volume = volume_series.rolling(
        resolved_window,
        min_periods=resolved_min_periods,
    ).sum()
    return (
        (price_series * volume_series)
        .rolling(resolved_window, min_periods=resolved_min_periods)
        .sum()
        / rolling_volume.replace(0.0, np.nan)
    )


def add_vwap(
    dataframe: pd.DataFrame,
    window: int,
    price_col: str = "close",
    volume_col: str = "volume",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"{price_col}_vwap{window}"] = calc_vwap(
        dataframe,
        window,
        price_col=price_col,
        volume_col=volume_col,
        min_periods=min_periods,
    )


def calc_distance_to_col(
    dataframe: pd.DataFrame,
    col: str,
    reference_col: str,
) -> pd.Series:
    """Return the log-distance between one dataframe column and a reference column."""
    source_series = _numeric_column(dataframe, col)
    reference_series = _numeric_column(dataframe, reference_col)
    return np.log(source_series / reference_series)


def add_distance_to_col(
    dataframe: pd.DataFrame,
    col: str,
    reference_col: str,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_distance_to_{reference_col}"] = calc_distance_to_col(
        dataframe,
        col,
        reference_col,
    )


def calc_log_return(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
) -> pd.Series:
    """Return a lookback return series by differencing over `window` rows."""
    resolved_window = _positive_int(window, name="window")
    source_series = _numeric_column(dataframe, col)
    return source_series.diff(resolved_window)


def add_log_return(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_log_return{window}"] = calc_log_return(
        dataframe,
        col,
        window,
    )


def calc_realized_vol(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int | None = None,
) -> pd.Series:
    """Return rolling realized volatility from an existing return series."""
    resolved_window = _positive_int(window, name="window")
    resolved_min_periods = _resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    source_series = _numeric_column(dataframe, col)
    return (
        source_series.rolling(resolved_window, min_periods=resolved_min_periods).std()
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
        col,
        window,
        min_periods=min_periods,
    )


def calc_momentum(
    dataframe: pd.DataFrame,
    return_col: str,
    volatility_col: str,
) -> pd.Series:
    """Return momentum by dividing a return column by a volatility column."""
    return_series = _numeric_column(dataframe, return_col)
    volatility_series = _numeric_column(dataframe, volatility_col)
    return return_series / volatility_series.replace(0.0, np.nan)


def add_momentum(
    dataframe: pd.DataFrame,
    return_col: str,
    volatility_col: str,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{return_col}_momentum"] = calc_momentum(
        dataframe,
        return_col,
        volatility_col,
    )


def calc_trend_slope(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
) -> pd.Series:
    """Return a rolling trend slope series for an existing column."""
    resolved_window = _positive_int(window, name="window")
    source_series = _numeric_column(dataframe, col)
    slope, _ = _rolling_trend_stats(source_series, resolved_window)
    return slope


def add_trend_slope(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_trend_slope{window}"] = calc_trend_slope(
        dataframe,
        col,
        window,
    )


def calc_trend_r2(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
) -> pd.Series:
    """Return a rolling trend R-squared series for an existing column."""
    resolved_window = _positive_int(window, name="window")
    source_series = _numeric_column(dataframe, col)
    _, r_squared = _rolling_trend_stats(source_series, resolved_window)
    return r_squared


def add_trend_r2(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_trend_r2{window}"] = calc_trend_r2(
        dataframe,
        col,
        window,
    )


def calc_breakout_distance(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int | None = None,
) -> pd.Series:
    """Return the log-distance to the prior rolling high."""
    resolved_window = _positive_int(window, name="window")
    resolved_min_periods = _resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    source_series = _numeric_column(dataframe, col)
    prior_window_high = source_series.shift(1).rolling(
        resolved_window,
        min_periods=resolved_min_periods,
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
        col,
        window,
        min_periods=min_periods,
    )


def calc_range_position(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int | None = None,
) -> pd.Series:
    """Return a normalized range position within the prior rolling high-low range."""
    resolved_window = _positive_int(window, name="window")
    resolved_min_periods = _resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    source_series = _numeric_column(dataframe, col)
    prior_window_high = source_series.shift(1).rolling(
        resolved_window,
        min_periods=resolved_min_periods,
    ).max()
    prior_window_low = source_series.shift(1).rolling(
        resolved_window,
        min_periods=resolved_min_periods,
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
        col,
        window,
        min_periods=min_periods,
    )


def calc_rel_return(
    dataframe: pd.DataFrame,
    return_col: str,
    benchmark_col: str,
    window: int,
) -> pd.Series:
    """Return relative return versus a benchmark lookback return."""
    resolved_window = _positive_int(window, name="window")
    return_series = _numeric_column(dataframe, return_col)
    benchmark_series = _numeric_column(dataframe, benchmark_col)
    return return_series - benchmark_series.diff(resolved_window)


def add_rel_return(
    dataframe: pd.DataFrame,
    return_col: str,
    benchmark_col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{return_col}_rel_to_{benchmark_col}"] = calc_rel_return(
        dataframe,
        return_col,
        benchmark_col,
        window,
    )


def calc_rel_momentum(
    dataframe: pd.DataFrame,
    rel_return_col: str,
    return_col: str,
    benchmark_return_col: str,
    window: int,
    min_periods: int | None = None,
) -> pd.Series:
    """Return relative momentum scaled by rolling tracking volatility."""
    resolved_window = _positive_int(window, name="window")
    resolved_min_periods = _resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    rel_return_series = _numeric_column(dataframe, rel_return_col)
    return_series = _numeric_column(dataframe, return_col)
    benchmark_return_series = _numeric_column(dataframe, benchmark_return_col)
    tracking_volatility = (
        (return_series - benchmark_return_series)
        .rolling(resolved_window, min_periods=resolved_min_periods)
        .std()
        * np.sqrt(resolved_window)
    )
    return rel_return_series / tracking_volatility.replace(0.0, np.nan)


def add_rel_momentum(
    dataframe: pd.DataFrame,
    rel_return_col: str,
    return_col: str,
    benchmark_return_col: str,
    window: int,
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    dataframe[output_col or f"{rel_return_col}_momentum"] = calc_rel_momentum(
        dataframe,
        rel_return_col,
        return_col,
        benchmark_return_col,
        window,
        min_periods=min_periods,
    )


def calc_rel_trend_slope(
    dataframe: pd.DataFrame,
    col: str,
    benchmark_col: str,
    window: int,
) -> pd.Series:
    """Return a rolling trend slope for the spread between two series."""
    resolved_window = _positive_int(window, name="window")
    source_series = _numeric_column(dataframe, col)
    benchmark_series = _numeric_column(dataframe, benchmark_col)
    slope, _ = _rolling_trend_stats(source_series - benchmark_series, resolved_window)
    return slope


def add_rel_trend_slope(
    dataframe: pd.DataFrame,
    col: str,
    benchmark_col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_rel_trend_slope{window}"] = calc_rel_trend_slope(
        dataframe,
        col,
        benchmark_col,
        window,
    )


def calc_rel_trend_r2(
    dataframe: pd.DataFrame,
    col: str,
    benchmark_col: str,
    window: int,
) -> pd.Series:
    """Return a rolling trend R-squared for the spread between two series."""
    resolved_window = _positive_int(window, name="window")
    source_series = _numeric_column(dataframe, col)
    benchmark_series = _numeric_column(dataframe, benchmark_col)
    _, r_squared = _rolling_trend_stats(source_series - benchmark_series, resolved_window)
    return r_squared


def add_rel_trend_r2(
    dataframe: pd.DataFrame,
    col: str,
    benchmark_col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_rel_trend_r2{window}"] = calc_rel_trend_r2(
        dataframe,
        col,
        benchmark_col,
        window,
    )


def _numeric_column(dataframe: pd.DataFrame, col: str) -> pd.Series:
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")

    return pd.to_numeric(dataframe[col], errors="coerce")


def _positive_int(value: int, *, name: str) -> int:
    if value <= 0:
        raise ValueError(f"{name} must be greater than 0.")

    return value


def _resolved_min_periods(min_periods: int | None, *, default_value: int) -> int:
    resolved_min_periods = default_value if min_periods is None else min_periods
    return _positive_int(resolved_min_periods, name="min_periods")


def _rolling_trend_stats(series: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    """Return rolling linear-regression slope and R-squared for a series.

    The implementation is vectorized for fixed-size windows so trend features stay fast.
    """
    if window < 2:
        empty_series = pd.Series(np.nan, index=series.index, dtype=float)
        return empty_series, empty_series

    y_values = pd.to_numeric(series, errors="coerce").astype(float)
    global_index = pd.Series(np.arange(len(y_values), dtype=float), index=series.index)

    sum_y = y_values.rolling(window, min_periods=window).sum()
    sum_y_squared = y_values.pow(2).rolling(window, min_periods=window).sum()
    sum_index_y = (y_values * global_index).rolling(window, min_periods=window).sum()

    sum_x = window * (window - 1) / 2.0
    sum_x_squared = (window - 1) * window * (2 * window - 1) / 6.0
    x_variance_term = (window * sum_x_squared) - (sum_x**2)

    window_start = global_index - (window - 1)
    sum_xy = sum_index_y - (window_start * sum_y)
    covariance_term = (window * sum_xy) - (sum_x * sum_y)
    y_variance_term = (window * sum_y_squared) - (sum_y**2)

    slope = covariance_term / x_variance_term
    denominator = np.sqrt(x_variance_term * y_variance_term.clip(lower=0.0))
    correlation = covariance_term / denominator.replace(0.0, np.nan)
    r_squared = correlation.clip(-1.0, 1.0).pow(2)

    return slope, r_squared
