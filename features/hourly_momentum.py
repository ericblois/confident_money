from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from FMP.company_profile import fmp_get_company_profile
from FMP.hourly_data import fmp_get_hourly_dataframe
from .core import add_log_return, calc_log_return
from .momentum import add_momentum
from .relative import (
    add_rel_momentum,
    add_rel_return,
    add_rel_trend_r2,
    add_rel_trend_slope,
)
from .trends import (
    add_breakout_distance,
    add_range_position,
    add_trend_r2,
    add_trend_slope,
)
from .utils import add_distance_to_col, calc_log_value
from .volatility import add_realized_vol
from .volume import add_vwap


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

    for trading_days in vwap_days:
        window = max(1, int(trading_days) * bars_per_day)
        vwap_col = f"vwap_{trading_days}d"
        add_vwap(
            prepared_dataframe,
            window,
            output_col=vwap_col,
            min_periods=window,
        )
        add_distance_to_col(
            prepared_dataframe,
            "close",
            vwap_col,
            output_col=f"distance_to_vwap_{trading_days}d",
        )

    _merge_benchmark_frames(prepared_dataframe, resolved_benchmark_frames)
    for label, window in lookback_windows.items():
        log_return_col = f"log_return_{label}"
        realized_vol_col = f"realized_vol_{label}"

        add_log_return(
            prepared_dataframe,
            "log_close",
            window,
            output_col=log_return_col,
        )
        add_realized_vol(
            prepared_dataframe,
            "log_return_1h",
            window,
            output_col=realized_vol_col,
            min_periods=window,
        )
        add_momentum(
            prepared_dataframe,
            log_return_col,
            realized_vol_col,
            output_col=f"momentum_{label}",
        )
        add_trend_slope(
            prepared_dataframe,
            "log_close",
            window,
            output_col=f"trend_slope_{label}",
        )
        add_trend_r2(
            prepared_dataframe,
            "log_close",
            window,
            output_col=f"trend_r2_{label}",
        )
        add_breakout_distance(
            prepared_dataframe,
            "close",
            window,
            output_col=f"breakout_distance_{label}",
            min_periods=window,
        )
        add_range_position(
            prepared_dataframe,
            "close",
            window,
            output_col=f"range_position_{label}",
            min_periods=window,
        )

        for benchmark_frame in resolved_benchmark_frames:
            benchmark_name = benchmark_frame.name
            rel_return_col = f"{benchmark_name}_rel_return_{label}"

            add_rel_return(
                prepared_dataframe,
                log_return_col,
                f"{benchmark_name}_log_close",
                window,
                output_col=rel_return_col,
            )
            add_rel_momentum(
                prepared_dataframe,
                rel_return_col,
                "log_return_1h",
                f"{benchmark_name}_log_return_1h",
                window,
                output_col=f"{benchmark_name}_rel_momentum_{label}",
                min_periods=window,
            )
            add_rel_trend_slope(
                prepared_dataframe,
                "log_close",
                f"{benchmark_name}_log_close",
                window,
                output_col=f"{benchmark_name}_rel_trend_slope_{label}",
            )
            add_rel_trend_r2(
                prepared_dataframe,
                "log_close",
                f"{benchmark_name}_log_close",
                window,
                output_col=f"{benchmark_name}_rel_trend_r2_{label}",
            )

    return prepared_dataframe


def resolve_sector_benchmark_symbol(
    symbol: str,
    *,
    use_cache: bool = True,
) -> str | None:
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
    prepared_dataframe["log_close"] = calc_log_value(prepared_dataframe, "close")
    prepared_dataframe["log_return_1h"] = calc_log_return(
        prepared_dataframe,
        "log_close",
        1,
    )
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


__all__ = [
    "BenchmarkFrame",
    "DEFAULT_MARKET_SYMBOL",
    "DEFAULT_MOMENTUM_LOOKBACK_DAYS",
    "DEFAULT_VWAP_LOOKBACK_DAYS",
    "DEFAULT_WARMUP_TRADING_DAYS",
    "SECTOR_ETF_BY_SECTOR",
    "add_hourly_momentum_columns",
    "get_hourly_momentum_dataframe",
    "resolve_sector_benchmark_symbol",
]
