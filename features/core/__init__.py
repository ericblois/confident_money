from __future__ import annotations

from .log_return import FEATURE_INFO as LOG_RETURN_FEATURE_INFO, add_log_return, calc_log_return
from .median_price import (
    FEATURE_INFO as MEDIAN_PRICE_FEATURE_INFO,
    add_median_price,
    calc_median_price,
)
from .price import FEATURE_INFO as PRICE_FEATURE_INFO, add_price, calc_price
from .rolling_high import (
    FEATURE_INFO as ROLLING_HIGH_FEATURE_INFO,
    add_rolling_high,
    calc_rolling_high,
)
from .rolling_low import (
    FEATURE_INFO as ROLLING_LOW_FEATURE_INFO,
    add_rolling_low,
    calc_rolling_low,
)
from .simple_return import FEATURE_INFO as RETURN_FEATURE_INFO, add_return, calc_return
from .typical_price import (
    FEATURE_INFO as TYPICAL_PRICE_FEATURE_INFO,
    add_typical_price,
    calc_typical_price,
)


FEATURE_INFOS = (
    PRICE_FEATURE_INFO,
    RETURN_FEATURE_INFO,
    LOG_RETURN_FEATURE_INFO,
    ROLLING_HIGH_FEATURE_INFO,
    ROLLING_LOW_FEATURE_INFO,
    TYPICAL_PRICE_FEATURE_INFO,
    MEDIAN_PRICE_FEATURE_INFO,
)


__all__ = [
    "FEATURE_INFOS",
    "add_log_return",
    "add_median_price",
    "add_price",
    "add_return",
    "add_rolling_high",
    "add_rolling_low",
    "add_typical_price",
    "calc_log_return",
    "calc_median_price",
    "calc_price",
    "calc_return",
    "calc_rolling_high",
    "calc_rolling_low",
    "calc_typical_price",
]
