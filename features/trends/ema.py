from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column, positive_int


FEATURE_INFO = feature_info(
    "ema",
    "Exponential Moving Average",
    "trends",
    args=[
        feature_arg("col", "Source Column", "source"),
        feature_arg("span", "Span Periods", "periods"),
        feature_arg("min_periods", "Minimum Periods", "min_periods", 1),
        feature_arg("adjust", "Adjust", "boolean_flag", False),
    ],
)


def calc_ema(
    dataframe: pd.DataFrame,
    col: str,
    span: int,
    min_periods: int = 1,
    adjust: bool = False,
) -> pd.Series:
    resolved_span = positive_int(span, name="span")
    resolved_span_min_periods = positive_int(min_periods, name="min_periods")
    return numeric_column(dataframe, col).ewm(
        span=resolved_span,
        adjust=adjust,
        min_periods=resolved_span_min_periods,
    ).mean()


def add_ema(
    dataframe: pd.DataFrame,
    col: str,
    span: int,
    output_col: str | None = None,
    min_periods: int = 1,
    adjust: bool = False,
) -> None:
    dataframe[output_col or f"{col}_ema{span}"] = calc_ema(
        dataframe,
        col=col,
        span=span,
        min_periods=min_periods,
        adjust=adjust,
    )
