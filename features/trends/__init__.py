from __future__ import annotations

from .adx import FEATURE_INFO as ADX_FEATURE_INFO, add_adx, calc_adx
from .breakout_distance import (
    FEATURE_INFO as BREAKOUT_DISTANCE_FEATURE_INFO,
    add_breakout_distance,
    calc_breakout_distance,
)
from .ema import FEATURE_INFO as EMA_FEATURE_INFO, add_ema, calc_ema
from .moving_average import FEATURE_INFO as MOVING_AVERAGE_FEATURE_INFO, add_mv_avg, calc_mv_avg
from .range_position import (
    FEATURE_INFO as RANGE_POSITION_FEATURE_INFO,
    add_range_position,
    calc_range_position,
)
from .trend_r2 import FEATURE_INFO as TREND_R2_FEATURE_INFO, add_trend_r2, calc_trend_r2
from .trend_slope import (
    FEATURE_INFO as TREND_SLOPE_FEATURE_INFO,
    add_trend_slope,
    calc_trend_slope,
)


FEATURE_INFOS = (
    MOVING_AVERAGE_FEATURE_INFO,
    EMA_FEATURE_INFO,
    TREND_SLOPE_FEATURE_INFO,
    TREND_R2_FEATURE_INFO,
    ADX_FEATURE_INFO,
    BREAKOUT_DISTANCE_FEATURE_INFO,
    RANGE_POSITION_FEATURE_INFO,
)


__all__ = [
    "FEATURE_INFOS",
    "add_adx",
    "add_breakout_distance",
    "add_ema",
    "add_mv_avg",
    "add_range_position",
    "add_trend_r2",
    "add_trend_slope",
    "calc_adx",
    "calc_breakout_distance",
    "calc_ema",
    "calc_mv_avg",
    "calc_range_position",
    "calc_trend_r2",
    "calc_trend_slope",
]
