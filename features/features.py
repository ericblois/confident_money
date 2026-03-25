from __future__ import annotations

from ._shared import (
    FeatureArgInfo,
    FeatureInfo,
    build_feature_category_map,
    build_feature_info_map,
)
from .calendar import FEATURE_INFOS as CALENDAR_FEATURE_INFOS
from .calendar import __all__ as CALENDAR_ALL
from .calendar import *
from .candles import FEATURE_INFOS as CANDLE_FEATURE_INFOS
from .candles import __all__ as CANDLE_ALL
from .candles import *
from .core import FEATURE_INFOS as CORE_FEATURE_INFOS
from .core import __all__ as CORE_ALL
from .core import *
from .momentum import FEATURE_INFOS as MOMENTUM_FEATURE_INFOS
from .momentum import __all__ as MOMENTUM_ALL
from .momentum import *
from .relative import FEATURE_INFOS as RELATIVE_FEATURE_INFOS
from .relative import __all__ as RELATIVE_ALL
from .relative import *
from .trends import FEATURE_INFOS as TREND_FEATURE_INFOS
from .trends import __all__ as TREND_ALL
from .trends import *
from .utils import FEATURE_INFOS as UTILITY_FEATURE_INFOS
from .utils import __all__ as UTILITY_ALL
from .utils import *
from .volatility import FEATURE_INFOS as VOLATILITY_FEATURE_INFOS
from .volatility import __all__ as VOLATILITY_ALL
from .volatility import *
from .volume import FEATURE_INFOS as VOLUME_FEATURE_INFOS
from .volume import __all__ as VOLUME_ALL
from .volume import *


FEATURE_INFOS_BY_SCRIPT: dict[str, FeatureInfo] = build_feature_info_map(
    CORE_FEATURE_INFOS,
    UTILITY_FEATURE_INFOS,
    TREND_FEATURE_INFOS,
    MOMENTUM_FEATURE_INFOS,
    RELATIVE_FEATURE_INFOS,
    VOLATILITY_FEATURE_INFOS,
    VOLUME_FEATURE_INFOS,
    CALENDAR_FEATURE_INFOS,
    CANDLE_FEATURE_INFOS,
)
FEATURE_INFOS: tuple[FeatureInfo, ...] = tuple(FEATURE_INFOS_BY_SCRIPT.values())
FEATURE_INFOS_BY_CATEGORY = build_feature_category_map(FEATURE_INFOS_BY_SCRIPT)


__all__ = [
    "FEATURE_INFOS",
    "FEATURE_INFOS_BY_CATEGORY",
    "FEATURE_INFOS_BY_SCRIPT",
    "FeatureArgInfo",
    "FeatureInfo",
    *CALENDAR_ALL,
    *CANDLE_ALL,
    *CORE_ALL,
    *MOMENTUM_ALL,
    *RELATIVE_ALL,
    *TREND_ALL,
    *UTILITY_ALL,
    *VOLATILITY_ALL,
    *VOLUME_ALL,
]
