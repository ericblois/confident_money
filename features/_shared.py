from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class FeatureArgInfo:
    script_name: str
    full_name: str
    arg_type: str
    default_value: Any | None = None


def _default_offset_arg() -> FeatureArgInfo:
    return FeatureArgInfo(
        script_name="offset",
        full_name="Offset",
        arg_type="offset",
        default_value=0,
    )


@dataclass(frozen=True, slots=True)
class FeatureInfo:
    script_name: str
    full_name: str
    category: str
    args: list[FeatureArgInfo]
    offset_arg: FeatureArgInfo = field(default_factory=_default_offset_arg)

    @property
    def all_args(self) -> tuple[FeatureArgInfo, ...]:
        return (*self.args, self.offset_arg)


def feature_arg(
    script_name: str,
    full_name: str,
    arg_type: str,
    default_value: Any | None = None,
) -> FeatureArgInfo:
    return FeatureArgInfo(
        script_name=script_name,
        full_name=full_name,
        arg_type=arg_type,
        default_value=default_value,
    )


def feature_info(
    script_name: str,
    full_name: str,
    category: str,
    args: Iterable[FeatureArgInfo] | None = None,
    offset_arg: FeatureArgInfo | None = None,
) -> FeatureInfo:
    return FeatureInfo(
        script_name=script_name,
        full_name=full_name,
        category=category,
        args=list(args or ()),
        offset_arg=_default_offset_arg() if offset_arg is None else offset_arg,
    )


def build_feature_info_map(
    *feature_info_groups: Iterable[FeatureInfo],
) -> dict[str, FeatureInfo]:
    feature_infos_by_script: dict[str, FeatureInfo] = {}

    for feature_info_group in feature_info_groups:
        for feature_info in feature_info_group:
            if feature_info.script_name in feature_infos_by_script:
                raise ValueError(
                    f"Duplicate feature script name '{feature_info.script_name}'."
                )

            feature_infos_by_script[feature_info.script_name] = feature_info

    return feature_infos_by_script


def build_feature_category_map(
    feature_infos_by_script: Mapping[str, FeatureInfo],
) -> dict[str, tuple[FeatureInfo, ...]]:
    grouped_feature_infos: dict[str, list[FeatureInfo]] = {}
    for feature_info in feature_infos_by_script.values():
        grouped_feature_infos.setdefault(feature_info.category, [])
        grouped_feature_infos[feature_info.category].append(feature_info)

    return {
        category: tuple(feature_infos)
        for category, feature_infos in grouped_feature_infos.items()
    }


def numeric_column(dataframe: pd.DataFrame, col: str) -> pd.Series:
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")

    return pd.to_numeric(dataframe[col], errors="coerce")


def datetime_column(dataframe: pd.DataFrame, col: str) -> pd.Series:
    if col not in dataframe.columns:
        raise ValueError(f"Column '{col}' not found in the dataframe.")

    return pd.to_datetime(dataframe[col], errors="coerce")


def positive_int(value: int | float, *, name: str) -> int:
    return _validated_int(value, name=name, minimum=1)


def non_negative_int(value: int | float, *, name: str) -> int:
    return _validated_int(value, name=name, minimum=0)


def resolved_min_periods(min_periods: int | None, *, default_value: int) -> int:
    return positive_int(
        default_value if min_periods is None else min_periods,
        name="min_periods",
    )


def offset_suffix(offset: int) -> str:
    resolved_offset = non_negative_int(offset, name="offset")
    return "" if resolved_offset == 0 else f"_offset{resolved_offset}"


def safe_log(series: pd.Series) -> pd.Series:
    numeric_series = pd.to_numeric(series, errors="coerce")
    return np.log(numeric_series.where(numeric_series > 0))


def wilder_mean(
    series: pd.Series,
    window: int,
    *,
    min_periods: int | None = None,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    resolved_window_min_periods = resolved_min_periods(
        min_periods,
        default_value=resolved_window,
    )
    return pd.to_numeric(series, errors="coerce").ewm(
        alpha=1.0 / resolved_window,
        adjust=False,
        min_periods=resolved_window_min_periods,
    ).mean()


def rolling_trend_stats(series: pd.Series, window: int) -> tuple[pd.Series, pd.Series]:
    """Return rolling slope and R-squared for a fixed-size linear regression window."""
    resolved_window = positive_int(window, name="window")
    if resolved_window < 2:
        empty_series = pd.Series(np.nan, index=series.index, dtype=float)
        return empty_series, empty_series

    y_values = pd.to_numeric(series, errors="coerce").astype(float)
    global_index = pd.Series(np.arange(len(y_values), dtype=float), index=series.index)

    sum_y = y_values.rolling(resolved_window, min_periods=resolved_window).sum()
    sum_y_squared = y_values.pow(2).rolling(resolved_window, min_periods=resolved_window).sum()
    sum_index_y = (y_values * global_index).rolling(
        resolved_window,
        min_periods=resolved_window,
    ).sum()

    sum_x = resolved_window * (resolved_window - 1) / 2.0
    sum_x_squared = (resolved_window - 1) * resolved_window * (2 * resolved_window - 1) / 6.0
    x_variance_term = (resolved_window * sum_x_squared) - (sum_x**2)

    window_start = global_index - (resolved_window - 1)
    sum_xy = sum_index_y - (window_start * sum_y)
    covariance_term = (resolved_window * sum_xy) - (sum_x * sum_y)
    y_variance_term = (resolved_window * sum_y_squared) - (sum_y**2)

    slope = covariance_term / x_variance_term
    denominator = np.sqrt(x_variance_term * y_variance_term.clip(lower=0.0))
    correlation = covariance_term / denominator.replace(0.0, np.nan)
    r_squared = correlation.clip(-1.0, 1.0).pow(2)

    return slope, r_squared


def _validated_int(value: int | float, *, name: str, minimum: int) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be an integer value.")

    numeric_value = float(value)
    if (
        not np.isfinite(numeric_value)
        or not numeric_value.is_integer()
        or numeric_value < minimum
    ):
        comparator = "greater than 0" if minimum == 1 else "greater than or equal to 0"
        raise ValueError(f"{name} must be an integer {comparator}.")

    return int(numeric_value)


__all__ = [
    "FeatureArgInfo",
    "FeatureInfo",
    "build_feature_category_map",
    "build_feature_info_map",
    "build_search_sort_key",
    "datetime_column",
    "feature_arg",
    "feature_info",
    "non_negative_int",
    "numeric_column",
    "offset_suffix",
    "positive_int",
    "resolved_min_periods",
    "normalized_search_text",
    "rolling_trend_stats",
    "safe_log",
    "wilder_mean",
]


def normalized_search_text(text: str) -> str:
    normalized_characters = [
        character.lower() if character.isalnum() else " "
        for character in text.strip()
    ]
    return " ".join("".join(normalized_characters).split())


def build_search_sort_key(
    query: str,
    *,
    script_name: str,
    full_name: str,
    priority: int = 0,
) -> tuple[int, int, int, str] | None:
    normalized_query = normalized_search_text(query)
    if not normalized_query:
        return None

    normalized_script_name = normalized_search_text(script_name)
    normalized_full_name = normalized_search_text(full_name)
    full_name_words = tuple(normalized_full_name.split())

    if normalized_script_name == normalized_query:
        return (0, priority, len(script_name), normalized_script_name)
    if normalized_script_name.startswith(normalized_query):
        return (1, priority, len(script_name), normalized_script_name)
    if any(word.startswith(normalized_query) for word in full_name_words):
        return (2, priority, len(script_name), normalized_script_name)
    if normalized_query in normalized_script_name:
        return (3, priority, len(script_name), normalized_script_name)
    if normalized_query in normalized_full_name:
        return (4, priority, len(script_name), normalized_script_name)

    query_tokens = normalized_query.split()
    if query_tokens and all(token in full_name_words for token in query_tokens):
        return (5, priority, len(script_name), normalized_script_name)
    if query_tokens and all(
        token in normalized_script_name or token in normalized_full_name
        for token in query_tokens
    ):
        return (6, priority, len(script_name), normalized_script_name)

    return None
