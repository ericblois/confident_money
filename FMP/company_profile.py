from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict, cast

from FMP.api import fmp_get_json


FMP_PROFILE_CACHE_DIR = Path(__file__).resolve().parent.parent / "company_profiles"


class FMPCompanyProfile(TypedDict, total=False):
    symbol: str
    companyName: str
    sector: str
    industry: str
    isEtf: bool
    isActivelyTrading: bool


def _build_profile_cache_path(symbol: str) -> Path:
    return FMP_PROFILE_CACHE_DIR / f"{symbol.upper()}_profile.json"


def _normalize_company_profile(payload: Any) -> FMPCompanyProfile | None:
    if not isinstance(payload, list) or not payload:
        return None

    first_row = payload[0]
    if not isinstance(first_row, dict):
        return None

    return cast(FMPCompanyProfile, first_row)


def _load_profile_cache(cache_path: Path) -> FMPCompanyProfile | None:
    try:
        with cache_path.open("r", encoding="utf-8") as cache_file:
            payload = json.load(cache_file)
    except (FileNotFoundError, json.JSONDecodeError):
        return None

    return _normalize_company_profile([payload])


def _save_profile_cache(profile: FMPCompanyProfile, cache_path: Path) -> None:
    FMP_PROFILE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as cache_file:
        json.dump(profile, cache_file, indent=2, sort_keys=True)


def fmp_get_company_profile(
    symbol: str,
    *,
    use_cache: bool = True,
) -> FMPCompanyProfile | None:
    """Return the cached or live company profile for `symbol`."""
    cache_path = _build_profile_cache_path(symbol)
    if use_cache:
        cached_profile = _load_profile_cache(cache_path)
        if cached_profile is not None:
            return cached_profile

    profile = _normalize_company_profile(fmp_get_json("/profile", {"symbol": symbol}))
    if profile is not None and use_cache:
        _save_profile_cache(profile, cache_path)

    return profile
