from __future__ import annotations

from .macd import FEATURE_INFO as MACD_FEATURE_INFO, add_macd, calc_macd
from .macd_hist import FEATURE_INFO as MACD_HIST_FEATURE_INFO, add_macd_hist, calc_macd_hist
from .macd_signal import (
    FEATURE_INFO as MACD_SIGNAL_FEATURE_INFO,
    add_macd_signal,
    calc_macd_signal,
)
from .momentum import FEATURE_INFO as MOMENTUM_FEATURE_INFO, add_momentum, calc_momentum
from .roc import FEATURE_INFO as ROC_FEATURE_INFO, add_roc, calc_roc
from .rsi import FEATURE_INFO as RSI_FEATURE_INFO, add_rsi, calc_rsi
from .stochastic_d import FEATURE_INFO as STOCHASTIC_D_FEATURE_INFO, add_stoch_d, calc_stoch_d
from .stochastic_k import FEATURE_INFO as STOCHASTIC_K_FEATURE_INFO, add_stoch_k, calc_stoch_k
from .williams_r import FEATURE_INFO as WILLIAMS_R_FEATURE_INFO, add_williams_r, calc_williams_r


FEATURE_INFOS = (
    MOMENTUM_FEATURE_INFO,
    RSI_FEATURE_INFO,
    STOCHASTIC_K_FEATURE_INFO,
    STOCHASTIC_D_FEATURE_INFO,
    MACD_FEATURE_INFO,
    MACD_SIGNAL_FEATURE_INFO,
    MACD_HIST_FEATURE_INFO,
    ROC_FEATURE_INFO,
    WILLIAMS_R_FEATURE_INFO,
)


__all__ = [
    "FEATURE_INFOS",
    "add_macd",
    "add_macd_hist",
    "add_macd_signal",
    "add_momentum",
    "add_roc",
    "add_rsi",
    "add_stoch_d",
    "add_stoch_k",
    "add_williams_r",
    "calc_macd",
    "calc_macd_hist",
    "calc_macd_signal",
    "calc_momentum",
    "calc_roc",
    "calc_rsi",
    "calc_stoch_d",
    "calc_stoch_k",
    "calc_williams_r",
]
