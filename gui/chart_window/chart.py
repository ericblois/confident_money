from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets

from condition_script import evaluate_condition as _evaluate_condition_script


SeriesInput = str | Sequence[Any] | pd.Series

_DASH_STYLES = {
    "solid": QtCore.Qt.PenStyle.SolidLine,
    "dash": QtCore.Qt.PenStyle.DashLine,
    "dot": QtCore.Qt.PenStyle.DotLine,
    "dashdot": QtCore.Qt.PenStyle.DashDotLine,
    "dashdotdot": QtCore.Qt.PenStyle.DashDotDotLine,
}
_CHART_BACKGROUND = "#24211f"
_CHART_SURFACE = "#202837"
_CHART_BORDER = "#3b4455"
_CHART_AXIS_TEXT = "#cbd5e1"
_CHART_AXIS_LINE = "#566277"
_CHART_TITLE_TEXT = "#f8fafc"
_CHART_WEEK_DIVIDER = "#5b667b"
_CHART_CURSOR_LINE = "#e2e8f0"
_CHART_TOOLTIP_FILL = "#252b39"
_CHART_TOOLTIP_BORDER = "#64748b"
_CHART_TOOLTIP_HEADER = "#f8fafc"
_CHART_TOOLTIP_SECTION = "#94a3b8"
_CHART_TOOLTIP_TEXT = "#dbe4ee"


# Styling and hover helpers keep the main chart class focused on display logic.
@dataclass(slots=True)
class LineStyle:
    color: str = "#1f77b4"
    width: float = 2.0
    dash: str = "solid"
    opacity: float = 1.0

    def pen(self) -> QtGui.QPen:
        color = QtGui.QColor(self.color)
        color.setAlphaF(max(0.0, min(1.0, self.opacity)))
        pen = pg.mkPen(color=color, width=self.width)
        pen.setStyle(_DASH_STYLES.get(self.dash.lower(), QtCore.Qt.PenStyle.SolidLine))
        return pen


@dataclass(slots=True)
class _HoverSeriesData:
    pane_name: str
    name: str
    plot_x: np.ndarray
    raw_x: list[Any]
    y_values: np.ndarray
    color: str
    is_sorted: bool

    def nearest_index(self, target_x: float) -> int | None:
        if self.plot_x.size == 0:
            return None

        if self.is_sorted:
            index = int(np.searchsorted(self.plot_x, target_x))
            if index <= 0:
                return 0
            if index >= self.plot_x.size:
                return int(self.plot_x.size - 1)

            left_index = index - 1
            if abs(self.plot_x[index] - target_x) < abs(self.plot_x[left_index] - target_x):
                return index
            return left_index

        distances = np.abs(self.plot_x - target_x)
        return int(np.nanargmin(distances)) if distances.size else None


@dataclass(slots=True)
class _ViewSeriesData:
    plot_x: np.ndarray
    y_values: np.ndarray
    is_sorted: bool
    cached_visible_key: tuple[int, int] | None = None
    cached_visible_bounds: tuple[float, float] | None = None

    @classmethod
    def from_values(
        cls,
        plot_x: Sequence[float] | pd.Series | np.ndarray,
        y_values: Sequence[float] | pd.Series | np.ndarray,
    ) -> "_ViewSeriesData":
        plot_x_array = np.asarray(plot_x, dtype=float)
        y_array = np.asarray(y_values, dtype=float)
        finite_mask = np.isfinite(plot_x_array) & np.isfinite(y_array)
        finite_plot_x = plot_x_array[finite_mask]
        finite_y = y_array[finite_mask]
        return cls(
            plot_x=finite_plot_x,
            y_values=finite_y,
            is_sorted=finite_plot_x.size < 2 or bool(np.all(np.diff(finite_plot_x) >= 0)),
        )

    def visible_y_bounds(self, x_min: float, x_max: float) -> tuple[float, float] | None:
        if self.plot_x.size == 0:
            return None

        if self.is_sorted:
            start = int(np.searchsorted(self.plot_x, x_min, side="left"))
            end = int(np.searchsorted(self.plot_x, x_max, side="right"))
            visible_key = (start, end)
            if visible_key == self.cached_visible_key:
                return self.cached_visible_bounds

            if start >= end:
                bounds = None
            else:
                visible_y = self.y_values[start:end]
                bounds = (float(np.min(visible_y)), float(np.max(visible_y)))

            self.cached_visible_key = visible_key
            self.cached_visible_bounds = bounds
            return bounds

        visible_mask = (self.plot_x >= x_min) & (self.plot_x <= x_max)
        if not np.any(visible_mask):
            return None

        visible_y = self.y_values[visible_mask]
        return float(np.min(visible_y)), float(np.max(visible_y))


@dataclass(slots=True)
class _ChartPane:
    name: str
    y_label: str
    height_ratio: int
    view_box: "_AutoFitViewBox"
    plot_item: pg.PlotItem
    hover_line: pg.InfiniteLine | None = None
    hover_tooltip: pg.TextItem | None = None
    week_dividers: dict[float, pg.InfiniteLine] = field(default_factory=dict)
    series_count: int = 0

    @property
    def hover_title(self) -> str:
        return self.y_label or self.name.title()


@dataclass(slots=True)
class _ConditionRegionItem:
    pane: _ChartPane
    item: pg.LinearRegionItem


def _estimate_plot_half_width(plot_x_values: np.ndarray, index: int) -> float:
    gaps: list[float] = []

    if index > 0 and np.isfinite(plot_x_values[index - 1]) and np.isfinite(plot_x_values[index]):
        previous_gap = abs(float(plot_x_values[index] - plot_x_values[index - 1])) / 2.0
        if previous_gap > 0:
            gaps.append(previous_gap)

    if (
        index + 1 < plot_x_values.size
        and np.isfinite(plot_x_values[index + 1])
        and np.isfinite(plot_x_values[index])
    ):
        next_gap = abs(float(plot_x_values[index + 1] - plot_x_values[index])) / 2.0
        if next_gap > 0:
            gaps.append(next_gap)

    return gaps[0] if gaps else 0.5


def build_condition_region_ranges(
    condition_mask: Sequence[bool],
    plot_x_values: Sequence[float],
) -> list[tuple[float, float]]:
    """Return x-axis ranges that cover contiguous true segments."""

    mask = np.asarray(condition_mask, dtype=bool)
    plot_x = np.asarray(plot_x_values, dtype=float)

    if mask.size != plot_x.size:
        raise ValueError(
            "Condition mask length must match the chart x-axis length: "
            f"{mask.size} != {plot_x.size}"
        )

    if mask.size == 0:
        return []

    left_edges = np.empty(plot_x.size, dtype=float)
    right_edges = np.empty(plot_x.size, dtype=float)

    for index, center in enumerate(plot_x):
        half_width = _estimate_plot_half_width(plot_x, index)

        if index > 0 and np.isfinite(plot_x[index - 1]) and np.isfinite(center):
            left_edge = float((plot_x[index - 1] + center) / 2.0)
        else:
            left_edge = float(center - half_width)

        if index + 1 < plot_x.size and np.isfinite(plot_x[index + 1]) and np.isfinite(center):
            right_edge = float((center + plot_x[index + 1]) / 2.0)
        else:
            right_edge = float(center + half_width)

        left_edges[index] = min(left_edge, right_edge)
        right_edges[index] = max(left_edge, right_edge)

    visible_mask = mask & np.isfinite(plot_x)
    regions: list[tuple[float, float]] = []
    region_start: int | None = None

    for index, is_true in enumerate(visible_mask):
        if is_true and region_start is None:
            region_start = index
            continue

        if not is_true and region_start is not None:
            regions.append((left_edges[region_start], right_edges[index - 1]))
            region_start = None

    if region_start is not None:
        regions.append((left_edges[region_start], right_edges[plot_x.size - 1]))

    return regions


# Axis and view helpers make the chart readable while keeping y-scaling tied to
# the currently visible x-range.
class _ChartDateAxisItem(pg.AxisItem):
    """Map row positions back to their original datetime labels."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._dates: list[pd.Timestamp | pd.NaTType] = []
        self._has_intraday_values = False

    def set_values(self, values: Sequence[Any]) -> None:
        parsed = pd.to_datetime(pd.Series(values), errors="coerce")
        self._dates = [pd.NaT if pd.isna(value) else pd.Timestamp(value) for value in parsed]
        self._has_intraday_values = any(
            not pd.isna(timestamp) and timestamp != timestamp.normalize()
            for timestamp in self._dates
        )

    def tickStrings(self, values: list[float], scale: float, spacing: float) -> list[str]:
        del scale

        if not self._dates:
            return [""] * len(values)

        fmt = "%Y-%m-%d\n%H:%M" if self._has_intraday_values and abs(spacing) <= 24 else "%Y-%m-%d"
        labels: list[str] = []
        last_index: int | None = None

        for value in values:
            if not np.isfinite(value):
                labels.append("")
                continue

            index = int(round(value))
            if index < 0 or index >= len(self._dates) or index == last_index:
                labels.append("")
                continue

            timestamp = self._dates[index]
            labels.append("" if pd.isna(timestamp) else timestamp.strftime(fmt))
            last_index = index

        return labels


class _ChartValueAxisItem(pg.AxisItem):
    """Format y-axis labels consistently and keep horizontal grid density light."""

    def tickStrings(self, values: list[float], scale: float, spacing: float) -> list[str]:
        if self.logMode:
            return self.logTickStrings(values, scale, spacing)

        labels: list[str] = []
        for value in values:
            scaled_value = value * scale
            labels.append("" if not np.isfinite(scaled_value) else f"{scaled_value:.2f}")
        return labels

    def tickSpacing(self, minVal: float, maxVal: float, size: float) -> list[tuple[float, float]]:
        spacing_levels = super().tickSpacing(minVal, maxVal, size)
        if not spacing_levels:
            return spacing_levels

        major_spacing, major_offset = spacing_levels[0]
        if not np.isfinite(major_spacing) or major_spacing <= 0:
            return [spacing_levels[0]]

        return [(major_spacing, major_offset), (major_spacing / 2.0, major_offset)]


class _AutoFitViewBox(pg.ViewBox):
    """Keep the y-axis fitted to the data visible in the current x-range."""

    _HORIZONTAL_WHEEL_PAN_FRACTION = 0.12

    def __init__(self, *, vertical_fill_ratio: float = 0.9) -> None:
        super().__init__()
        self.setMouseEnabled(x=True, y=False)
        self.setMenuEnabled(False)

        self._padding_fraction = (1 - vertical_fill_ratio) / (2 * vertical_fill_ratio)
        self._series_data: list[_ViewSeriesData] = []
        self._last_y_range: tuple[float, float] | None = None
        self.sigXRangeChanged.connect(self.refit_y_range)

    def register_series(
        self,
        x_values: Sequence[float] | pd.Series | np.ndarray,
        y_values: Sequence[float] | pd.Series | np.ndarray,
    ) -> None:
        self._series_data.append(_ViewSeriesData.from_values(x_values, y_values))
        self._last_y_range = None

    def wheelEvent(self, ev: Any, axis: int | None = None) -> None:
        if axis != 1 and self.state["mouseEnabled"][0]:
            pan_view = self._x_pan_target_view()
            horizontal_pan = self._horizontal_wheel_pan_delta(
                ev,
                x_span=self._view_x_span(pan_view),
                view_width=self._view_width(pan_view),
                axis=axis,
            )
            if horizontal_pan is not None:
                pan_view._resetTarget()
                pan_view.translateBy(x=horizontal_pan)
                ev.accept()
                pan_view.sigRangeChangedManually.emit([True, False])
                return

        super().wheelEvent(ev, axis=axis)

    def _x_pan_target_view(self) -> pg.ViewBox:
        return self.linkedView(self.XAxis) or self

    def _horizontal_wheel_pan_delta(
        self,
        ev: Any,
        *,
        x_span: float,
        view_width: float,
        axis: int | None = None,
    ) -> float | None:
        pixel_delta = ev.pixelDelta() if hasattr(ev, "pixelDelta") else None
        if pixel_delta is not None:
            pixel_x = float(pixel_delta.x())
            pixel_y = float(pixel_delta.y())
            if pixel_x and abs(pixel_x) >= abs(pixel_y):
                return -x_span * (pixel_x / view_width)

        if axis == 0 or (
            hasattr(ev, "orientation")
            and ev.orientation() == QtCore.Qt.Orientation.Horizontal
        ):
            wheel_delta = float(ev.delta())
            if wheel_delta:
                return -x_span * (wheel_delta / 120.0) * self._HORIZONTAL_WHEEL_PAN_FRACTION

        return None

    def _view_x_span(self, view: pg.ViewBox) -> float:
        x_min, x_max = view.viewRange()[0]
        span = abs(float(x_max - x_min))
        return span if np.isfinite(span) and span > 0 else 1.0

    def _view_width(self, view: pg.ViewBox) -> float:
        width = float(view.sceneBoundingRect().width())
        if width <= 0:
            width = float(view.boundingRect().width())
        return width if width > 0 else 1.0

    def refit_y_range(self, *_: Any) -> None:
        min_y: float | None = None
        max_y: float | None = None
        x_min, x_max = self.viewRange()[0]
        if not np.isfinite(x_min) or not np.isfinite(x_max):
            return
        if x_min > x_max:
            x_min, x_max = x_max, x_min

        for series_data in self._series_data:
            visible_bounds = series_data.visible_y_bounds(x_min, x_max)
            if visible_bounds is None:
                continue

            series_min, series_max = visible_bounds
            min_y = series_min if min_y is None else min(min_y, series_min)
            max_y = series_max if max_y is None else max(max_y, series_max)

        if min_y is None or max_y is None:
            self._last_y_range = None
            return

        if min_y == max_y:
            padding = abs(min_y) * self._padding_fraction or 1.0
        else:
            padding = (max_y - min_y) * self._padding_fraction
        y_range = (min_y - padding, max_y + padding)
        if self._last_y_range is not None and np.allclose(
            y_range,
            self._last_y_range,
            rtol=1e-9,
            atol=1e-9,
        ):
            return

        self._last_y_range = y_range
        self.setYRange(*y_range, padding=0.0)


class DataChart:
    """Display an interactive PyQtGraph line chart in a native desktop window."""

    _VIEW_FEEDBACK_INTERVAL_MS = 16

    def __init__(
        self,
        data: pd.DataFrame,
        *,
        x_column: str = "date",
        title: str = "Interactive Chart",
        y_label: str = "Value",
        show_spikes: bool = True,
    ) -> None:
        if x_column not in data.columns:
            raise ValueError(f"Missing x-axis column: {x_column}")

        self.data = data.copy()
        self.x_column = x_column
        self.title = title
        self.y_label = y_label
        self.show_spikes = show_spikes

        self.data[self.x_column] = self._coerce_x_values(self.data[self.x_column])
        self._x_is_datetime = pd.api.types.is_datetime64_any_dtype(self.data[self.x_column])

        existing_app = QtWidgets.QApplication.instance()
        self._owns_app = existing_app is None
        self._app = existing_app or QtWidgets.QApplication([])

        pg.setConfigOptions(antialias=False, leftButtonPan=True)

        self._layout_widget = pg.GraphicsLayoutWidget()
        self._layout_widget.setBackground(_CHART_BACKGROUND)
        self._window: QtWidgets.QMainWindow | None = None

        self._panes: list[_ChartPane] = []
        self._pane_by_name: dict[str, _ChartPane] = {}
        self._hover_series_data: list[_HoverSeriesData] = []
        self._hover_x_position: float | None = None
        self._active_hover_pane: _ChartPane | None = None
        self._mouse_proxy: pg.SignalProxy | None = None
        self._view_feedback_timer = QtCore.QTimer(self._layout_widget)
        self._view_feedback_timer.setSingleShot(True)
        self._view_feedback_timer.setInterval(self._VIEW_FEEDBACK_INTERVAL_MS)
        self._view_feedback_timer.timeout.connect(self._apply_view_feedback)
        self._default_plot_x = self._to_plot_x(self.data[self.x_column])
        self._condition_region_items: list[_ConditionRegionItem] = []
        self._week_divider_positions = self._build_week_divider_positions()

        self._create_pane("main", y_label=self.y_label, height_ratio=3)
        if self.show_spikes:
            self._configure_hover_feedback()

    def _build_bottom_axis(self) -> pg.AxisItem:
        if not self._x_is_datetime:
            return pg.AxisItem(orientation="bottom")

        axis = _ChartDateAxisItem(orientation="bottom")
        axis.set_values(self.data[self.x_column])
        return axis

    def _build_left_axis(self) -> pg.AxisItem:
        return _ChartValueAxisItem(orientation="left")

    def _configure_pane_plot(self, pane: _ChartPane) -> None:
        pane.plot_item.setLabel("left", pane.y_label, color=_CHART_AXIS_TEXT)
        pane.plot_item.showGrid(x=False, y=True, alpha=0.18)
        pane.plot_item.setClipToView(True)
        pane.plot_item.setDownsampling(auto=True, mode="peak")
        for axis_name in ("left", "bottom"):
            axis = pane.plot_item.getAxis(axis_name)
            axis.setPen(pg.mkPen(_CHART_AXIS_LINE))
            axis.setTextPen(pg.mkPen(_CHART_AXIS_TEXT))
            axis.setTickPen(pg.mkPen(_CHART_AXIS_LINE))
            axis.setStyle(tickAlpha=0.35)

    def _create_pane(
        self,
        name: str,
        *,
        y_label: str,
        height_ratio: int,
    ) -> _ChartPane:
        view_box = _AutoFitViewBox(vertical_fill_ratio=0.9)
        plot_item = self._layout_widget.addPlot(
            row=len(self._panes),
            col=0,
            viewBox=view_box,
            axisItems={
                "bottom": self._build_bottom_axis(),
                "left": self._build_left_axis(),
            },
        )
        plot_item.addLegend(offset=(10, 10))
        if plot_item.legend is not None:
            plot_item.legend.setBrush(pg.mkBrush(_CHART_SURFACE))
            plot_item.legend.setPen(pg.mkPen(_CHART_BORDER))
            plot_item.legend.setLabelTextColor(_CHART_AXIS_TEXT)

        if self._panes:
            plot_item.setXLink(self._panes[0].plot_item)

        pane = _ChartPane(
            name=name,
            y_label=y_label,
            height_ratio=max(1, int(height_ratio)),
            view_box=view_box,
            plot_item=plot_item,
        )
        self._configure_pane_plot(pane)
        self._panes.append(pane)
        self._pane_by_name[name] = pane

        self._set_pane_height(len(self._panes) - 1, pane.height_ratio)
        self._refresh_pane_axes()

        if self.show_spikes:
            self._attach_hover_feedback_to_pane(pane)

        pane.view_box.sigXRangeChanged.connect(self._handle_view_range_changed)
        self._sync_week_dividers_for_pane(pane)
        return pane

    def _set_pane_height(self, row: int, height_ratio: int) -> None:
        layout = getattr(self._layout_widget.ci, "layout", None)
        if layout is not None and hasattr(layout, "setRowStretchFactor"):
            layout.setRowStretchFactor(row, max(1, int(height_ratio)))

    def _refresh_pane_axes(self) -> None:
        for index, pane in enumerate(self._panes):
            pane.plot_item.setLabel("left", pane.y_label, color=_CHART_AXIS_TEXT)
            if index == 0:
                pane.plot_item.setTitle(self.title, color=_CHART_TITLE_TEXT, size="14pt")
            else:
                pane.plot_item.setTitle("")

            if index == len(self._panes) - 1:
                pane.plot_item.showAxis("bottom")
                pane.plot_item.setLabel("bottom", self.x_column.title(), color=_CHART_AXIS_TEXT)
            else:
                pane.plot_item.hideAxis("bottom")

    def _configure_hover_feedback(self) -> None:
        for pane in self._panes:
            self._attach_hover_feedback_to_pane(pane)

        self._mouse_proxy = pg.SignalProxy(
            self._layout_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._handle_mouse_moved,
        )

    def _attach_hover_feedback_to_pane(self, pane: _ChartPane) -> None:
        if pane.hover_line is None:
            pane.hover_line = pg.InfiniteLine(
                pos=0.0,
                angle=90,
                pen=self._build_hover_line_pen(),
                movable=False,
            )
            pane.hover_line.setZValue(9)
            pane.hover_line.hide()
            pane.plot_item.addItem(pane.hover_line, ignoreBounds=True)

        if pane.hover_tooltip is None:
            tooltip_fill = QtGui.QColor(_CHART_TOOLTIP_FILL)
            tooltip_fill.setAlpha(235)
            pane.hover_tooltip = pg.TextItem(
                anchor=(0, 1),
                border=pg.mkPen(_CHART_TOOLTIP_BORDER),
                fill=pg.mkBrush(tooltip_fill),
            )
            pane.hover_tooltip.setZValue(10)
            pane.hover_tooltip.hide()
            pane.plot_item.addItem(pane.hover_tooltip, ignoreBounds=True)

    def _build_hover_line_pen(self) -> QtGui.QPen:
        pen = QtGui.QPen(QtGui.QColor(_CHART_CURSOR_LINE))
        pen.setCosmetic(True)
        pen.setWidthF(2.0)
        pen.setStyle(QtCore.Qt.PenStyle.SolidLine)
        return pen

    def _build_week_divider_positions(self) -> list[float]:
        if not self._x_is_datetime:
            return []

        timestamps = pd.Series(self.data[self.x_column]).reset_index(drop=True)
        week_periods = timestamps.dt.to_period("W-SUN")
        divider_positions: list[float] = []

        for index in range(1, len(week_periods)):
            if pd.isna(timestamps.iloc[index - 1]) or pd.isna(timestamps.iloc[index]):
                continue
            if week_periods.iloc[index] == week_periods.iloc[index - 1]:
                continue
            divider_positions.append(float(index) - 0.5)

        return divider_positions

    def _build_week_divider_pen(self) -> QtGui.QPen:
        pen = QtGui.QPen(QtGui.QColor(_CHART_WEEK_DIVIDER))
        pen.setCosmetic(True)
        pen.setWidthF(1.0)
        pen.setStyle(QtCore.Qt.PenStyle.CustomDashLine)
        pen.setDashPattern([4.0, 4.0])
        return pen

    def _visible_week_divider_positions(self, x_min: float, x_max: float) -> list[float]:
        if not self._week_divider_positions or not self._x_is_datetime:
            return []

        start_index = max(0, int(np.ceil(x_min)))
        end_index = min(len(self.data) - 1, int(np.floor(x_max)))
        if end_index < start_index:
            return []

        visible_dates = self.data[self.x_column].iloc[start_index : end_index + 1].dropna()
        if visible_dates.empty:
            return []

        visible_start = pd.Timestamp(visible_dates.iloc[0])
        visible_end = pd.Timestamp(visible_dates.iloc[-1])
        if visible_end >= visible_start + pd.DateOffset(months=6):
            return []

        return [
            x_position
            for x_position in self._week_divider_positions
            if x_min <= x_position <= x_max
        ]

    def _sync_week_dividers(self) -> None:
        for pane in self._panes:
            self._sync_week_dividers_for_pane(pane)

    def _sync_week_dividers_for_pane(self, pane: _ChartPane) -> None:
        x_min, x_max = pane.view_box.viewRange()[0]
        visible_positions = set(self._visible_week_divider_positions(x_min, x_max))

        for x_position, divider in list(pane.week_dividers.items()):
            if x_position in visible_positions:
                continue
            pane.plot_item.removeItem(divider)
            del pane.week_dividers[x_position]

        if not visible_positions:
            return

        divider_pen = self._build_week_divider_pen()
        for x_position in sorted(visible_positions):
            if x_position in pane.week_dividers:
                continue

            divider = pg.InfiniteLine(
                pos=x_position,
                angle=90,
                pen=divider_pen,
                movable=False,
            )
            divider.setZValue(-4)
            pane.plot_item.addItem(divider, ignoreBounds=True)
            pane.week_dividers[x_position] = divider

    def _handle_mouse_moved(self, event: tuple[Any, ...]) -> None:
        active_pane = self._pane_at_scene_position(event[0])
        if active_pane is None:
            self._hide_hover_feedback()
            return

        mouse_point = active_pane.view_box.mapSceneToView(event[0])
        hover_lines, snapped_x = self._build_hover_lines(mouse_point.x())
        if not hover_lines:
            self._hide_hover_feedback()
            return

        self._hover_x_position = snapped_x
        self._active_hover_pane = active_pane
        self._update_hover_line()

        if active_pane.hover_tooltip is None:
            return

        for pane in self._panes:
            if pane.hover_tooltip is not None and pane is not active_pane:
                pane.hover_tooltip.hide()

        active_pane.hover_tooltip.setHtml("<br>".join(hover_lines))
        self._position_hover_tooltip(active_pane, snapped_x, mouse_point.y())
        active_pane.hover_tooltip.show()

    def _pane_at_scene_position(self, position: Any) -> _ChartPane | None:
        for pane in self._panes:
            if pane.view_box.sceneBoundingRect().contains(position):
                return pane
        return None

    def _handle_view_range_changed(self, *_: Any) -> None:
        if not self.show_spikes and not self._week_divider_positions:
            return
        self._view_feedback_timer.start()

    def _apply_view_feedback(self) -> None:
        self._update_hover_line()
        self._sync_week_dividers()

    def _hide_hover_feedback(self) -> None:
        self._hover_x_position = None
        self._active_hover_pane = None
        for pane in self._panes:
            if pane.hover_line is not None:
                pane.hover_line.hide()
            if pane.hover_tooltip is not None:
                pane.hover_tooltip.hide()

    def _update_hover_line(self) -> None:
        if self._hover_x_position is None:
            for pane in self._panes:
                if pane.hover_line is not None:
                    pane.hover_line.hide()
            return

        for pane in self._panes:
            if pane.hover_line is None:
                continue

            pane.hover_line.setPos(float(self._hover_x_position))
            pane.hover_line.show()

    def _build_hover_lines(self, target_x: float) -> tuple[list[str], float]:
        snapped = self._snap_hover_x(target_x)
        if snapped is None:
            return [], target_x

        snapped_raw_x, snapped_plot_x = snapped
        rows: list[str] = []
        current_pane_name: str | None = None

        for hover_data in self._hover_series_data:
            index = hover_data.nearest_index(snapped_plot_x)
            if index is None:
                continue

            matched_plot_x = float(hover_data.plot_x[index])
            if not self._hover_points_match(matched_plot_x, snapped_plot_x):
                continue

            if len(self._panes) > 1 and hover_data.pane_name != current_pane_name:
                pane = self._pane_by_name[hover_data.pane_name]
                rows.append(self._format_hover_section_header(pane.hover_title))
                current_pane_name = hover_data.pane_name

            rows.append(
                self._format_hover_row(
                    name=hover_data.name,
                    y_value=float(hover_data.y_values[index]),
                    color=hover_data.color,
                )
            )

        if not rows:
            return [], target_x

        header = (
            f"<span style='color:{_CHART_TOOLTIP_HEADER}; font-size:11pt; font-weight:600;'>"
            f"{self._format_hover_x_value(snapped_raw_x)}"
            "</span>"
        )
        return [header, *rows], snapped_plot_x

    def _hover_points_match(self, point_x: float, snapped_x: float) -> bool:
        return bool(np.isclose(point_x, snapped_x, rtol=1e-9, atol=1e-9))

    def _snap_hover_x(self, target_x: float) -> tuple[Any, float] | None:
        best_match: tuple[Any, float, float] | None = None

        for hover_data in self._hover_series_data:
            index = hover_data.nearest_index(target_x)
            if index is None:
                continue

            plot_x = float(hover_data.plot_x[index])
            distance = abs(plot_x - target_x)
            if best_match is None or distance < best_match[2]:
                best_match = (hover_data.raw_x[index], plot_x, distance)

        if best_match is None:
            return None
        return best_match[0], best_match[1]

    def _format_hover_section_header(self, title: str) -> str:
        return (
            f"<span style='color:{_CHART_TOOLTIP_SECTION}; font-size:9pt; font-weight:600;'>"
            f"{title}"
            "</span>"
        )

    def _format_hover_row(self, *, name: str, y_value: float, color: str) -> str:
        return (
            f"<span style='color:{color}; font-weight:600;'>&#9632;</span> "
            f"<span style='color:{_CHART_TOOLTIP_TEXT}; font-size:10pt;'>{name}: {self._format_hover_number(y_value)}</span>"
        )

    def _format_hover_x_value(self, value: Any) -> str:
        if self._x_is_datetime:
            timestamp = pd.Timestamp(value)
            if pd.isna(timestamp):
                return ""
            return timestamp.strftime("%Y-%m-%d" if timestamp == timestamp.normalize() else "%Y-%m-%d %H:%M")
        return self._format_hover_number(value)

    def _format_hover_number(self, value: Any) -> str:
        numeric_value = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
        return str(value) if pd.isna(numeric_value) else f"{float(numeric_value):,.2f}"

    def _position_hover_tooltip(
        self,
        pane: _ChartPane,
        x_position: float,
        y_position: float,
    ) -> None:
        if pane.hover_tooltip is None:
            return

        x_min, x_max = pane.view_box.viewRange()[0]
        y_min, y_max = pane.view_box.viewRange()[1]
        x_padding = (x_max - x_min) * 0.02 or 1.0
        y_padding = (y_max - y_min) * 0.02 or 1.0

        place_left = x_position > (x_min + x_max) / 2
        place_top = y_position > (y_min + y_max) / 2
        tooltip_x = x_position - x_padding if place_left else x_position + x_padding
        tooltip_y = (
            max(y_min + y_padding, y_position - y_padding)
            if place_top
            else min(y_max - y_padding, y_position + y_padding)
        )

        pane.hover_tooltip.setAnchor((1 if place_left else 0, 1 if place_top else 0))
        pane.hover_tooltip.setPos(tooltip_x, tooltip_y)

    def _resolve_series(
        self,
        values: SeriesInput | None,
        *,
        name: str,
        default: pd.Series | None = None,
    ) -> pd.Series:
        if values is None:
            if default is None:
                raise ValueError(f"Missing series for {name}")
            resolved = default
        elif isinstance(values, str):
            if values not in self.data.columns:
                raise ValueError(f"Missing series column for {name}: {values}")
            resolved = self.data[values]
        else:
            resolved = pd.Series(values)

        resolved = pd.Series(resolved)
        if len(resolved) != len(self.data):
            raise ValueError(
                f"Series length mismatch for {name}: expected {len(self.data)}, got {len(resolved)}"
            )

        if resolved.index.equals(self.data.index):
            return resolved

        if isinstance(values, pd.Series):
            # Align labeled series by chart row index so plotted values and
            # condition masks stay synced with the chart dataframe.
            if resolved.index.is_unique and self.data.index.is_unique:
                if (
                    resolved.index.difference(self.data.index).empty
                    and self.data.index.difference(resolved.index).empty
                ):
                    return resolved.reindex(self.data.index)
            raise ValueError(
                f"Series index mismatch for {name}: expected values aligned to the chart rows."
            )

        resolved.index = self.data.index
        return resolved

    def _coerce_x_values(self, values: Sequence[Any] | pd.Series) -> pd.Series:
        series = pd.Series(values).copy()
        parsed = pd.to_datetime(series, errors="coerce")
        return parsed if parsed.notna().any() else series

    def _to_plot_x(self, values: pd.Series) -> pd.Series:
        # Datetime values are plotted as row positions so the custom axis can
        # format clean date labels from the original values.
        if pd.api.types.is_datetime64_any_dtype(values):
            return pd.Series(
                np.arange(len(values), dtype=float),
                index=values.index,
                dtype=float,
            )
        return pd.to_numeric(values, errors="coerce")

    def _resolve_pane(self, pane: str) -> _ChartPane:
        if pane not in self._pane_by_name:
            raise ValueError(f"Unknown chart pane: {pane}")
        return self._pane_by_name[pane]

    @property
    def widget(self) -> pg.GraphicsLayoutWidget:
        """Expose the chart widget so it can be embedded in other Qt windows."""

        return self._layout_widget

    @property
    def application(self) -> QtWidgets.QApplication:
        return self._app

    @property
    def owns_application(self) -> bool:
        return self._owns_app

    def refresh_view(self, *, auto_range: bool = False) -> None:
        """Refresh pane ranges while optionally preserving the current x-zoom."""

        for pane in self._panes:
            if auto_range:
                pane.plot_item.autoRange()
            pane.view_box.refit_y_range()
        self._sync_week_dividers()

    def run_application(self) -> None:
        """Start the Qt event loop when this chart created the QApplication."""

        if self._owns_app:
            self._app.exec()

    def clear_condition_regions(self) -> "DataChart":
        """Remove every highlighted condition range from the chart."""

        while self._condition_region_items:
            region = self._condition_region_items.pop()
            region.pane.plot_item.removeItem(region.item)

        return self

    def evaluate_condition_script(self, script: str) -> pd.Series:
        """Evaluate a condition script against the same chart dataframe used for display."""

        return self._resolve_condition_mask(_evaluate_condition_script(self.data, script))

    def set_condition_regions(
        self,
        condition: SeriesInput,
        *,
        color: str = "#22c55e",
        opacity: float = 0.18,
        panes: Sequence[str] | None = None,
        clear_existing: bool = True,
    ) -> int:
        """Highlight contiguous x-ranges where a boolean condition is true."""

        condition_mask = self._resolve_condition_mask(condition)
        region_ranges = build_condition_region_ranges(
            condition_mask.to_numpy(dtype=bool, copy=False),
            self._default_plot_x.to_numpy(dtype=float, copy=False),
        )

        if clear_existing:
            self.clear_condition_regions()
        if not region_ranges:
            return 0

        target_panes = (
            [self._resolve_pane(pane_name) for pane_name in panes]
            if panes is not None
            else list(self._panes)
        )
        brush = self._build_condition_region_brush(color=color, opacity=opacity)
        pen = self._build_condition_region_pen(color=color, opacity=opacity)

        for pane in target_panes:
            for x_min, x_max in region_ranges:
                region_item = pg.LinearRegionItem(
                    values=(x_min, x_max),
                    orientation="vertical",
                    brush=brush,
                    pen=pen,
                    movable=False,
                )
                region_item.setZValue(-5)
                pane.plot_item.addItem(region_item, ignoreBounds=True)
                self._condition_region_items.append(
                    _ConditionRegionItem(pane=pane, item=region_item)
                )

        return len(region_ranges)

    def _resolve_condition_mask(self, condition: SeriesInput) -> pd.Series:
        return self._resolve_series(condition, name="condition mask").fillna(False).astype(bool)

    def add_pane(
        self,
        name: str,
        *,
        y_label: str | None = None,
        height_ratio: int = 1,
    ) -> "DataChart":
        """Add a named pane below the existing chart panes."""

        if name in self._pane_by_name:
            raise ValueError(f"Chart pane already exists: {name}")

        self._create_pane(
            name,
            y_label=y_label or name.title(),
            height_ratio=height_ratio,
        )
        return self

    def add_close_line(
        self,
        *,
        column: str = "close",
        name: str = "Close",
        color: str = "#1f77b4",
        width: float = 2.0,
        pane: str = "main",
    ) -> "DataChart":
        """Convenience helper for plotting a standard close-price line."""

        return self.add_line(name=name, y=column, color=color, width=width, pane=pane)

    def add_horizontal_line(
        self,
        *,
        name: str,
        y: float,
        pane: str = "main",
        color: str = "#94a3b8",
        width: float = 1.5,
        dash: str = "dash",
        opacity: float = 1.0,
        hover: bool = False,
    ) -> "DataChart":
        """Plot a constant horizontal reference line across a pane."""

        return self.add_line(
            name=name,
            y=np.full(len(self.data), float(y), dtype=float),
            pane=pane,
            color=color,
            width=width,
            dash=dash,
            opacity=opacity,
            hover=hover,
        )

    def add_line(
        self,
        name: str,
        y: SeriesInput,
        *,
        x: SeriesInput | None = None,
        pane: str = "main",
        color: str = "#1f77b4",
        width: float = 2.0,
        dash: str = "solid",
        opacity: float = 1.0,
        hover: bool = True,
    ) -> "DataChart":
        """Plot a line, register it for hover feedback, and include it in auto-fit."""

        target_pane = self._resolve_pane(pane)
        x_values = self._coerce_x_values(
            self._resolve_series(x, name=f"x-axis for {name}", default=self.data[self.x_column])
        )
        if pd.api.types.is_datetime64_any_dtype(x_values) != self._x_is_datetime:
            expected = "datetime" if self._x_is_datetime else "numeric"
            raise ValueError(f"X-axis type mismatch for {name}: chart expects {expected} values.")

        y_values = pd.to_numeric(self._resolve_series(y, name=name), errors="coerce")
        style = LineStyle(color=color, width=width, dash=dash, opacity=opacity)

        self._plot_line(
            pane=target_pane,
            name=name,
            x_values=x_values,
            y_values=y_values,
            style=style,
            hover=hover,
        )
        return self

    def _plot_line(
        self,
        *,
        pane: _ChartPane,
        name: str,
        x_values: pd.Series,
        y_values: pd.Series,
        style: LineStyle,
        hover: bool,
    ) -> None:
        plot_x = self._to_plot_x(x_values)
        plot_x_array = plot_x.to_numpy(dtype=float, copy=False)
        y_array = y_values.to_numpy(dtype=float, copy=False)
        item = pane.plot_item.plot(
            x=plot_x_array,
            y=y_array,
            name=name,
            pen=style.pen(),
            connect="finite",
            antialias=False,
        )
        if np.isfinite(plot_x_array).all() and np.isfinite(y_array).all():
            item.setSkipFiniteCheck(True)

        pane.view_box.register_series(plot_x_array, y_array)
        if hover:
            self._register_hover_series(
                pane_name=pane.name,
                name=name,
                x_values=x_values,
                plot_x=plot_x,
                y_values=y_values,
                color=style.color,
            )

        if pane.series_count == 0:
            pane.plot_item.autoRange()
        else:
            item.informViewBoundsChanged()

        pane.series_count += 1
        pane.view_box.refit_y_range()

    def _register_hover_series(
        self,
        *,
        pane_name: str,
        name: str,
        x_values: pd.Series,
        plot_x: pd.Series,
        y_values: pd.Series,
        color: str,
    ) -> None:
        hover_mask = plot_x.notna() & y_values.notna()
        if not hover_mask.any():
            return

        hover_plot_x = plot_x[hover_mask].to_numpy(dtype=float, copy=True)
        self._hover_series_data.append(
            _HoverSeriesData(
                pane_name=pane_name,
                name=name,
                plot_x=hover_plot_x,
                raw_x=x_values[hover_mask].reset_index(drop=True).tolist(),
                y_values=y_values[hover_mask].to_numpy(dtype=float, copy=True),
                color=color,
                is_sorted=hover_plot_x.size < 2 or bool(np.all(np.diff(hover_plot_x) >= 0)),
            )
        )

    def _build_condition_region_brush(
        self,
        *,
        color: str,
        opacity: float,
    ) -> QtGui.QBrush:
        fill_color = QtGui.QColor(color)
        fill_color.setAlphaF(max(0.0, min(1.0, opacity)))
        return pg.mkBrush(fill_color)

    def _build_condition_region_pen(
        self,
        *,
        color: str,
        opacity: float,
    ) -> QtGui.QPen:
        border_color = QtGui.QColor(color)
        border_color.setAlphaF(max(0.0, min(1.0, opacity * 1.4)))
        pen = pg.mkPen(border_color, width=1.0)
        pen.setCosmetic(True)
        return pen

    def _ensure_window(self, *, width: int, height: int) -> QtWidgets.QMainWindow:
        if self._window is None:
            window = QtWidgets.QMainWindow()
            window.setWindowTitle(self.title)
            window.resize(width, height)
            window.setCentralWidget(self._layout_widget)
            self._window = window
        return self._window

    def show(self, *, width: int = 1280, height: int = 800) -> None:
        """Open the chart in a native window and start the Qt event loop if needed."""

        window = self._ensure_window(width=width, height=height)
        window.show()
        window.raise_()
        window.activateWindow()
        self.refresh_view(auto_range=True)
        self.run_application()
