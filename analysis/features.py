from __future__ import annotations

import numpy as np
import pandas as pd


def add_mv_avg(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    min_periods: int = 1,
) -> None:
    """Add a rolling moving average column based on an existing dataframe column.

    By default the new column is named `"{col}_ma{window}"`.
    """
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")
    if window <= 0:
        raise ValueError("window must be greater than 0.")
    if min_periods <= 0:
        raise ValueError("min_periods must be greater than 0.")

    source_series = pd.to_numeric(dataframe[col], errors="coerce")
    dataframe[f"{col}_ma{window}"] = source_series.rolling(
        window=window,
        min_periods=min_periods,
    ).mean()


def add_vwap(
    dataframe: pd.DataFrame,
    window: int,
    price_col: str = "close",
    volume_col: str = "volume",
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    """Add a volume-weighted average price column from existing price and volume columns.

    The calculation uses a rolling window and writes to `output_col` or a default name.
    """
    if price_col not in dataframe.columns:
        raise ValueError(f"Column '{price_col}' not found in the dataframe.")
    if volume_col not in dataframe.columns:
        raise ValueError(f"Column '{volume_col}' not found in the dataframe.")
    if window <= 0:
        raise ValueError("window must be greater than 0.")

    price_series = pd.to_numeric(dataframe[price_col], errors="coerce")
    volume_series = pd.to_numeric(dataframe[volume_col], errors="coerce")
    price_volume = price_series * volume_series
    min_per = window if min_periods is None else min_periods
    if min_per <= 0:
        raise ValueError("min_periods must be greater than 0.")

    rolling_volume = volume_series.rolling(window, min_periods=min_per).sum()
    dataframe[output_col or f"{price_col}_vwap{window}"] = (
        price_volume.rolling(window, min_periods=min_per).sum()
        / rolling_volume.replace(0.0, np.nan)
    )


def add_distance_to_col(
    dataframe: pd.DataFrame,
    col: str,
    reference_col: str,
    output_col: str | None = None,
) -> None:
    """Add a log-distance column between one dataframe column and a reference column.

    This is computed as `log(col / reference_col)`.
    """
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")
    if reference_col not in dataframe.columns:
        raise ValueError(f"Column '{reference_col}' not found in the dataframe.")

    source_series = pd.to_numeric(dataframe[col], errors="coerce")
    reference_series = pd.to_numeric(dataframe[reference_col], errors="coerce")
    dataframe[output_col or f"{col}_distance_to_{reference_col}"] = np.log(
        source_series / reference_series
    )


def add_log_return(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    """Add a lookback return column by differencing an existing series over `window` rows.

    This is typically used with log-price columns to produce log returns.
    """
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")
    if window <= 0:
        raise ValueError("window must be greater than 0.")

    source_series = pd.to_numeric(dataframe[col], errors="coerce")
    dataframe[output_col or f"{col}_log_return{window}"] = source_series.diff(window)


def add_realized_vol(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    """Add a rolling realized volatility column from an existing return series.

    The result is the rolling standard deviation scaled by `sqrt(window)`.
    """
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")
    if window <= 0:
        raise ValueError("window must be greater than 0.")

    resolved_min_periods = window if min_periods is None else min_periods
    if resolved_min_periods <= 0:
        raise ValueError("min_periods must be greater than 0.")

    source_series = pd.to_numeric(dataframe[col], errors="coerce")
    dataframe[output_col or f"{col}_realized_vol{window}"] = (
        source_series.rolling(window, min_periods=resolved_min_periods).std()
        * np.sqrt(window)
    )


def add_momentum(
    dataframe: pd.DataFrame,
    return_col: str,
    volatility_col: str,
    output_col: str | None = None,
) -> None:
    """Add a momentum column by dividing a return column by a volatility column.

    Zero volatility values are treated as missing to avoid divide-by-zero output.
    """
    if return_col not in dataframe.columns:
        raise ValueError(f"Column '{return_col}' not found in the dataframe.")
    if volatility_col not in dataframe.columns:
        raise ValueError(f"Column '{volatility_col}' not found in the dataframe.")

    return_series = pd.to_numeric(dataframe[return_col], errors="coerce")
    volatility_series = pd.to_numeric(dataframe[volatility_col], errors="coerce")
    dataframe[output_col or f"{return_col}_momentum"] = (
        return_series / volatility_series.replace(0.0, np.nan)
    )


def add_trend_slope(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    """Add a rolling trend slope column for an existing series.

    The slope comes from a fixed-window linear regression over each rolling window.
    """
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")
    if window <= 0:
        raise ValueError("window must be greater than 0.")

    source_series = pd.to_numeric(dataframe[col], errors="coerce")
    slope, _ = _rolling_trend_stats(source_series, window)
    dataframe[output_col or f"{col}_trend_slope{window}"] = slope


def add_trend_r2(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    """Add a rolling trend R-squared column for an existing series.

    This measures how well a straight-line trend fits each rolling window.
    """
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")
    if window <= 0:
        raise ValueError("window must be greater than 0.")

    source_series = pd.to_numeric(dataframe[col], errors="coerce")
    _, r_squared = _rolling_trend_stats(source_series, window)
    dataframe[output_col or f"{col}_trend_r2{window}"] = r_squared


def add_breakout_distance(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    """Add a breakout-distance column relative to the prior rolling high.

    The value is computed as `log(col / prior_window_high)`.
    """
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")
    if window <= 0:
        raise ValueError("window must be greater than 0.")

    resolved_min_periods = window if min_periods is None else min_periods
    if resolved_min_periods <= 0:
        raise ValueError("min_periods must be greater than 0.")

    source_series = pd.to_numeric(dataframe[col], errors="coerce")
    prior_window_high = source_series.shift(1).rolling(
        window,
        min_periods=resolved_min_periods,
    ).max()
    dataframe[output_col or f"{col}_breakout_distance{window}"] = np.log(
        source_series / prior_window_high
    )


def add_range_position(
    dataframe: pd.DataFrame,
    col: str,
    window: int,
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    """Add a normalized range-position column within the prior rolling high-low range.

    Values near 0 are close to the prior low and values near 1 are close to the prior high.
    """
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")
    if window <= 0:
        raise ValueError("window must be greater than 0.")

    resolved_min_periods = window if min_periods is None else min_periods
    if resolved_min_periods <= 0:
        raise ValueError("min_periods must be greater than 0.")

    source_series = pd.to_numeric(dataframe[col], errors="coerce")
    prior_window_high = source_series.shift(1).rolling(
        window,
        min_periods=resolved_min_periods,
    ).max()
    prior_window_low = source_series.shift(1).rolling(
        window,
        min_periods=resolved_min_periods,
    ).min()
    dataframe[output_col or f"{col}_range_position{window}"] = (
        (source_series - prior_window_low)
        / (prior_window_high - prior_window_low).replace(0.0, np.nan)
    )


def add_rel_return(
    dataframe: pd.DataFrame,
    return_col: str,
    benchmark_col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    """Add a relative return column by comparing an asset return to a benchmark lookback return.

    The benchmark contribution is computed from `benchmark_col.diff(window)`.
    """
    if return_col not in dataframe.columns:
        raise ValueError(f"Column '{return_col}' not found in the dataframe.")
    if benchmark_col not in dataframe.columns:
        raise ValueError(f"Column '{benchmark_col}' not found in the dataframe.")
    if window <= 0:
        raise ValueError("window must be greater than 0.")

    return_series = pd.to_numeric(dataframe[return_col], errors="coerce")
    benchmark_series = pd.to_numeric(dataframe[benchmark_col], errors="coerce")
    dataframe[output_col or f"{return_col}_rel_to_{benchmark_col}"] = (
        return_series - benchmark_series.diff(window)
    )


def add_rel_momentum(
    dataframe: pd.DataFrame,
    rel_return_col: str,
    return_col: str,
    benchmark_return_col: str,
    window: int,
    output_col: str | None = None,
    min_periods: int | None = None,
) -> None:
    """Add a relative momentum column by scaling relative return by tracking volatility.

    Tracking volatility is based on the rolling spread between asset and benchmark returns.
    """
    if rel_return_col not in dataframe.columns:
        raise ValueError(f"Column '{rel_return_col}' not found in the dataframe.")
    if return_col not in dataframe.columns:
        raise ValueError(f"Column '{return_col}' not found in the dataframe.")
    if benchmark_return_col not in dataframe.columns:
        raise ValueError(f"Column '{benchmark_return_col}' not found in the dataframe.")
    if window <= 0:
        raise ValueError("window must be greater than 0.")

    min_per = window if min_periods is None else min_periods
    if min_per <= 0:
        raise ValueError("min_periods must be greater than 0.")

    rel_return_series = pd.to_numeric(dataframe[rel_return_col], errors="coerce")
    return_series = pd.to_numeric(dataframe[return_col], errors="coerce")
    benchmark_return_series = pd.to_numeric(
        dataframe[benchmark_return_col],
        errors="coerce",
    )
    tracking_volatility = (
        (return_series - benchmark_return_series)
        .rolling(window, min_periods=min_per)
        .std()
        * np.sqrt(window)
    )
    dataframe[output_col or f"{rel_return_col}_momentum"] = (
        rel_return_series / tracking_volatility.replace(0.0, np.nan)
    )


def add_rel_trend_slope(
    dataframe: pd.DataFrame,
    col: str,
    benchmark_col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    """Add a rolling trend slope column for the spread between an asset and benchmark series.

    This captures whether the asset is trending stronger or weaker than the benchmark.
    """
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")
    if benchmark_col not in dataframe.columns:
        raise ValueError(f"Column '{benchmark_col}' not found in the dataframe.")
    if window <= 0:
        raise ValueError("window must be greater than 0.")

    source_series = pd.to_numeric(dataframe[col], errors="coerce")
    benchmark_series = pd.to_numeric(dataframe[benchmark_col], errors="coerce")
    slope, _ = _rolling_trend_stats(source_series - benchmark_series, window)
    dataframe[output_col or f"{col}_rel_trend_slope{window}"] = slope


def add_rel_trend_r2(
    dataframe: pd.DataFrame,
    col: str,
    benchmark_col: str,
    window: int,
    output_col: str | None = None,
) -> None:
    """Add a rolling trend R-squared column for the spread between an asset and benchmark series.

    This measures how consistently the relative trend follows a straight line.
    """
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")
    if benchmark_col not in dataframe.columns:
        raise ValueError(f"Column '{benchmark_col}' not found in the dataframe.")
    if window <= 0:
        raise ValueError("window must be greater than 0.")

    source_series = pd.to_numeric(dataframe[col], errors="coerce")
    benchmark_series = pd.to_numeric(dataframe[benchmark_col], errors="coerce")
    _, r_squared = _rolling_trend_stats(source_series - benchmark_series, window)
    dataframe[output_col or f"{col}_rel_trend_r2{window}"] = r_squared


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
