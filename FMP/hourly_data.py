from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import (
    Any,
    ClassVar,
    Literal,
    Sequence,
    TypedDict,
    TypeGuard,
    cast,
    overload,
)

import pandas as pd

from FMP.api import fmp_get_json, get_fmp_api_key
from utils import console_loading


type FMPHourlyColumn = Literal["date", "open", "high", "low", "close", "volume"]

FMP_HOURLY_COLUMNS: tuple[FMPHourlyColumn, ...] = (
    "date",
    "open",
    "high",
    "low",
    "close",
    "volume",
)
FMP_HOURLY_CACHE_DIR = Path(__file__).resolve().parent.parent / "hourly_data"
FMP_HOURLY_CACHE_TAIL_REFRESH = timedelta(days=1)


class FMPHourlyRow(TypedDict):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class FMPHourlyDataFrame(pd.DataFrame):
    """DataFrame with the expected Financial Modeling Prep hourly chart columns."""

    expected_columns: ClassVar[tuple[FMPHourlyColumn, ...]] = FMP_HOURLY_COLUMNS

    @property
    def _constructor(self) -> type[FMPHourlyDataFrame]:
        return FMPHourlyDataFrame

    @overload
    def __getitem__(self, key: Literal["date"]) -> "pd.Series": ...

    @overload
    def __getitem__(self, key: Literal["open"]) -> "pd.Series": ...

    @overload
    def __getitem__(self, key: Literal["high"]) -> "pd.Series": ...

    @overload
    def __getitem__(self, key: Literal["low"]) -> "pd.Series": ...

    @overload
    def __getitem__(self, key: Literal["close"]) -> "pd.Series": ...

    @overload
    def __getitem__(self, key: Literal["volume"]) -> "pd.Series": ...

    @overload
    def __getitem__(self, key: Any) -> Any: ...

    def __getitem__(self, key: Any) -> Any:
        return super().__getitem__(key)


def _is_fmp_hourly_row(row: dict[str, Any]) -> TypeGuard[FMPHourlyRow]:
    return all(column in row for column in FMP_HOURLY_COLUMNS)


def _parse_fmp_datetime(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unsupported FMP datetime format: {value}")


def _validate_date_range(start_date: datetime, end_date: datetime) -> None:
    if start_date > end_date:
        raise ValueError("start_date must be less than or equal to end_date.")


def _empty_hourly_dataframe() -> FMPHourlyDataFrame:
    return FMPHourlyDataFrame(pd.DataFrame(columns=FMP_HOURLY_COLUMNS))


def _parse_hourly_dates(dataframe: pd.DataFrame) -> pd.Series:
    return pd.to_datetime(dataframe["date"], errors="coerce")


# Cache helpers keep backwards compatibility with older filenames while steering writes
# back to one canonical CSV per symbol.
def _build_hourly_cache_path(symbol: str) -> Path:
    return FMP_HOURLY_CACHE_DIR / f"{symbol.upper()}_hourly.csv"


def _is_hourly_cache_path(cache_path: Path, symbol: str) -> bool:
    if cache_path.suffix.lower() != ".csv":
        return False

    canonical_stem = f"{symbol.upper()}_hourly"
    return cache_path.stem == canonical_stem or cache_path.stem.startswith(
        f"{canonical_stem}_"
    )


def _get_hourly_cache_paths(symbol: str) -> list[Path]:
    if not FMP_HOURLY_CACHE_DIR.exists():
        return []

    canonical_path = _build_hourly_cache_path(symbol)
    cache_paths = [
        cache_path
        for cache_path in FMP_HOURLY_CACHE_DIR.iterdir()
        if cache_path.is_file() and _is_hourly_cache_path(cache_path, symbol)
    ]
    return sorted(
        cache_paths,
        key=lambda cache_path: (cache_path != canonical_path, cache_path.name),
    )


def _cleanup_redundant_hourly_caches(symbol: str, keep_cache_path: Path) -> None:
    for cache_path in _get_hourly_cache_paths(symbol):
        if cache_path != keep_cache_path and cache_path.exists():
            cache_path.unlink()


def _save_hourly_cache(dataframe: pd.DataFrame, cache_path: Path) -> None:
    FMP_HOURLY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _normalize_hourly_dataframe(dataframe).to_csv(cache_path, index=False)


# Normalize dataframes at the edges so the rest of the module can assume a stable
# schema, sorted timestamps, and no duplicate hourly rows.
def _normalize_hourly_dataframe(dataframe: pd.DataFrame) -> FMPHourlyDataFrame:
    normalized = dataframe.reindex(columns=FMP_HOURLY_COLUMNS).dropna(subset=["date"]).copy()
    if normalized.empty:
        return _empty_hourly_dataframe()

    normalized["_parsed_date"] = _parse_hourly_dates(normalized)
    normalized = normalized.loc[normalized["_parsed_date"].notna()]
    if normalized.empty:
        return _empty_hourly_dataframe()

    normalized = normalized.sort_values("_parsed_date").drop_duplicates(
        subset="date", keep="last"
    )
    normalized = normalized.drop(columns="_parsed_date")
    normalized["date"] = normalized["date"].astype(str)
    return FMPHourlyDataFrame(normalized.reset_index(drop=True))


def _filter_hourly_dataframe(
    dataframe: pd.DataFrame,
    start_date: datetime,
    end_date: datetime,
) -> FMPHourlyDataFrame:
    normalized = _normalize_hourly_dataframe(dataframe)
    if normalized.empty:
        return normalized

    parsed_dates = _parse_hourly_dates(normalized)
    mask = parsed_dates.between(start_date, end_date, inclusive="both")
    return FMPHourlyDataFrame(normalized.loc[mask].reset_index(drop=True))


def _merge_hourly_dataframes(dataframes: Sequence[pd.DataFrame]) -> FMPHourlyDataFrame:
    non_empty_dataframes = [dataframe for dataframe in dataframes if not dataframe.empty]
    if not non_empty_dataframes:
        return _empty_hourly_dataframe()

    return _normalize_hourly_dataframe(pd.concat(non_empty_dataframes, ignore_index=True))


def _load_hourly_cache(cache_path: Path) -> FMPHourlyDataFrame:
    try:
        return _normalize_hourly_dataframe(pd.read_csv(cache_path))
    except pd.errors.EmptyDataError:
        return _empty_hourly_dataframe()


def _get_hourly_dataframe_bounds(
    dataframe: pd.DataFrame,
) -> tuple[datetime, datetime] | None:
    if dataframe.empty:
        return None

    parsed_dates = _parse_hourly_dates(dataframe).dropna()
    if parsed_dates.empty:
        return None

    return parsed_dates.min().to_pydatetime(), parsed_dates.max().to_pydatetime()


def _should_refresh_recent_tail(end_date: datetime) -> bool:
    return end_date.date() >= datetime.now().date() - FMP_HOURLY_CACHE_TAIL_REFRESH


def _get_cache_refresh_windows(
    cached_bounds: tuple[datetime, datetime] | None,
    start_date: datetime,
    end_date: datetime,
) -> list[tuple[datetime, datetime]]:
    if cached_bounds is None:
        return [(start_date, end_date)]

    cached_start, cached_end = cached_bounds
    refresh_windows: list[tuple[datetime, datetime]] = []

    if cached_start.date() > start_date.date():
        refresh_windows.append((start_date, min(end_date, cached_start)))

    if cached_end.date() < end_date.date() or _should_refresh_recent_tail(end_date):
        refresh_windows.append(
            (max(start_date, cached_end - FMP_HOURLY_CACHE_TAIL_REFRESH), end_date)
        )

    return refresh_windows


# FMP can return intraday history in chunks, so we walk the end of the request window
# backward until we reach the requested start or stop making progress.
def _fetch_fmp_hourly_window(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
) -> list[FMPHourlyRow]:
    payload = fmp_get_json(
        "/historical-chart/1hour",
        {
            "symbol": symbol,
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d"),
        },
    )

    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected response from FMP: {payload}")

    dated_rows: list[tuple[datetime, FMPHourlyRow]] = []
    for row in payload:
        if not isinstance(row, dict) or not _is_fmp_hourly_row(row):
            continue

        row_date = _parse_fmp_datetime(str(row["date"]))
        if start_date <= row_date <= end_date:
            dated_rows.append((row_date, cast(FMPHourlyRow, row)))

    dated_rows.sort(key=lambda item: item[0])
    return [row for _, row in dated_rows]


def _calculate_collection_percent(
    start_date: datetime,
    end_date: datetime,
    earliest_row_date: datetime,
) -> float:
    total_seconds = (end_date - start_date).total_seconds()
    if total_seconds <= 0:
        return 100.0

    clamped_earliest = min(max(earliest_row_date, start_date), end_date)
    collected_seconds = (end_date - clamped_earliest).total_seconds()
    return max(0.0, min(100.0, (collected_seconds / total_seconds) * 100.0))


def _finish_loading_progress(
    verbose: bool,
    reached_target_start_date: bool,
    last_reported_percent: float,
    loading_message: str,
) -> None:
    if not verbose:
        return

    if reached_target_start_date:
        console_loading(100.0, loading_message)
    elif last_reported_percent < 100.0:
        print()


def _fetch_hourly_dataframe(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    verbose: bool,
) -> FMPHourlyDataFrame:
    return fmp_hourly_to_dataframe(
        fmp_get_hourly(symbol, start_date, end_date, verbose=verbose)
    )


def fmp_get_hourly(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    verbose: bool = True,
) -> list[FMPHourlyRow]:
    """Fetch hourly FMP chart data for `symbol` between `start_date` and `end_date`, inclusive."""
    _validate_date_range(start_date, end_date)
    get_fmp_api_key()

    all_rows_by_date: dict[str, FMPHourlyRow] = {}
    current_end_date = end_date
    previous_earliest_row_date: datetime | None = None
    last_reported_percent = 0.0
    reached_target_start_date = False
    loading_message = f"Retrieving {symbol.upper()} hourly data"

    if verbose:
        console_loading(last_reported_percent, loading_message)

    while True:
        window_rows = _fetch_fmp_hourly_window(symbol, start_date, current_end_date)
        if not window_rows:
            break

        earliest_row_date = _parse_fmp_datetime(str(window_rows[0]["date"]))
        if earliest_row_date == previous_earliest_row_date:
            break

        last_reported_percent = _calculate_collection_percent(
            start_date,
            end_date,
            earliest_row_date,
        )
        if verbose:
            console_loading(last_reported_percent, loading_message)

        all_rows_by_date.update({row["date"]: row for row in window_rows})
        reached_target_start_date = earliest_row_date <= start_date
        if reached_target_start_date:
            break

        # Reusing the earliest row as the next boundary intentionally overlaps one
        # timestamp; deduping keeps the overlap harmless while the guard above stops
        # us if FMP stops returning older data.
        previous_earliest_row_date = earliest_row_date
        current_end_date = earliest_row_date

    _finish_loading_progress(
        verbose,
        reached_target_start_date,
        last_reported_percent,
        loading_message,
    )

    return sorted(
        all_rows_by_date.values(),
        key=lambda row: _parse_fmp_datetime(str(row["date"])),
    )


def fmp_hourly_to_dataframe(rows: Sequence[FMPHourlyRow]) -> FMPHourlyDataFrame:
    """Convert FMP hourly rows into a normalized dataframe with the standard columns."""
    return _normalize_hourly_dataframe(pd.DataFrame(rows))


# Cache-backed reads stay simple: load what exists, fill any missing historical gap,
# then refresh the recent tail because the latest intraday candles can still change.
def fmp_get_hourly_dataframe(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    verbose: bool = True,
    use_cache: bool = True,
) -> FMPHourlyDataFrame:
    """Fetch hourly FMP data and return it as a typed dataframe."""
    _validate_date_range(start_date, end_date)
    if not use_cache:
        return _fetch_hourly_dataframe(symbol, start_date, end_date, verbose=verbose)

    cache_path = _build_hourly_cache_path(symbol)
    cache_paths = _get_hourly_cache_paths(symbol)
    cached_dataframe = _merge_hourly_dataframes(
        [_load_hourly_cache(existing_cache_path) for existing_cache_path in cache_paths]
    )
    refresh_windows = _get_cache_refresh_windows(
        _get_hourly_dataframe_bounds(cached_dataframe),
        start_date,
        end_date,
    )
    refresh_frames = [
        _fetch_hourly_dataframe(symbol, refresh_start, refresh_end, verbose=verbose)
        for refresh_start, refresh_end in refresh_windows
    ]
    combined_dataframe = _merge_hourly_dataframes([cached_dataframe, *refresh_frames])
    should_write_cache = (
        bool(refresh_windows) or cache_path not in cache_paths or len(cache_paths) > 1
    )

    if should_write_cache:
        _save_hourly_cache(combined_dataframe, cache_path)
        _cleanup_redundant_hourly_caches(symbol, cache_path)

    return _filter_hourly_dataframe(combined_dataframe, start_date, end_date)
