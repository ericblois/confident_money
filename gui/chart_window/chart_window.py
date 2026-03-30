from __future__ import annotations

import pandas as pd
from PySide6 import QtCore, QtGui, QtWidgets

from condition_script import (
    ScriptFeatureCall,
    collect_script_feature_calls,
    evaluate_expression,
    render_script_expression,
)
from condition_script.types import ColumnExpression, FunctionCallExpression
from gui.chart_window.chart import DataChart
from gui.chart_window.right_panel import ChartRightPanel

_SCRIPT_FEATURE_COLORS = (
    "#ef4444",
    "#f59e0b",
    "#2563eb",
    "#16a34a",
    "#7c3aed",
    "#0891b2",
    "#dc2626",
    "#ea580c",
)
_OVERLAY_FEATURE_NAMES = frozenset(
    {
        "px",
        "ma",
        "ema",
        "roll_hi",
        "roll_lo",
        "typ_px",
        "med_px",
        "vwap",
    }
)
_PANE_LABELS = {
    "main": "Price",
    "core": "Returns",
    "trends": "Trend",
    "momentum": "Momentum",
    "relative": "Relative",
    "volatility": "Volatility",
    "volume": "Volume",
    "calendar": "Calendar",
    "candles": "Candles",
    "utils": "Derived",
}
_MAIN_SOURCE_COLUMNS = frozenset({"open", "high", "low", "close", "price"})


class ChartWindow(QtWidgets.QMainWindow):
    """Display a chart and condition-script side panel in one shared window."""

    _SETTINGS_ORGANIZATION = "confident_money"
    _SETTINGS_APPLICATION = "confident_money"
    _BUY_SCRIPT_SETTINGS_KEY = "chart_window/buy_script"
    _SELL_SCRIPT_SETTINGS_KEY = "chart_window/sell_script"
    _BUY_REGION_COLOR = "#22c55e"
    _SELL_REGION_COLOR = "#ef4444"

    def __init__(
        self,
        chart: DataChart,
        *,
        initial_script: str = "",
        initial_sell_script: str = "",
        settings: QtCore.QSettings | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._chart_data = chart.data.copy()
        self._chart_config = {
            "x_column": chart.x_column,
            "title": chart.title,
            "y_label": chart.y_label,
            "show_spikes": chart.show_spikes,
        }
        self._application = chart.application
        self._owns_application = chart.owns_application
        self._settings = settings or QtCore.QSettings(
            self._SETTINGS_ORGANIZATION,
            self._SETTINGS_APPLICATION,
        )
        # Explicit initial values override the last saved drafts when callers
        # intentionally preload either editor.
        buy_script = (
            initial_script
            if initial_script != ""
            else self._settings.value(self._BUY_SCRIPT_SETTINGS_KEY, "", type=str)
        )
        sell_script = (
            initial_sell_script
            if initial_sell_script != ""
            else self._settings.value(self._SELL_SCRIPT_SETTINGS_KEY, "", type=str)
        )
        self.right_panel = ChartRightPanel(
            initial_script=buy_script,
            initial_sell_script=sell_script,
        )
        try:
            self.chart = self._build_chart_for_scripts(buy_script, sell_script)
        except Exception:
            self.chart = self._build_chart_for_scripts("", "")

        self._build_window()
        self._connect_signals()
        self._persist_script_state(
            self.right_panel.script_text(),
            self.right_panel.sell_script_text(),
        )

    def _build_window(self) -> None:
        """Create a resizable side-by-side layout for the chart and script panel."""

        self.setWindowTitle(self.chart.title)
        self.resize(1600, 920)

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self.chart.widget)
        self._splitter.addWidget(self.right_panel)
        self._splitter.setStretchFactor(0, 5)
        self._splitter.setStretchFactor(1, 2)
        self._splitter.setSizes([1180, 380])

        self.setCentralWidget(self._splitter)

    def _connect_signals(self) -> None:
        self.right_panel.run_requested.connect(self.run_condition_script)
        self.right_panel.script_changed.connect(self._persist_script_state)

    def _persist_script_state(self, buy_script: str, sell_script: str) -> None:
        self._settings.setValue(self._BUY_SCRIPT_SETTINGS_KEY, buy_script)
        self._settings.setValue(self._SELL_SCRIPT_SETTINGS_KEY, sell_script)

    def _build_chart_for_scripts(
        self,
        buy_script: str,
        sell_script: str,
    ) -> DataChart:
        chart = DataChart(self._chart_data, **self._chart_config)
        chart.add_close_line()

        feature_calls = self._collect_chart_feature_calls(buy_script, sell_script)
        if not feature_calls:
            return chart

        feature_calls_by_rendered = {
            feature_call.rendered_call: feature_call
            for feature_call in feature_calls
        }
        resolved_panes: dict[str, str] = {}
        pane_names: list[str] = []
        for feature_call in feature_calls:
            pane_name = self._resolve_feature_pane_name(
                feature_call,
                feature_calls_by_rendered,
                resolved_panes,
            )
            if pane_name != "main" and pane_name not in pane_names:
                pane_names.append(pane_name)

        for pane_name in pane_names:
            chart.add_pane(
                pane_name,
                y_label=_PANE_LABELS.get(pane_name, pane_name.replace("_", " ").title()),
                height_ratio=1,
            )

        pane_line_counts: dict[str, int] = {}
        for feature_call in feature_calls:
            pane_name = resolved_panes[feature_call.rendered_call]
            values = evaluate_expression(chart.data, feature_call.expression)
            if not isinstance(values, pd.Series):
                raise ValueError(
                    f"Feature '{feature_call.rendered_call}' did not return a series."
                )

            line_index = pane_line_counts.get(pane_name, 0)
            chart.add_line(
                name=feature_call.rendered_call,
                y=values,
                pane=pane_name,
                color=_SCRIPT_FEATURE_COLORS[
                    line_index % len(_SCRIPT_FEATURE_COLORS)
                ],
                width=1.5,
            )
            pane_line_counts[pane_name] = line_index + 1

        return chart

    def _collect_chart_feature_calls(
        self,
        buy_script: str,
        sell_script: str,
    ) -> tuple[ScriptFeatureCall, ...]:
        collected_calls: list[ScriptFeatureCall] = []
        seen_rendered_calls: set[str] = set()

        for label, script in (("Buy", buy_script.strip()), ("Sell", sell_script.strip())):
            if not script:
                continue

            try:
                feature_calls = collect_script_feature_calls(script)
            except Exception as exc:
                raise ValueError(f"{label} condition error: {exc}") from exc

            for feature_call in feature_calls:
                if feature_call.rendered_call in seen_rendered_calls:
                    continue
                seen_rendered_calls.add(feature_call.rendered_call)
                collected_calls.append(feature_call)

        return tuple(collected_calls)

    def _resolve_feature_pane_name(
        self,
        feature_call: ScriptFeatureCall,
        feature_calls_by_rendered: dict[str, ScriptFeatureCall],
        resolved_panes: dict[str, str],
    ) -> str:
        cached_pane_name = resolved_panes.get(feature_call.rendered_call)
        if cached_pane_name is not None:
            return cached_pane_name

        if feature_call.feature_name in _OVERLAY_FEATURE_NAMES:
            pane_name = self._resolve_overlay_source_pane_name(
                feature_call,
                feature_calls_by_rendered,
                resolved_panes,
            )
        elif feature_call.feature_name in {"ret", "log_ret"}:
            pane_name = "core"
        else:
            pane_name = feature_call.feature_category

        resolved_panes[feature_call.rendered_call] = pane_name
        return pane_name

    def _resolve_overlay_source_pane_name(
        self,
        feature_call: ScriptFeatureCall,
        feature_calls_by_rendered: dict[str, ScriptFeatureCall],
        resolved_panes: dict[str, str],
    ) -> str:
        for parameter_name in ("source", "price", "close", "high", "low", "open"):
            if parameter_name not in feature_call.parameter_names:
                continue

            parameter_index = feature_call.parameter_names.index(parameter_name)
            if parameter_index >= len(feature_call.expression.arguments):
                continue

            argument = feature_call.expression.arguments[parameter_index]
            if isinstance(argument, ColumnExpression):
                return self._resolve_column_pane_name(argument.name)

            if isinstance(argument, FunctionCallExpression):
                nested_call = feature_calls_by_rendered.get(
                    render_script_expression(argument)
                )
                if nested_call is not None:
                    return self._resolve_feature_pane_name(
                        nested_call,
                        feature_calls_by_rendered,
                        resolved_panes,
                    )

        return "main"

    def _resolve_column_pane_name(self, column_name: str) -> str:
        normalized_name = column_name.strip().lower()
        if normalized_name in _MAIN_SOURCE_COLUMNS:
            return "main"
        if (
            normalized_name == "volume"
            or normalized_name.startswith("volume_")
            or normalized_name.endswith("_volume")
        ):
            return "volume"
        return "main"

    def _replace_chart(self, chart: DataChart) -> None:
        if not hasattr(self, "_splitter"):
            self.chart = chart
            return

        previous_widget = self.chart.widget
        splitter_sizes = self._splitter.sizes()
        self.chart = chart
        self._splitter.insertWidget(0, self.chart.widget)
        previous_widget.setParent(None)
        previous_widget.deleteLater()
        if splitter_sizes:
            self._splitter.setSizes(splitter_sizes)
        self.setWindowTitle(self.chart.title)

    def run_condition_script(self, buy_script: str, sell_script: str = "") -> None:
        """Evaluate the buy and sell scripts and reflect the matching regions on the chart."""

        buy_script = buy_script.strip()
        sell_script = sell_script.strip()
        try:
            next_chart = self._build_chart_for_scripts(buy_script, sell_script)
        except Exception as exc:
            self.chart.clear_condition_regions()
            self.right_panel.show_error(str(exc))
            return

        if not buy_script and not sell_script:
            self._replace_chart(next_chart)
            self.chart.clear_condition_regions()
            self.right_panel.show_error("Enter a buy or sell condition before running.")
            return

        conditions: list[tuple[str, str, object]] = []
        for label, script, color in (
            ("Buy", buy_script, self._BUY_REGION_COLOR),
            ("Sell", sell_script, self._SELL_REGION_COLOR),
        ):
            if not script:
                continue

            try:
                condition = next_chart.evaluate_condition_script(script)
            except Exception as exc:
                self.chart.clear_condition_regions()
                self.right_panel.show_error(f"{label} condition error: {exc}")
                return

            conditions.append((label, color, condition))

        self._replace_chart(next_chart)
        self.chart.clear_condition_regions()
        summary_parts: list[str] = []
        total_highlighted_ranges = 0

        for label, color, condition in conditions:
            matched_timestamps = int(condition.fillna(False).sum())
            highlighted_ranges = self.chart.set_condition_regions(
                condition,
                color=color,
                clear_existing=False,
            )
            total_highlighted_ranges += highlighted_ranges

            if highlighted_ranges == 0:
                summary_parts.append(f"{label.lower()}: no matches")
                continue

            timestamp_label = "timestamp" if matched_timestamps == 1 else "timestamps"
            range_label = "range" if highlighted_ranges == 1 else "ranges"
            summary_parts.append(
                f"{label.lower()}: {matched_timestamps} {timestamp_label} across {highlighted_ranges} {range_label}"
            )

        self.chart.refresh_view()

        if total_highlighted_ranges == 0:
            self.right_panel.show_hint("No matching timestamps were found for the current scripts.")
            return

        self.right_panel.show_success("Results: " + "; ".join(summary_parts) + ".")

    def show(self) -> None:
        """Show the combined window and start the Qt event loop when needed."""

        super().show()
        self.raise_()
        self.activateWindow()
        self.chart.refresh_view(auto_range=True)
        if self._owns_application:
            self._application.exec()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._persist_script_state(
            self.right_panel.script_text(),
            self.right_panel.sell_script_text(),
        )
        self._settings.sync()
        super().closeEvent(event)
