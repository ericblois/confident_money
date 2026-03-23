from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from FMP.company_profile import fmp_get_company_profile
from FMP.hourly_data import fmp_get_hourly_dataframe


DEFAULT_MARKET_SYMBOL = "SPY"
DEFAULT_MOMENTUM_LOOKBACK_DAYS: dict[str, int] = {
    "1d": 1,
    "3d": 3,
    "1w": 5,
    "2w": 10,
    "1m": 21,
}
DEFAULT_VWAP_LOOKBACK_DAYS: tuple[int, ...] = (20, 60)
DEFAULT_WARMUP_TRADING_DAYS = 90
SECTOR_ETF_BY_SECTOR: dict[str, str] = {
    "Basic Materials": "XLB",
    "Communication Services": "XLC",
    "Consumer Cyclical": "XLY",
    "Consumer Defensive": "XLP",
    "Energy": "XLE",
    "Financial Services": "XLF",
    "Healthcare": "XLV",
    "Industrials": "XLI",
    "Real Estate": "XLRE",
    "Technology": "XLK",
    "Utilities": "XLU",
}


@dataclass(frozen=True, slots=True)
class BenchmarkFrame:
    name: str
    symbol: str
    dataframe: pd.DataFrame


# The public entrypoint fetches enough warmup history for rolling windows, then trims
# the result back to the requested range once all features have been calculated.
def get_hourly_momentum_dataframe(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    *,
    verbose: bool = True,
    use_cache: bool = True,
    market_symbol: str = DEFAULT_MARKET_SYMBOL,
    sector_symbol: str | None = None,
    industry_symbol: str | None = None,
    warmup_trading_days: int = DEFAULT_WARMUP_TRADING_DAYS,
    lookback_days: Mapping[str, int] | None = None,
    vwap_days: Sequence[int] = DEFAULT_VWAP_LOOKBACK_DAYS,
) -> pd.DataFrame:
    analysis_start_date = start_date - timedelta(
        days=_trading_days_to_calendar_days(warmup_trading_days)
    )
    hourly_dataframe = fmp_get_hourly_dataframe(
        symbol,
        analysis_start_date,
        end_date,
        verbose=verbose,
        use_cache=use_cache,
    )

    resolved_sector_symbol = sector_symbol or resolve_sector_benchmark_symbol(
        symbol,
        use_cache=use_cache,
    )

    benchmark_frames: list[BenchmarkFrame] = []
    if market_symbol:
        benchmark_frames.append(
            BenchmarkFrame(
                name="market",
                symbol=market_symbol.upper(),
                dataframe=(
                    hourly_dataframe
                    if market_symbol.upper() == symbol.upper()
                    else fmp_get_hourly_dataframe(
                        market_symbol,
                        analysis_start_date,
                        end_date,
                        verbose=verbose,
                        use_cache=use_cache,
                    )
                ),
            )
        )

    if resolved_sector_symbol:
        benchmark_frames.append(
            BenchmarkFrame(
                name="sector",
                symbol=resolved_sector_symbol.upper(),
                dataframe=(
                    hourly_dataframe
                    if resolved_sector_symbol.upper() == symbol.upper()
                    else fmp_get_hourly_dataframe(
                        resolved_sector_symbol,
                        analysis_start_date,
                        end_date,
                        verbose=verbose,
                        use_cache=use_cache,
                    )
                ),
            )
        )

    if industry_symbol:
        benchmark_frames.append(
            BenchmarkFrame(
                name="industry",
                symbol=industry_symbol.upper(),
                dataframe=(
                    hourly_dataframe
                    if industry_symbol.upper() == symbol.upper()
                    else fmp_get_hourly_dataframe(
                        industry_symbol,
                        analysis_start_date,
                        end_date,
                        verbose=verbose,
                        use_cache=use_cache,
                    )
                ),
            )
        )

    momentum_dataframe = add_hourly_momentum_columns(
        hourly_dataframe,
        benchmark_frames=benchmark_frames,
        lookback_days=lookback_days,
        vwap_days=vwap_days,
    )
    filtered_dataframe = _filter_to_requested_range(momentum_dataframe, start_date, end_date)
    filtered_dataframe.attrs["momentum_context"] = {
        "symbol": symbol.upper(),
        "market_symbol": market_symbol.upper() if market_symbol else None,
        "sector_symbol": resolved_sector_symbol.upper() if resolved_sector_symbol else None,
        "industry_symbol": industry_symbol.upper() if industry_symbol else None,
        "warmup_trading_days": warmup_trading_days,
    }

    return filtered_dataframe


# This is the core reusable transformer. It accepts any hourly dataframe that matches
# the existing FMP shape and appends momentum/trend columns in-place on a copy.
def add_hourly_momentum_columns(
    hourly_dataframe: pd.DataFrame,
    *,
    market_dataframe: pd.DataFrame | None = None,
    sector_dataframe: pd.DataFrame | None = None,
    industry_dataframe: pd.DataFrame | None = None,
    benchmark_frames: Sequence[BenchmarkFrame] | None = None,
    lookback_days: Mapping[str, int] | None = None,
    vwap_days: Sequence[int] = DEFAULT_VWAP_LOOKBACK_DAYS,
) -> pd.DataFrame:
    prepared_dataframe = _prepare_hourly_dataframe(hourly_dataframe)
    if prepared_dataframe.empty:
        return prepared_dataframe

    resolved_benchmark_frames = [
        *_build_optional_benchmark_frames(
            market_dataframe=market_dataframe,
            sector_dataframe=sector_dataframe,
            industry_dataframe=industry_dataframe,
        ),
        *(benchmark_frames or []),
    ]
    resolved_lookback_days = dict(lookback_days or DEFAULT_MOMENTUM_LOOKBACK_DAYS)
    bars_per_day = _estimate_bars_per_trading_day(prepared_dataframe)
    lookback_windows = {
        label: max(1, int(trading_days) * bars_per_day)
        for label, trading_days in resolved_lookback_days.items()
    }

    prepared_dataframe["bars_per_trading_day"] = bars_per_day
    prepared_dataframe["dollar_volume"] = (
        prepared_dataframe["close"] * prepared_dataframe["volume"]
    )

    _add_vwap_features(prepared_dataframe, bars_per_day, vwap_days)
    _merge_benchmark_frames(prepared_dataframe, resolved_benchmark_frames)
    _add_horizon_features(prepared_dataframe, lookback_windows, resolved_benchmark_frames)

    return prepared_dataframe


def resolve_sector_benchmark_symbol(
    symbol: str,
    *,
    use_cache: bool = True,
) -> str | None:
    """Map a company profile sector to a liquid sector ETF proxy."""
    try:
        profile = fmp_get_company_profile(symbol, use_cache=use_cache)
    except (OSError, RuntimeError):
        return None

    if profile is None:
        return None

    sector = str(profile.get("sector") or "").strip()
    return SECTOR_ETF_BY_SECTOR.get(sector)


def _prepare_hourly_dataframe(hourly_dataframe: pd.DataFrame) -> pd.DataFrame:
    required_columns = {"date", "close", "volume"}
    missing_columns = sorted(required_columns - set(hourly_dataframe.columns))
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Hourly dataframe is missing required columns: {missing}")

    prepared_dataframe = hourly_dataframe.copy()
    prepared_dataframe["timestamp"] = pd.to_datetime(
        prepared_dataframe["date"],
        errors="coerce",
    )
    prepared_dataframe["close"] = pd.to_numeric(
        prepared_dataframe["close"],
        errors="coerce",
    )
    prepared_dataframe["volume"] = pd.to_numeric(
        prepared_dataframe["volume"],
        errors="coerce",
    ).fillna(0.0)

    prepared_dataframe = prepared_dataframe.loc[
        prepared_dataframe["timestamp"].notna() & prepared_dataframe["close"].gt(0)
    ].copy()
    prepared_dataframe = (
        prepared_dataframe.sort_values("timestamp")
        .drop_duplicates(subset="timestamp", keep="last")
        .reset_index(drop=True)
    )

    prepared_dataframe["trading_day"] = prepared_dataframe["timestamp"].dt.normalize()
    prepared_dataframe["log_close"] = np.log(prepared_dataframe["close"])
    prepared_dataframe["log_return_1h"] = prepared_dataframe["log_close"].diff()
    return prepared_dataframe


def _estimate_bars_per_trading_day(hourly_dataframe: pd.DataFrame) -> int:
    daily_counts = hourly_dataframe.groupby("trading_day")["timestamp"].size()
    if daily_counts.empty:
        return 1

    return max(1, int(round(float(daily_counts.median()))))


def _build_optional_benchmark_frames(
    *,
    market_dataframe: pd.DataFrame | None,
    sector_dataframe: pd.DataFrame | None,
    industry_dataframe: pd.DataFrame | None,
) -> list[BenchmarkFrame]:
    benchmark_frames: list[BenchmarkFrame] = []

    if market_dataframe is not None:
        benchmark_frames.append(
            BenchmarkFrame(name="market", symbol="MARKET", dataframe=market_dataframe)
        )
    if sector_dataframe is not None:
        benchmark_frames.append(
            BenchmarkFrame(name="sector", symbol="SECTOR", dataframe=sector_dataframe)
        )
    if industry_dataframe is not None:
        benchmark_frames.append(
            BenchmarkFrame(name="industry", symbol="INDUSTRY", dataframe=industry_dataframe)
        )

    return benchmark_frames


def _trading_days_to_calendar_days(trading_days: int) -> int:
    return max(7, int(np.ceil((max(1, trading_days) * 7) / 5)) + 7)


def _filter_to_requested_range(
    dataframe: pd.DataFrame,
    start_date: datetime,
    end_date: datetime,
) -> pd.DataFrame:
    if dataframe.empty:
        return dataframe

    return dataframe.loc[
        dataframe["timestamp"].between(start_date, end_date, inclusive="both")
    ].reset_index(drop=True)


def _add_vwap_features(
    dataframe: pd.DataFrame,
    bars_per_day: int,
    vwap_days: Sequence[int],
) -> None:
    price_volume = dataframe["close"] * dataframe["volume"]

    for trading_days in vwap_days:
        window = max(1, int(trading_days) * bars_per_day)
        rolling_volume = dataframe["volume"].rolling(window, min_periods=window).sum()
        rolling_vwap = price_volume.rolling(window, min_periods=window).sum() / (
            rolling_volume.replace(0.0, np.nan)
        )
        dataframe[f"vwap_{trading_days}d"] = rolling_vwap
        dataframe[f"distance_to_vwap_{trading_days}d"] = np.log(
            dataframe["close"] / rolling_vwap
        )


def _merge_benchmark_frames(
    dataframe: pd.DataFrame,
    benchmark_frames: Sequence[BenchmarkFrame],
) -> None:
    for benchmark_frame in benchmark_frames:
        prepared_benchmark = _prepare_hourly_dataframe(benchmark_frame.dataframe).set_index(
            "timestamp"
        )
        for source_column, target_column in (
            ("close", f"{benchmark_frame.name}_close"),
            ("log_close", f"{benchmark_frame.name}_log_close"),
            ("log_return_1h", f"{benchmark_frame.name}_log_return_1h"),
        ):
            dataframe[target_column] = dataframe["timestamp"].map(
                prepared_benchmark[source_column]
            )


def _add_horizon_features(
    dataframe: pd.DataFrame,
    lookback_windows: Mapping[str, int],
    benchmark_frames: Sequence[BenchmarkFrame],
) -> None:
    for label, window in lookback_windows.items():
        realized_volatility = dataframe["log_return_1h"].rolling(
            window,
            min_periods=window,
        ).std() * np.sqrt(window)
        trend_slope, trend_r_squared = _rolling_trend_stats(
            dataframe["log_close"],
            window,
        )
        prior_window_high = dataframe["close"].shift(1).rolling(
            window,
            min_periods=window,
        ).max()
        prior_window_low = dataframe["close"].shift(1).rolling(
            window,
            min_periods=window,
        ).min()

        dataframe[f"log_return_{label}"] = dataframe["log_close"].diff(window)
        dataframe[f"realized_vol_{label}"] = realized_volatility
        dataframe[f"momentum_{label}"] = (
            dataframe[f"log_return_{label}"] / realized_volatility
        )
        dataframe[f"trend_slope_{label}"] = trend_slope
        dataframe[f"trend_r2_{label}"] = trend_r_squared
        dataframe[f"breakout_distance_{label}"] = np.log(
            dataframe["close"] / prior_window_high
        )
        dataframe[f"range_position_{label}"] = (
            (dataframe["close"] - prior_window_low)
            / (prior_window_high - prior_window_low).replace(0.0, np.nan)
        )

        for benchmark_frame in benchmark_frames:
            _add_relative_horizon_features(
                dataframe,
                benchmark_frame.name,
                label,
                window,
            )


def _add_relative_horizon_features(
    dataframe: pd.DataFrame,
    benchmark_name: str,
    label: str,
    window: int,
) -> None:
    benchmark_log_close_column = f"{benchmark_name}_log_close"
    benchmark_log_return_column = f"{benchmark_name}_log_return_1h"
    if benchmark_log_close_column not in dataframe.columns:
        return

    relative_log_spread = dataframe["log_close"] - dataframe[benchmark_log_close_column]
    relative_trend_slope, relative_trend_r_squared = _rolling_trend_stats(
        relative_log_spread,
        window,
    )
    benchmark_log_return = dataframe[benchmark_log_close_column].diff(window)
    tracking_volatility = (
        (dataframe["log_return_1h"] - dataframe[benchmark_log_return_column])
        .rolling(window, min_periods=window)
        .std()
        * np.sqrt(window)
    )

    dataframe[f"{benchmark_name}_relative_return_{label}"] = (
        dataframe[f"log_return_{label}"] - benchmark_log_return
    )
    dataframe[f"{benchmark_name}_relative_momentum_{label}"] = (
        dataframe[f"{benchmark_name}_relative_return_{label}"] / tracking_volatility
    )
    dataframe[f"{benchmark_name}_relative_trend_slope_{label}"] = relative_trend_slope
    dataframe[f"{benchmark_name}_relative_trend_r2_{label}"] = relative_trend_r_squared


# Fixed-window regression can be vectorized because every rolling fit uses the same
# x-axis: 0..window-1. That keeps the trend features fast and easy to reuse.
def _rolling_trend_stats(series: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
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
