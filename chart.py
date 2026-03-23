from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np
import pandas as pd
import pyqtgraph as pg
from PySide6 import QtCore, QtGui, QtWidgets


SeriesInput = str | Sequence[Any] | pd.Series

_DASH_STYLES = {
    "solid": QtCore.Qt.PenStyle.SolidLine,
    "dash": QtCore.Qt.PenStyle.DashLine,
    "dot": QtCore.Qt.PenStyle.DotLine,
    "dashdot": QtCore.Qt.PenStyle.DashDotLine,
    "dashdotdot": QtCore.Qt.PenStyle.DashDotDotLine,
}


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


class _AutoFitViewBox(pg.ViewBox):
    """Keep the y-axis fitted to the data visible in the current x-range."""

    def __init__(self, *, vertical_fill_ratio: float = 0.9) -> None:
        super().__init__()
        self.setMouseEnabled(x=True, y=False)
        self.setMenuEnabled(False)

        self._padding_fraction = (1 - vertical_fill_ratio) / (2 * vertical_fill_ratio)
        self._series_data: list[tuple[pd.Series, pd.Series]] = []
        self.sigXRangeChanged.connect(self.refit_y_range)

    def register_series(self, x_values: pd.Series, y_values: pd.Series) -> None:
        self._series_data.append((x_values, y_values))

    def refit_y_range(self, *_: Any) -> None:
        min_y: float | None = None
        max_y: float | None = None
        x_min, x_max = self.viewRange()[0]

        for x_values, y_values in self._series_data:
            visible_mask = x_values.between(x_min, x_max, inclusive="both") & y_values.notna()
            visible_values = y_values[visible_mask]
            if visible_values.empty:
                continue

            series_min = float(visible_values.min())
            series_max = float(visible_values.max())
            min_y = series_min if min_y is None else min(min_y, series_min)
            max_y = series_max if max_y is None else max(max_y, series_max)

        if min_y is None or max_y is None:
            return

        if min_y == max_y:
            padding = abs(min_y) * self._padding_fraction or 1.0
        else:
            padding = (max_y - min_y) * self._padding_fraction
        self.setYRange(min_y - padding, max_y + padding, padding=0.0)


class DataChart:
    """Display an interactive PyQtGraph line chart in a native desktop window."""

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

        self._view_box = _AutoFitViewBox(vertical_fill_ratio=0.9)
        self._plot_widget = pg.PlotWidget(
            viewBox=self._view_box,
            axisItems={"bottom": self._build_bottom_axis()},
            background="w",
        )
        self._plot_item = self._plot_widget.getPlotItem()
        self._plot_item.addLegend(offset=(10, 10))

        self._window: QtWidgets.QMainWindow | None = None
        self._series_count = 0
        self._hover_series_data: list[_HoverSeriesData] = []
        self._hover_x_position: float | None = None
        self._hover_line: pg.PlotCurveItem | None = None
        self._hover_tooltip: pg.TextItem | None = None
        self._mouse_proxy: pg.SignalProxy | None = None

        self._configure_plot()
        if self.show_spikes:
            self._configure_hover_feedback()

    def _build_bottom_axis(self) -> pg.AxisItem:
        if not self._x_is_datetime:
            return pg.AxisItem(orientation="bottom")

        axis = _ChartDateAxisItem(orientation="bottom")
        axis.set_values(self.data[self.x_column])
        return axis

    def _configure_plot(self) -> None:
        self._plot_item.setTitle(self.title, color="#222222", size="14pt")
        self._plot_item.setLabel("bottom", self.x_column.title(), color="#444444")
        self._plot_item.setLabel("left", self.y_label, color="#444444")
        self._plot_item.showGrid(x=True, y=True, alpha=0.15)
        self._plot_item.setClipToView(True)
        self._plot_item.setDownsampling(auto=True, mode="peak")

    def _configure_hover_feedback(self) -> None:
        self._hover_line = pg.PlotCurveItem(
            x=[],
            y=[],
            pen=self._build_hover_line_pen(),
            connect="all",
            antialias=False,
        )
        self._hover_line.setZValue(9)
        self._hover_line.hide()
        self._plot_item.addItem(self._hover_line, ignoreBounds=True)

        self._hover_tooltip = pg.TextItem(
            anchor=(0, 1),
            border=pg.mkPen("#b7c1cc"),
            fill=pg.mkBrush(255, 255, 255, 235),
        )
        self._hover_tooltip.setZValue(10)
        self._hover_tooltip.hide()
        self._plot_item.addItem(self._hover_tooltip, ignoreBounds=True)

        self._mouse_proxy = pg.SignalProxy(
            self._plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._handle_mouse_moved,
        )
        self._view_box.sigRangeChanged.connect(self._handle_view_range_changed)

    def _build_hover_line_pen(self) -> QtGui.QPen:
        pen = QtGui.QPen(QtGui.QColor("#334155"))
        pen.setCosmetic(True)
        pen.setWidthF(2.0)
        pen.setStyle(QtCore.Qt.PenStyle.CustomDashLine)
        pen.setDashPattern([4.0, 3.0])
        return pen

    def _handle_mouse_moved(self, event: tuple[Any, ...]) -> None:
        if self._hover_line is None or self._hover_tooltip is None:
            return

        position = event[0]
        if not self._plot_item.sceneBoundingRect().contains(position):
            self._hide_hover_feedback()
            return

        mouse_point = self._view_box.mapSceneToView(position)
        hover_lines, snapped_x = self._build_hover_lines(mouse_point.x())
        if not hover_lines:
            self._hide_hover_feedback()
            return

        self._hover_x_position = snapped_x
        self._update_hover_line()
        self._hover_tooltip.setHtml("<br>".join(hover_lines))
        self._position_hover_tooltip(snapped_x, mouse_point.y())
        self._hover_tooltip.show()

    def _handle_view_range_changed(self, *_: Any) -> None:
        self._update_hover_line()

    def _hide_hover_feedback(self) -> None:
        self._hover_x_position = None
        if self._hover_line is not None:
            self._hover_line.hide()
        if self._hover_tooltip is not None:
            self._hover_tooltip.hide()

    def _update_hover_line(self) -> None:
        if self._hover_line is None or self._hover_x_position is None:
            return

        y_min, y_max = self._view_box.viewRange()[1]
        self._hover_line.setData(
            x=np.array([self._hover_x_position, self._hover_x_position], dtype=float),
            y=np.array([y_min, y_max], dtype=float),
        )
        self._hover_line.show()

    def _build_hover_lines(self, target_x: float) -> tuple[list[str], float]:
        snapped = self._snap_hover_x(target_x)
        if snapped is None:
            return [], target_x

        snapped_raw_x, snapped_plot_x = snapped
        rows: list[str] = []
        for hover_data in self._hover_series_data:
            index = hover_data.nearest_index(snapped_plot_x)
            if index is None:
                continue

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
            "<span style='color:#111827; font-size:11pt; font-weight:600;'>"
            f"{self._format_hover_x_value(snapped_raw_x)}"
            "</span>"
        )
        return [header, *rows], snapped_plot_x

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

    def _format_hover_row(self, *, name: str, y_value: float, color: str) -> str:
        return (
            f"<span style='color:{color}; font-weight:600;'>&#9632;</span> "
            f"<span style='color:#1f2937; font-size:10pt;'>{name}: {self._format_hover_number(y_value)}</span>"
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

    def _position_hover_tooltip(self, x_position: float, y_position: float) -> None:
        if self._hover_tooltip is None:
            return

        x_min, x_max = self._view_box.viewRange()[0]
        y_min, y_max = self._view_box.viewRange()[1]
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

        self._hover_tooltip.setAnchor((1 if place_left else 0, 1 if place_top else 0))
        self._hover_tooltip.setPos(tooltip_x, tooltip_y)

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

        resolved = pd.Series(resolved).reset_index(drop=True)
        if len(resolved) != len(self.data):
            raise ValueError(
                f"Series length mismatch for {name}: expected {len(self.data)}, got {len(resolved)}"
            )
        return resolved

    def _coerce_x_values(self, values: Sequence[Any] | pd.Series) -> pd.Series:
        series = pd.Series(values).reset_index(drop=True)
        parsed = pd.to_datetime(series, errors="coerce")
        return pd.Series(parsed) if parsed.notna().any() else series

    def _to_plot_x(self, values: pd.Series) -> pd.Series:
        # Datetime values are plotted as row positions so the custom axis can
        # format clean date labels from the original values.
        if pd.api.types.is_datetime64_any_dtype(values):
            return pd.Series(np.arange(len(values), dtype=float))
        return pd.to_numeric(values, errors="coerce")

    def add_close_line(
        self,
        *,
        column: str = "close",
        name: str = "Close",
        color: str = "#1f77b4",
        width: float = 2.0,
    ) -> "DataChart":
        """Convenience helper for plotting a standard close-price line."""

        return self.add_line(name=name, y=column, color=color, width=width)

    def add_line(
        self,
        name: str,
        y: SeriesInput,
        *,
        x: SeriesInput | None = None,
        color: str = "#1f77b4",
        width: float = 2.0,
        dash: str = "solid",
        opacity: float = 1.0,
    ) -> "DataChart":
        """Plot a line, register it for hover feedback, and include it in auto-fit."""

        x_values = self._coerce_x_values(
            self._resolve_series(x, name=f"x-axis for {name}", default=self.data[self.x_column])
        )
        if pd.api.types.is_datetime64_any_dtype(x_values) != self._x_is_datetime:
            expected = "datetime" if self._x_is_datetime else "numeric"
            raise ValueError(f"X-axis type mismatch for {name}: chart expects {expected} values.")

        y_values = pd.to_numeric(self._resolve_series(y, name=name), errors="coerce")
        style = LineStyle(color=color, width=width, dash=dash, opacity=opacity)

        self._plot_line(name=name, x_values=x_values, y_values=y_values, style=style)
        return self

    def _plot_line(
        self,
        *,
        name: str,
        x_values: pd.Series,
        y_values: pd.Series,
        style: LineStyle,
    ) -> None:
        plot_x = self._to_plot_x(x_values)
        item = self._plot_item.plot(
            x=plot_x.to_numpy(dtype=float, copy=False),
            y=y_values.to_numpy(dtype=float, copy=False),
            name=name,
            pen=style.pen(),
            connect="finite",
            antialias=False,
        )

        self._view_box.register_series(plot_x, y_values)
        self._register_hover_series(
            name=name,
            x_values=x_values,
            plot_x=plot_x,
            y_values=y_values,
            color=style.color,
        )

        if self._series_count == 0:
            self._plot_item.autoRange()
        else:
            item.informViewBoundsChanged()

        self._series_count += 1
        self._view_box.refit_y_range()

    def _register_hover_series(
        self,
        *,
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
                name=name,
                plot_x=hover_plot_x,
                raw_x=x_values[hover_mask].reset_index(drop=True).tolist(),
                y_values=y_values[hover_mask].to_numpy(dtype=float, copy=True),
                color=color,
                is_sorted=hover_plot_x.size < 2 or bool(np.all(np.diff(hover_plot_x) >= 0)),
            )
        )

    def _ensure_window(self, *, width: int, height: int) -> QtWidgets.QMainWindow:
        if self._window is None:
            window = QtWidgets.QMainWindow()
            window.setWindowTitle(self.title)
            window.resize(width, height)
            window.setCentralWidget(self._plot_widget)
            self._window = window
        return self._window

    def show(self, *, width: int = 1280, height: int = 800) -> None:
        """Open the chart in a native window and start the Qt event loop if needed."""

        window = self._ensure_window(width=width, height=height)
        window.show()
        window.raise_()
        window.activateWindow()

        self._plot_item.autoRange()
        self._view_box.refit_y_range()

        if self._owns_app:
            self._app.exec()
