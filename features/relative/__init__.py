from __future__ import annotations

from .relative_momentum import (
    FEATURE_INFO as RELATIVE_MOMENTUM_FEATURE_INFO,
    add_rel_momentum,
    calc_rel_momentum,
)
from .relative_return import (
    FEATURE_INFO as RELATIVE_RETURN_FEATURE_INFO,
    add_rel_return,
    calc_rel_return,
)
from .relative_trend_r2 import (
    FEATURE_INFO as RELATIVE_TREND_R2_FEATURE_INFO,
    add_rel_trend_r2,
    calc_rel_trend_r2,
)
from .relative_trend_slope import (
    FEATURE_INFO as RELATIVE_TREND_SLOPE_FEATURE_INFO,
    add_rel_trend_slope,
    calc_rel_trend_slope,
)


FEATURE_INFOS = (
    RELATIVE_RETURN_FEATURE_INFO,
    RELATIVE_MOMENTUM_FEATURE_INFO,
    RELATIVE_TREND_SLOPE_FEATURE_INFO,
    RELATIVE_TREND_R2_FEATURE_INFO,
)


__all__ = [
    "FEATURE_INFOS",
    "add_rel_momentum",
    "add_rel_return",
    "add_rel_trend_r2",
    "add_rel_trend_slope",
    "calc_rel_momentum",
    "calc_rel_return",
    "calc_rel_trend_r2",
    "calc_rel_trend_slope",
]
