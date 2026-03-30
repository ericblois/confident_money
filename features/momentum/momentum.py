from __future__ import annotations

import numpy as np
import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column


FEATURE_INFO = feature_info(
    "mom",
    "Momentum",
    "momentum",
    args=[
        feature_arg("return", "Return Column", "return_source"),
        feature_arg("volatility", "Volatility Column", "volatility_source"),
    ],
)


def calc_momentum(
    dataframe: pd.DataFrame,
    return_col: str,
    volatility_col: str,
) -> pd.Series:
    return_series = numeric_column(dataframe, return_col)
    volatility_series = numeric_column(dataframe, volatility_col)
    return return_series / volatility_series.replace(0.0, np.nan)


def add_momentum(
    dataframe: pd.DataFrame,
    return_col: str,
    volatility_col: str,
    output_col: str | None = None,
) -> None:
    dataframe[output_col or f"{return_col}_momentum"] = calc_momentum(
        dataframe,
        return_col=return_col,
        volatility_col=volatility_col,
    )
