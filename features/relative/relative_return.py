from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column, positive_int


FEATURE_INFO = feature_info(
    "rel_ret",
    "Relative Return",
    "relative",
    args=[
        feature_arg("return", "Return Column", "return_source"),
        feature_arg("benchmark", "Benchmark Column", "benchmark_source"),
        feature_arg("window", "Lookback Periods", "periods"),
        feature_arg("benchmark_is_return", "Benchmark Is Return", "boolean_flag", False),
    ],
)


def calc_rel_return(
    dataframe: pd.DataFrame,
    return_col: str,
    benchmark_col: str,
    window: int,
    benchmark_is_return: bool = False,
) -> pd.Series:
    resolved_window = positive_int(window, name="window")
    return_series = numeric_column(dataframe, return_col)
    benchmark_series = numeric_column(dataframe, benchmark_col)
    if benchmark_is_return:
        return return_series - benchmark_series
    return return_series - benchmark_series.diff(resolved_window)


def add_rel_return(
    dataframe: pd.DataFrame,
    return_col: str,
    benchmark_col: str,
    window: int,
    output_col: str | None = None,
    benchmark_is_return: bool = False,
) -> None:
    dataframe[output_col or f"{return_col}_rel_to_{benchmark_col}"] = calc_rel_return(
        dataframe,
        return_col=return_col,
        benchmark_col=benchmark_col,
        window=window,
        benchmark_is_return=benchmark_is_return,
    )
