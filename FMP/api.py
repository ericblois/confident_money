from __future__ import annotations

import json
import os
from typing import Any, Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FMP_API_KEY_ENV = "FMP_API_KEY"
FMP_API_ROOT_URL = "https://financialmodelingprep.com"
FMP_STABLE_API_URL = f"{FMP_API_ROOT_URL}/stable"


def get_fmp_api_key() -> str:
    """Return the configured FMP API key or raise a helpful error."""
    api_key = os.getenv(FMP_API_KEY_ENV)
    if api_key:
        return api_key

    raise RuntimeError(
        f"Missing {FMP_API_KEY_ENV}. Set it in your shell environment before calling "
        "Financial Modeling Prep helpers."
    )


def fmp_get_json(
    path: str,
    params: Mapping[str, Any] | None = None,
    *,
    timeout: int = 30,
) -> Any:
    """Fetch JSON from an FMP stable endpoint."""
    query_params = {
        key: value for key, value in (params or {}).items() if value is not None
    }
    query_params["apikey"] = get_fmp_api_key()

    normalized_path = path if path.startswith("/") else f"/{path}"
    request = Request(
        f"{FMP_STABLE_API_URL}{normalized_path}?{urlencode(query_params)}",
        headers={"Accept": "application/json"},
    )

    with urlopen(request, timeout=timeout) as response:
        return json.load(response)
