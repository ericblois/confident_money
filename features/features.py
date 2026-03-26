from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import Literal

from ._shared import (
    FeatureArgInfo,
    FeatureInfo,
    build_feature_category_map,
    build_feature_info_map,
    build_search_sort_key,
    normalized_search_text,
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
type ScriptValueTypeName = Literal["number", "boolean", "string", "any"]


@dataclass(frozen=True, slots=True)
class _FeatureSearchEntry:
    feature_info: FeatureInfo
    script_name: str
    full_name: str
    full_name_words: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScriptParameterInfo:
    name: str
    full_name: str
    accepted_types: tuple[ScriptValueTypeName, ...] = ("number",)


@dataclass(frozen=True, slots=True)
class ScriptFunctionInfo:
    name: str
    full_name: str
    signatures: tuple[tuple[str, ...], ...]
    return_type: ScriptValueTypeName = "number"


@dataclass(frozen=True, slots=True)
class ScriptFunctionAliasInfo:
    name: str
    target_name: str
    signatures: tuple[tuple[str, ...], ...] | None = None


def script_parameter_info(
    name: str,
    full_name: str,
    *accepted_types: ScriptValueTypeName,
) -> ScriptParameterInfo:
    return ScriptParameterInfo(
        name=name,
        full_name=full_name,
        accepted_types=accepted_types or ("number",),
    )


def script_function_info(
    name: str,
    full_name: str,
    signatures: tuple[tuple[str, ...], ...],
    *,
    return_type: ScriptValueTypeName = "number",
) -> ScriptFunctionInfo:
    return ScriptFunctionInfo(
        name=name,
        full_name=full_name,
        signatures=tuple(tuple(signature) for signature in signatures),
        return_type=return_type,
    )


def script_function_alias_info(
    name: str,
    target_name: str,
    signatures: tuple[tuple[str, ...], ...] | None = None,
) -> ScriptFunctionAliasInfo:
    return ScriptFunctionAliasInfo(
        name=name,
        target_name=target_name,
        signatures=signatures,
    )


def _build_script_parameter_info_map(
    *parameter_infos: ScriptParameterInfo,
) -> dict[str, ScriptParameterInfo]:
    return {parameter_info.name: parameter_info for parameter_info in parameter_infos}


def _build_script_function_info_map(
    *function_infos: ScriptFunctionInfo,
) -> dict[str, ScriptFunctionInfo]:
    return {function_info.name: function_info for function_info in function_infos}


def _merge_script_parameter_info(
    existing_parameter_info: ScriptParameterInfo | None,
    new_parameter_info: ScriptParameterInfo,
) -> ScriptParameterInfo:
    if existing_parameter_info is None:
        return new_parameter_info

    merged_types = tuple(
        dict.fromkeys(
            (*existing_parameter_info.accepted_types, *new_parameter_info.accepted_types)
        )
    )
    return ScriptParameterInfo(
        name=existing_parameter_info.name,
        full_name=existing_parameter_info.full_name,
        accepted_types=merged_types,
    )


def _script_value_types_for_feature_arg(arg_type: str) -> tuple[ScriptValueTypeName, ...]:
    if arg_type == "boolean_flag":
        return ("boolean",)
    if arg_type == "source" or arg_type.endswith("_source"):
        return ("number", "string")
    return ("number",)


def _feature_arg_parameter_info(feature_arg_info: FeatureArgInfo) -> ScriptParameterInfo:
    return script_parameter_info(
        feature_arg_info.script_name,
        feature_arg_info.full_name,
        *_script_value_types_for_feature_arg(feature_arg_info.arg_type),
    )


def _build_feature_script_parameter_info_map(
    feature_infos_by_script: dict[str, FeatureInfo],
    base_parameter_infos_by_name: dict[str, ScriptParameterInfo],
) -> dict[str, ScriptParameterInfo]:
    parameter_infos_by_name = dict(base_parameter_infos_by_name)

    for feature_info in feature_infos_by_script.values():
        for feature_arg_info in feature_info.all_args:
            parameter_info = _feature_arg_parameter_info(feature_arg_info)
            parameter_infos_by_name[parameter_info.name] = _merge_script_parameter_info(
                parameter_infos_by_name.get(parameter_info.name),
                parameter_info,
            )

    return parameter_infos_by_name


def _feature_calc_parameters(
    calc_function: object,
) -> tuple[inspect.Parameter, ...]:
    return tuple(
        parameter
        for parameter in inspect.signature(calc_function).parameters.values()
        if parameter.name != "dataframe"
        and parameter.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    )


def _build_feature_calc_parameter_names_map(
    feature_calculators_by_script: dict[str, object],
) -> dict[str, tuple[str, ...]]:
    return {
        script_name: tuple(
            parameter.name for parameter in _feature_calc_parameters(calc_function)
        )
        for script_name, calc_function in feature_calculators_by_script.items()
    }


def _build_feature_script_function_info_map(
    feature_infos_by_script: dict[str, FeatureInfo],
    feature_calc_parameter_names_by_script: dict[str, tuple[str, ...]],
    feature_calculators_by_script: dict[str, object],
) -> dict[str, ScriptFunctionInfo]:
    feature_function_infos_by_name: dict[str, ScriptFunctionInfo] = {}

    for script_name, feature_info in feature_infos_by_script.items():
        calc_function = feature_calculators_by_script.get(script_name)
        if calc_function is None:
            raise ValueError(f"Missing calc function mapping for feature '{script_name}'.")

        calc_parameter_names = feature_calc_parameter_names_by_script.get(script_name)
        if calc_parameter_names is None:
            raise ValueError(f"Missing calc parameter mapping for feature '{script_name}'.")

        calc_parameters = _feature_calc_parameters(calc_function)
        if len(calc_parameter_names) != len(calc_parameters):
            raise ValueError(
                f"Feature '{script_name}' calc parameter metadata is out of sync."
            )
        script_parameter_names = tuple(
            feature_arg_info.script_name
            for feature_arg_info in feature_info.all_args[: len(calc_parameters)]
        )
        if len(script_parameter_names) != len(calc_parameters):
            raise ValueError(
                f"Feature '{script_name}' metadata does not align with its calc signature."
            )

        required_parameter_count = sum(
            parameter.default is inspect.Signature.empty
            for parameter in calc_parameters
        )
        signatures = tuple(
            script_parameter_names[:parameter_count]
            for parameter_count in range(
                required_parameter_count,
                len(calc_parameters) + 1,
            )
        )
        feature_function_infos_by_name[script_name] = script_function_info(
            script_name,
            feature_info.full_name,
            signatures,
        )

    return feature_function_infos_by_name


def _build_alias_script_function_info_map(
    alias_infos: tuple[ScriptFunctionAliasInfo, ...],
    feature_function_infos_by_name: dict[str, ScriptFunctionInfo],
) -> dict[str, ScriptFunctionInfo]:
    alias_function_infos_by_name: dict[str, ScriptFunctionInfo] = {}

    for alias_info in alias_infos:
        target_function_info = feature_function_infos_by_name[alias_info.target_name]
        alias_function_infos_by_name[alias_info.name] = script_function_info(
            alias_info.name,
            target_function_info.full_name,
            (
                target_function_info.signatures
                if alias_info.signatures is None
                else alias_info.signatures
            ),
            return_type=target_function_info.return_type,
        )

    return alias_function_infos_by_name


def _humanize_identifier(name: str) -> str:
    return " ".join(
        part.upper() if part.isupper() else part.capitalize()
        for part in name.split("_")
    )


_BASE_SCRIPT_PARAMETER_INFOS_BY_NAME = _build_script_parameter_info_map(
    script_parameter_info("open", "Opening Price"),
    script_parameter_info("high", "High Price"),
    script_parameter_info("low", "Low Price"),
    script_parameter_info("close", "Closing Price"),
    script_parameter_info("source", "Source Series"),
    script_parameter_info("left", "Left Series"),
    script_parameter_info("right", "Right Series"),
    script_parameter_info("benchmark", "Benchmark Series"),
    script_parameter_info("return", "Return Series"),
    script_parameter_info("rel_return", "Relative Return Series"),
    script_parameter_info("volatility", "Volatility Series"),
    script_parameter_info("price", "Price Series"),
    script_parameter_info("volume", "Volume Series"),
    script_parameter_info("window", "Lookback Window"),
    script_parameter_info("min_periods", "Minimum Periods"),
)
FEATURE_CALCULATORS_BY_SCRIPT: dict[str, object] = {
    "px": calc_price,
    "ret": calc_return,
    "log_ret": calc_log_return,
    "roll_hi": calc_rolling_high,
    "roll_lo": calc_rolling_low,
    "typ_px": calc_typical_price,
    "med_px": calc_median_price,
    "abs": calc_abs,
    "log": calc_log_value,
    "dist": calc_distance_to_col,
    "z": calc_z_score,
    "pct_rank": calc_percentile_rank,
    "ma": calc_mv_avg,
    "ema": calc_ema,
    "trend_slp": calc_trend_slope,
    "trend_r2": calc_trend_r2,
    "adx": calc_adx,
    "brk_dist": calc_breakout_distance,
    "rng_pos": calc_range_position,
    "mom": calc_momentum,
    "rsi": calc_rsi,
    "stoch_k": calc_stoch_k,
    "stoch_d": calc_stoch_d,
    "macd": calc_macd,
    "macd_sig": calc_macd_signal,
    "macd_hist": calc_macd_hist,
    "roc": calc_roc,
    "will_r": calc_williams_r,
    "rel_ret": calc_rel_return,
    "rel_mom": calc_rel_momentum,
    "rel_trend_slp": calc_rel_trend_slope,
    "rel_trend_r2": calc_rel_trend_r2,
    "tr": calc_true_range,
    "atr": calc_atr,
    "vlt": calc_realized_vol,
    "pk_vlt": calc_parkinson_volatility,
    "gk_vlt": calc_garman_klass_volatility,
    "rs_vlt": calc_rogers_satchell_volatility,
    "vol": calc_volume,
    "vwap": calc_vwap,
    "obv": calc_obv,
    "adl": calc_adl,
    "cmf": calc_cmf,
    "mfi": calc_mfi,
    "rvol_pct": calc_relative_volume_percentile,
    "dow": calc_day_of_week,
    "dom": calc_day_of_month,
    "doy": calc_day_of_year,
    "woy": calc_week_of_year,
    "moy": calc_month_of_year,
    "qtr": calc_quarter,
    "hour": calc_hour,
    "is_ms": calc_is_month_start,
    "is_me": calc_is_month_end,
    "is_hol_adj": calc_is_holiday_adjacent,
    "body_pct": calc_body_pct,
    "up_wick": calc_upper_wick_ratio,
    "low_wick": calc_lower_wick_ratio,
    "clv": calc_close_location,
}
FEATURE_CALCULATOR_PARAMETER_NAMES_BY_SCRIPT = _build_feature_calc_parameter_names_map(
    FEATURE_CALCULATORS_BY_SCRIPT
)
SCRIPT_PARAMETER_INFOS_BY_NAME = _build_feature_script_parameter_info_map(
    FEATURE_INFOS_BY_SCRIPT,
    _BASE_SCRIPT_PARAMETER_INFOS_BY_NAME,
)
SCRIPT_PARAMETER_INFOS: tuple[ScriptParameterInfo, ...] = tuple(
    SCRIPT_PARAMETER_INFOS_BY_NAME.values()
)
FEATURE_SCRIPT_FUNCTION_INFOS_BY_NAME = _build_feature_script_function_info_map(
    FEATURE_INFOS_BY_SCRIPT,
    FEATURE_CALCULATOR_PARAMETER_NAMES_BY_SCRIPT,
    FEATURE_CALCULATORS_BY_SCRIPT,
)
SCRIPT_FUNCTION_ALIAS_INFOS = (
    script_function_alias_info(
        "mv_avg",
        "ma",
        (("source", "window"), ("source", "window", "min_periods")),
    ),
    script_function_alias_info(
        "moving_avg",
        "ma",
        (("source", "window"), ("source", "window", "min_periods")),
    ),
    script_function_alias_info(
        "vwap",
        "vwap",
        (
            ("window",),
            ("window", "price"),
            ("window", "price", "volume"),
            ("window", "price", "volume", "min_periods"),
        ),
    ),
    script_function_alias_info("distance", "dist", (("left", "right"),)),
    script_function_alias_info(
        "log_return",
        "log_ret",
        (("window",), ("source", "window")),
    ),
    script_function_alias_info(
        "vlt",
        "vlt",
        (
            ("window",),
            ("source", "window"),
            ("source", "window", "min_periods"),
        ),
    ),
    script_function_alias_info(
        "realized_vol",
        "vlt",
        (
            ("window",),
            ("source", "window"),
            ("source", "window", "min_periods"),
        ),
    ),
    script_function_alias_info("momentum", "mom", (("return", "volatility"),)),
    script_function_alias_info("trend_slope", "trend_slp", (("source", "window"),)),
    script_function_alias_info("trend_r2", "trend_r2", (("source", "window"),)),
    script_function_alias_info(
        "breakout_distance",
        "brk_dist",
        (("source", "window"), ("source", "window", "min_periods")),
    ),
    script_function_alias_info(
        "range_position",
        "rng_pos",
        (("source", "window"), ("source", "window", "min_periods")),
    ),
    script_function_alias_info(
        "rel_return",
        "rel_ret",
        (("return", "benchmark", "window"),),
    ),
    script_function_alias_info(
        "rel_momentum",
        "rel_mom",
        (
            ("rel_return", "return", "benchmark", "window"),
            ("rel_return", "return", "benchmark", "window", "min_periods"),
        ),
    ),
    script_function_alias_info(
        "rel_trend_slope",
        "rel_trend_slp",
        (("source", "benchmark", "window"),),
    ),
    script_function_alias_info(
        "rel_trend_r2",
        "rel_trend_r2",
        (("source", "benchmark", "window"),),
    ),
)
SCRIPT_ALIAS_FUNCTION_INFOS_BY_NAME = _build_alias_script_function_info_map(
    SCRIPT_FUNCTION_ALIAS_INFOS,
    FEATURE_SCRIPT_FUNCTION_INFOS_BY_NAME,
)
SCRIPT_FUNCTION_INFOS_BY_NAME = {
    **FEATURE_SCRIPT_FUNCTION_INFOS_BY_NAME,
    **SCRIPT_ALIAS_FUNCTION_INFOS_BY_NAME,
}
SCRIPT_FUNCTION_INFOS: tuple[ScriptFunctionInfo, ...] = tuple(
    SCRIPT_FUNCTION_INFOS_BY_NAME.values()
)


def get_script_function_full_name(name: str) -> str:
    function_info = SCRIPT_FUNCTION_INFOS_BY_NAME.get(name)
    return function_info.full_name if function_info is not None else _humanize_identifier(name)


def get_script_parameter_full_name(name: str) -> str:
    parameter_info = SCRIPT_PARAMETER_INFOS_BY_NAME.get(name)
    return parameter_info.full_name if parameter_info is not None else _humanize_identifier(name)


def search_features(query: str, n: int = 3) -> list[FeatureInfo]:
    """Return the strongest feature metadata matches for a search query."""
    normalized_query = normalized_search_text(query)
    if not normalized_query:
        return []

    ranked_entries: list[tuple[tuple[int, int, str], FeatureInfo]] = []
    for search_entry in _FEATURE_SEARCH_INDEX:
        sort_key = _feature_search_sort_key(search_entry, normalized_query)
        if sort_key is not None:
            ranked_entries.append((sort_key, search_entry.feature_info))

    ranked_entries.sort(key=lambda ranked_entry: ranked_entry[0])
    return [feature_info for _, feature_info in ranked_entries[: max(0, int(n))]]


def _feature_search_sort_key(
    search_entry: _FeatureSearchEntry,
    normalized_query: str,
) -> tuple[int, int, int, str] | None:
    return build_search_sort_key(
        normalized_query,
        script_name=search_entry.script_name,
        full_name=search_entry.full_name,
        priority=len(search_entry.feature_info.full_name),
    )


_FEATURE_SEARCH_INDEX: tuple[_FeatureSearchEntry, ...] = tuple(
    _FeatureSearchEntry(
        feature_info=feature_info,
        script_name=normalized_search_text(feature_info.script_name),
        full_name=normalized_search_text(feature_info.full_name),
        full_name_words=tuple(normalized_search_text(feature_info.full_name).split()),
    )
    for feature_info in FEATURE_INFOS
)


__all__ = [
    "FEATURE_INFOS",
    "FEATURE_INFOS_BY_CATEGORY",
    "FEATURE_INFOS_BY_SCRIPT",
    "FeatureArgInfo",
    "FeatureInfo",
    "FEATURE_CALCULATORS_BY_SCRIPT",
    "FEATURE_CALCULATOR_PARAMETER_NAMES_BY_SCRIPT",
    "FEATURE_SCRIPT_FUNCTION_INFOS_BY_NAME",
    "SCRIPT_ALIAS_FUNCTION_INFOS_BY_NAME",
    "SCRIPT_FUNCTION_ALIAS_INFOS",
    "ScriptFunctionAliasInfo",
    "ScriptFunctionInfo",
    "ScriptParameterInfo",
    "SCRIPT_FUNCTION_INFOS",
    "SCRIPT_FUNCTION_INFOS_BY_NAME",
    "SCRIPT_PARAMETER_INFOS",
    "SCRIPT_PARAMETER_INFOS_BY_NAME",
    "build_search_sort_key",
    "get_script_function_full_name",
    "get_script_parameter_full_name",
    "normalized_search_text",
    "search_features",
    "script_function_alias_info",
    "script_function_info",
    "script_parameter_info",
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
