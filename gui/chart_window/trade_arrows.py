from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import pandas as pd

from gui.chart_window.arrow_overlays import ArrowOverlay


@dataclass(slots=True)
class TradeArrowColorScale:
    """Describe how trade returns map onto arrow colors."""

    negative_threshold: float = -10.0
    positive_threshold: float = 10.0
    negative_color: str = "#dc2626"
    neutral_color: str = "#ffffff"
    positive_color: str = "#16a34a"

    def resolve_color(self, percent_change: float) -> str:
        if percent_change <= 0:
            if percent_change <= self.negative_threshold:
                return self.negative_color
            if self.negative_threshold >= 0:
                return self.neutral_color
            return self._blend_colors(
                self.neutral_color,
                self.negative_color,
                percent_change / self.negative_threshold,
            )

        if percent_change >= self.positive_threshold:
            return self.positive_color
        if self.positive_threshold <= 0:
            return self.neutral_color
        return self._blend_colors(
            self.neutral_color,
            self.positive_color,
            percent_change / self.positive_threshold,
        )

    def _blend_colors(self, start_color: str, end_color: str, ratio: float) -> str:
        clamped_ratio = max(0.0, min(1.0, ratio))
        start_channels = [int(start_color[index : index + 2], 16) for index in (1, 3, 5)]
        end_channels = [int(end_color[index : index + 2], 16) for index in (1, 3, 5)]
        blended_channels = [
            int(start_channel + (end_channel - start_channel) * clamped_ratio)
            for start_channel, end_channel in zip(start_channels, end_channels, strict=True)
        ]
        return "#" + "".join(f"{channel:02x}" for channel in blended_channels)


def build_entry_exit_arrow_overlays(
    x_values: Sequence[object] | pd.Series,
    prices: Sequence[float] | pd.Series,
    buy_condition: Sequence[bool] | pd.Series,
    sell_condition: Sequence[bool] | pd.Series,
    *,
    pane: str = "main",
    width: float = 2.6,
    opacity: float = 0.95,
    color_scale: TradeArrowColorScale | None = None,
) -> tuple[ArrowOverlay, ...]:
    """Pair each new buy signal with the next sell signal and return arrow overlays."""

    x_series = pd.Series(x_values).reset_index(drop=True)
    price_series = pd.to_numeric(pd.Series(prices), errors="coerce").reset_index(drop=True)
    buy_series = pd.Series(buy_condition).fillna(False).astype(bool).reset_index(drop=True)
    sell_series = pd.Series(sell_condition).fillna(False).astype(bool).reset_index(drop=True)

    expected_length = len(x_series)
    if len(price_series) != expected_length:
        raise ValueError("Trade arrow prices must match the chart length.")
    if len(buy_series) != expected_length:
        raise ValueError("Buy condition length must match the chart length.")
    if len(sell_series) != expected_length:
        raise ValueError("Sell condition length must match the chart length.")

    resolved_color_scale = color_scale or TradeArrowColorScale()
    entry_index: int | None = None
    overlays: list[ArrowOverlay] = []

    for index in range(expected_length):
        price = price_series.iat[index]
        if entry_index is None:
            if buy_series.iat[index] and pd.notna(price):
                entry_index = index
            continue

        if not sell_series.iat[index] or pd.isna(price):
            continue

        entry_price = price_series.iat[entry_index]
        if pd.notna(entry_price):
            entry_price_float = float(entry_price)
            exit_price_float = float(price)
            percent_change = (
                ((exit_price_float - entry_price_float) / entry_price_float) * 100.0
                if entry_price_float != 0
                else 0.0
            )
            label_text = f"{percent_change:+.2f}%" if entry_price_float != 0 else None
            overlays.append(
                ArrowOverlay(
                    start_x=x_series.iat[entry_index],
                    start_y=entry_price_float,
                    end_x=x_series.iat[index],
                    end_y=exit_price_float,
                    pane=pane,
                    color=resolved_color_scale.resolve_color(percent_change),
                    width=width,
                    opacity=opacity,
                    label_text=label_text,
                    label_side="above" if exit_price_float > entry_price_float else "below",
                    label_visible_max_months=24,
                )
            )
        entry_index = None

    return tuple(overlays)
