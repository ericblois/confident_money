from __future__ import annotations

import json
import os
from datetime import datetime
from datetime import timedelta
from pathlib import Path
from typing import Any, ClassVar, Literal, Sequence, TypedDict, TypeGuard, cast, overload
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from utils import console_loading


FMP_BASE_URL = "https://financialmodelingprep.com/stable/historical-chart/1hour"
FMP_API_KEY_ENV = "FMP_API_KEY"
FMP_HOURLY_COLUMNS = ("date", "open", "high", "low", "close", "volume")
FMP_HOURLY_CACHE_DIR = Path(__file__).resolve().parent.parent / "hourly_data"
FMP_HOURLY_CACHE_TAIL_REFRESH = timedelta(days=1)

type FMPHourlyColumn = Literal["date", "open", "high", "low", "close", "volume"]


class FMPHourlyRow(TypedDict):
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


def _is_fmp_hourly_row(row: dict[str, Any]) -> TypeGuard[FMPHourlyRow]:
    return all(column in row for column in FMP_HOURLY_COLUMNS)


class FMPHourlyDataFrame(pd.DataFrame):
    """DataFrame with the expected Financial Modeling Prep hourly chart columns."""

    expected_columns: ClassVar[tuple[FMPHourlyColumn, ...]] = cast(
        tuple[FMPHourlyColumn, ...], FMP_HOURLY_COLUMNS
    )

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


def _parse_fmp_datetime(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    raise ValueError(f"Unsupported FMP datetime format: {value}")


def _build_hourly_cache_path(symbol: str) -> Path:
    return FMP_HOURLY_CACHE_DIR / f"{symbol.upper()}_hourly.csv"


def _is_hourly_cache_path(cache_path: Path, symbol: str) -> bool:
    if cache_path.suffix.lower() != ".csv":
        return False

    normalized_symbol = symbol.upper()
    canonical_stem = f"{normalized_symbol}_hourly"
    legacy_prefix = f"{canonical_stem}_"
    return cache_path.stem == canonical_stem or cache_path.stem.startswith(legacy_prefix)


def _get_hourly_cache_paths(symbol: str) -> list[Path]:
    if not FMP_HOURLY_CACHE_DIR.exists():
        return []

    canonical_path = _build_hourly_cache_path(symbol)
    cache_paths = [
        cache_path
        for cache_path in FMP_HOURLY_CACHE_DIR.iterdir()
        if cache_path.is_file() and _is_hourly_cache_path(cache_path, symbol)
    ]
    return sorted(cache_paths, key=lambda cache_path: (cache_path != canonical_path, cache_path.name))


def _normalize_hourly_dataframe(dataframe: pd.DataFrame) -> FMPHourlyDataFrame:
    normalized = dataframe.copy()
    normalized = normalized.reindex(columns=FMP_HOURLY_COLUMNS)

    if normalized.empty:
        return FMPHourlyDataFrame(normalized)

    normalized = normalized.dropna(subset=["date"]).copy()
    normalized["_sort_date"] = pd.to_datetime(normalized["date"], errors="coerce")
    normalized = normalized.loc[normalized["_sort_date"].notna()].copy()
    normalized = normalized.sort_values("_sort_date")
    normalized = normalized.drop_duplicates(subset="date", keep="last")
    normalized = normalized.drop(columns="_sort_date")
    normalized["date"] = normalized["date"].astype(str)
    normalized = normalized.reset_index(drop=True)
    return FMPHourlyDataFrame(normalized)


def _filter_hourly_dataframe(
    dataframe: pd.DataFrame, start_date: datetime, end_date: datetime
) -> FMPHourlyDataFrame:
    if dataframe.empty:
        return _normalize_hourly_dataframe(dataframe)

    parsed_dates = pd.to_datetime(dataframe["date"], errors="coerce")
    mask = parsed_dates.notna() & (parsed_dates >= start_date) & (parsed_dates <= end_date)
    return _normalize_hourly_dataframe(dataframe.loc[mask].copy())


def _merge_hourly_dataframes(dataframes: Sequence[pd.DataFrame]) -> FMPHourlyDataFrame:
    non_empty_dataframes = [dataframe for dataframe in dataframes if not dataframe.empty]
    if not non_empty_dataframes:
        return FMPHourlyDataFrame(pd.DataFrame(columns=FMP_HOURLY_COLUMNS))

    return _normalize_hourly_dataframe(pd.concat(non_empty_dataframes, ignore_index=True))


def _load_hourly_cache(cache_path: Path) -> FMPHourlyDataFrame:
    try:
        return _normalize_hourly_dataframe(pd.read_csv(cache_path))
    except pd.errors.EmptyDataError:
        return FMPHourlyDataFrame(pd.DataFrame(columns=FMP_HOURLY_COLUMNS))


def _get_hourly_dataframe_bounds(
    dataframe: pd.DataFrame,
) -> tuple[datetime, datetime] | None:
    if dataframe.empty:
        return None

    parsed_dates = pd.to_datetime(dataframe["date"], errors="coerce")
    parsed_dates = parsed_dates.dropna()
    if parsed_dates.empty:
        return None

    return parsed_dates.min().to_pydatetime(), parsed_dates.max().to_pydatetime()


def _cleanup_redundant_hourly_caches(symbol: str, keep_cache_path: Path) -> None:
    for cache_path in _get_hourly_cache_paths(symbol):
        if cache_path != keep_cache_path and cache_path.exists():
            cache_path.unlink()


def _save_hourly_cache(dataframe: pd.DataFrame, cache_path: Path) -> None:
    FMP_HOURLY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _normalize_hourly_dataframe(dataframe).to_csv(cache_path, index=False)


def _fetch_fmp_hourly_window(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    api_key: str,
) -> list[FMPHourlyRow]:
    query = urlencode(
        {
            "symbol": symbol,
            "from": start_date.strftime("%Y-%m-%d"),
            "to": end_date.strftime("%Y-%m-%d"),
            "apikey": api_key,
        }
    )
    request = Request(f"{FMP_BASE_URL}?{query}", headers={"Accept": "application/json"})

    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    if not isinstance(payload, list):
        raise RuntimeError(f"Unexpected response from FMP: {payload}")

    filtered_rows: list[FMPHourlyRow] = []
    for row in payload:
        if not isinstance(row, dict) or not _is_fmp_hourly_row(row):
            continue

        row_date = _parse_fmp_datetime(str(row["date"]))
        if start_date <= row_date <= end_date:
            filtered_rows.append(cast(FMPHourlyRow, row))

    filtered_rows.sort(key=lambda row: _parse_fmp_datetime(str(row["date"])))
    return filtered_rows


def _calculate_collection_percent(
    start_date: datetime, end_date: datetime, earliest_row_date: datetime
) -> float:
    total_seconds = (end_date - start_date).total_seconds()
    if total_seconds <= 0:
        return 100.0

    clamped_earliest = min(max(earliest_row_date, start_date), end_date)
    collected_seconds = (end_date - clamped_earliest).total_seconds()
    return max(0.0, min(100.0, (collected_seconds / total_seconds) * 100.0))


def fmp_get_hourly(
    symbol: str, start_date: datetime, end_date: datetime, verbose: bool = True
) -> list[FMPHourlyRow]:
    """Fetch hourly FMP chart data for `symbol` between `start_date` and `end_date`, inclusive."""
    api_key = os.getenv(FMP_API_KEY_ENV)
    if not api_key:
        raise RuntimeError(
            f"Missing {FMP_API_KEY_ENV}. Set it in your shell environment before calling "
            "fmp_get_hourly()."
        )

    if start_date > end_date:
        raise ValueError("start_date must be less than or equal to end_date.")

    all_rows_by_date: dict[str, FMPHourlyRow] = {}
    current_end_date = end_date
    previous_earliest_row_date: datetime | None = None
    last_reported_percent = 0.0
    reached_target_start_date = False
    loading_message = f"Retrieving {symbol.upper()} hourly data"

    if verbose:
        console_loading(last_reported_percent, loading_message)

    while True:
        window_rows = _fetch_fmp_hourly_window(symbol, start_date, current_end_date, api_key)

        if not window_rows:
            break

        earliest_row_date = _parse_fmp_datetime(str(window_rows[0]["date"]))
        if earliest_row_date == previous_earliest_row_date:
            break

        last_reported_percent = _calculate_collection_percent(
            start_date, end_date, earliest_row_date
        )
        if verbose:
            console_loading(last_reported_percent, loading_message)

        previous_earliest_row_date = earliest_row_date

        for row in window_rows:
            all_rows_by_date[row["date"]] = row

        if earliest_row_date <= start_date:
            reached_target_start_date = True
            break

        current_end_date = earliest_row_date

    if verbose:
        if reached_target_start_date:
            console_loading(100.0, loading_message)
        elif last_reported_percent < 100.0:
            print()

    all_rows = list(all_rows_by_date.values())
    all_rows.sort(key=lambda row: _parse_fmp_datetime(str(row["date"])))
    return all_rows


def fmp_hourly_to_dataframe(rows: Sequence[FMPHourlyRow]) -> FMPHourlyDataFrame:
    """Convert FMP hourly rows into a typed dataframe with the standard FMP hourly columns."""
    dataframe = pd.DataFrame(rows)
    dataframe = dataframe.reindex(columns=FMP_HOURLY_COLUMNS)
    return FMPHourlyDataFrame(dataframe)


def fmp_get_hourly_dataframe(
    symbol: str,
    start_date: datetime,
    end_date: datetime,
    verbose: bool = True,
    use_cache: bool = True,
) -> FMPHourlyDataFrame:
    """Fetch hourly FMP data and return it as a typed dataframe."""
    if not use_cache:
        return fmp_hourly_to_dataframe(
            fmp_get_hourly(symbol, start_date, end_date, verbose=verbose)
        )

    if start_date > end_date:
        raise ValueError("start_date must be less than or equal to end_date.")

    cache_path = _build_hourly_cache_path(symbol)
    cache_paths = _get_hourly_cache_paths(symbol)
    cached_dataframe = _merge_hourly_dataframes(
        [_load_hourly_cache(existing_cache_path) for existing_cache_path in cache_paths]
    )
    cached_bounds = _get_hourly_dataframe_bounds(cached_dataframe)
    refresh_frames: list[pd.DataFrame] = []
    should_write_cache = cache_path not in cache_paths or len(cache_paths) > 1

    if cached_bounds is None:
        refresh_frames.append(
            fmp_hourly_to_dataframe(
                fmp_get_hourly(symbol, start_date, end_date, verbose=verbose)
            )
        )
        should_write_cache = True
    else:
        cached_start, cached_end = cached_bounds

        if cached_start.date() > start_date.date():
            refresh_frames.append(
                fmp_hourly_to_dataframe(
                    fmp_get_hourly(symbol, start_date, cached_start, verbose=verbose)
                )
            )
            should_write_cache = True

        if cached_end.date() < end_date.date():
            refresh_start = max(start_date, cached_end - FMP_HOURLY_CACHE_TAIL_REFRESH)
            refresh_frames.append(
                fmp_hourly_to_dataframe(
                    fmp_get_hourly(symbol, refresh_start, end_date, verbose=verbose)
                )
            )
            should_write_cache = True
        elif end_date.date() >= (datetime.now().date() - FMP_HOURLY_CACHE_TAIL_REFRESH):
            refresh_start = max(start_date, cached_end - FMP_HOURLY_CACHE_TAIL_REFRESH)
            refresh_frames.append(
                fmp_hourly_to_dataframe(
                    fmp_get_hourly(symbol, refresh_start, end_date, verbose=verbose)
                )
            )
            should_write_cache = True

    expanded_cached_dataframe = _merge_hourly_dataframes([cached_dataframe, *refresh_frames])

    if should_write_cache:
        _save_hourly_cache(expanded_cached_dataframe, cache_path)
        _cleanup_redundant_hourly_caches(symbol, cache_path)

    return _filter_hourly_dataframe(
        expanded_cached_dataframe,
        start_date,
        end_date,
    )
