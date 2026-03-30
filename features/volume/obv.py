from __future__ import annotations

import pandas as pd

from .._shared import feature_arg, feature_info, numeric_column


FEATURE_INFO = feature_info(
    "obv",
    "On-Balance Volume",
    "volume",
    args=[
        feature_arg("close", "Close Column", "close_source", "close"),
        feature_arg("volume", "Volume Column", "volume_source", "volume"),
    ],
)


def calc_obv(
    dataframe: pd.DataFrame,
    close_col: str = "close",
    volume_col: str = "volume",
) -> pd.Series:
    close_delta = numeric_column(dataframe, close_col).diff()
    direction = close_delta.gt(0.0).astype(int) - close_delta.lt(0.0).astype(int)
    return (direction.fillna(0).astype(float) * numeric_column(dataframe, volume_col)).cumsum()


def add_obv(
    dataframe: pd.DataFrame,
    close_col: str = "close",
    volume_col: str = "volume",
    output_col: str | None = None,
) -> None:
    dataframe[output_col or "obv"] = calc_obv(
        dataframe,
        close_col=close_col,
        volume_col=volume_col,
    )
