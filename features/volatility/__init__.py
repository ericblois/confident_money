from __future__ import annotations

from .atr import FEATURE_INFO as ATR_FEATURE_INFO, add_atr, calc_atr
from .garman_klass_volatility import (
    FEATURE_INFO as GARMAN_KLASS_VOLATILITY_FEATURE_INFO,
    add_garman_klass_volatility,
    calc_garman_klass_volatility,
)
from .parkinson_volatility import (
    FEATURE_INFO as PARKINSON_VOLATILITY_FEATURE_INFO,
    add_parkinson_volatility,
    calc_parkinson_volatility,
)
from .realized_volatility import (
    FEATURE_INFO as REALIZED_VOLATILITY_FEATURE_INFO,
    add_realized_vol,
    calc_realized_vol,
)
from .rogers_satchell_volatility import (
    FEATURE_INFO as ROGERS_SATCHELL_VOLATILITY_FEATURE_INFO,
    add_rogers_satchell_volatility,
    calc_rogers_satchell_volatility,
)
from .true_range import FEATURE_INFO as TRUE_RANGE_FEATURE_INFO, add_true_range, calc_true_range


FEATURE_INFOS = (
    TRUE_RANGE_FEATURE_INFO,
    ATR_FEATURE_INFO,
    REALIZED_VOLATILITY_FEATURE_INFO,
    PARKINSON_VOLATILITY_FEATURE_INFO,
    GARMAN_KLASS_VOLATILITY_FEATURE_INFO,
    ROGERS_SATCHELL_VOLATILITY_FEATURE_INFO,
)


__all__ = [
    "FEATURE_INFOS",
    "add_atr",
    "add_garman_klass_volatility",
    "add_parkinson_volatility",
    "add_realized_vol",
    "add_rogers_satchell_volatility",
    "add_true_range",
    "calc_atr",
    "calc_garman_klass_volatility",
    "calc_parkinson_volatility",
    "calc_realized_vol",
    "calc_rogers_satchell_volatility",
    "calc_true_range",
]
