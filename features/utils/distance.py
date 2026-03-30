from __future__ import annotations

import numpy as np
import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column


FEATURE_INFO = feature_info(
    "dist",
    "Log Distance Between Series",
    "utils",
    args=[
        feature_arg("col", "Source Column", "source"),
        feature_arg("reference", "Reference Column", "reference_source"),
    ],
)


def calc_distance_to_col(
    dataframe: pd.DataFrame,
    col: str,
    reference_col: str,
) -> pd.Series:
    source_series = numeric_column(dataframe, col)
    reference_series = numeric_column(dataframe, reference_col)
    return np.log(source_series / reference_series)


def add_distance_to_col(
    dataframe: pd.DataFrame,
    col: str,
    reference_col: str,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{col}_distance_to_{reference_col}"] = calc_distance_to_col(
        dataframe,
        col=col,
        reference_col=reference_col,
    )
