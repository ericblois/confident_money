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
from gui.chart_window.left_panel import ChartLeftPanel
from gui.chart_window.right_panel import ChartRightPanel
from gui.components.text_btn import TextBtn, TextBtnStyle

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
_CHART_TITLE_STYLE = """
    QFrame#chartContainer {
        background: #24211f;
    }
    QLabel#chartHeaderTitle {
        color: #f8fafc;
        font-size: 16px;
        font-weight: 600;
    }
"""
_CHART_OPTIONS_BUTTON_STYLE = TextBtnStyle(
    background="#1f2937",
    hover_background="#334155",
    pressed_background="#0f172a",
    text_color="#f8fafc",
    border_color="#475569",
    hover_border_color="#64748b",
    pressed_border_color="#64748b",
    border_radius=6,
    min_height=34,
    horizontal_padding=12,
    font_size=12,
    font_weight=600,
)


class ChartWindow(QtWidgets.QMainWindow):
    """Display a chart and condition-script side panel in one shared window."""

    _SETTINGS_ORGANIZATION = "confident_money"
    _SETTINGS_APPLICATION = "confident_money"
    _BUY_SCRIPT_SETTINGS_KEY = "chart_window/buy_script"
    _SELL_SCRIPT_SETTINGS_KEY = "chart_window/sell_script"
    _BUY_REGION_COLOR = "#22c55e"
    _SELL_REGION_COLOR = "#ef4444"
    _DEFAULT_LEFT_PANEL_WIDTH = 320

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
        self.left_panel = ChartLeftPanel(self)
        try:
            self.chart = self._build_chart_for_scripts(buy_script, sell_script)
        except Exception:
            self.chart = self._build_chart_for_scripts("", "")
        self.chart.set_title_visible(False)
        self._left_panel_width = self._DEFAULT_LEFT_PANEL_WIDTH

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
        self._build_chart_container()

        self._splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        self._splitter.setChildrenCollapsible(False)
        self._splitter.addWidget(self.left_panel)
        self._splitter.addWidget(self._chart_container)
        self._splitter.addWidget(self.right_panel)
        self._splitter.setStretchFactor(0, 0)
        self._splitter.setStretchFactor(1, 5)
        self._splitter.setStretchFactor(2, 2)
        self.left_panel.hide()
        self._splitter.setSizes([0, 1180, 380])

        self.setCentralWidget(self._splitter)

    def _connect_signals(self) -> None:
        self.right_panel.run_requested.connect(self.run_condition_script)
        self.right_panel.script_changed.connect(self._persist_script_state)
        self._chart_options_button.clicked.connect(self._show_left_panel)
        self.left_panel.close_requested.connect(self._hide_left_panel)

    def _build_chart_container(self) -> None:
        self._chart_container = QtWidgets.QFrame(self)
        self._chart_container.setObjectName("chartContainer")
        self._chart_container.setStyleSheet(_CHART_TITLE_STYLE)

        self._chart_options_slot = QtWidgets.QWidget(self._chart_container)
        self._chart_options_slot.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._chart_options_button = TextBtn(
            "Chart Options",
            style=_CHART_OPTIONS_BUTTON_STYLE,
            parent=self._chart_options_slot,
        )
        self._chart_options_button.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Maximum,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        chart_options_slot_layout = QtWidgets.QHBoxLayout(self._chart_options_slot)
        chart_options_slot_layout.setContentsMargins(0, 0, 0, 0)
        chart_options_slot_layout.addWidget(
            self._chart_options_button,
            0,
            QtCore.Qt.AlignmentFlag.AlignLeft,
        )

        self._chart_title_label = QtWidgets.QLabel(self.chart.title, self._chart_container)
        self._chart_title_label.setObjectName("chartHeaderTitle")
        self._chart_title_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self._chart_header_spacer = QtWidgets.QWidget(self._chart_container)
        self._chart_header_spacer.setSizePolicy(
            QtWidgets.QSizePolicy.Policy.Fixed,
            QtWidgets.QSizePolicy.Policy.Fixed,
        )
        self._sync_chart_header_balance()

        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setContentsMargins(18, 14, 18, 0)
        header_layout.setSpacing(12)
        header_layout.addWidget(self._chart_options_slot, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
        header_layout.addWidget(self._chart_title_label, 1)
        header_layout.addWidget(self._chart_header_spacer)

        self._chart_layout = QtWidgets.QVBoxLayout(self._chart_container)
        self._chart_layout.setContentsMargins(0, 0, 0, 0)
        self._chart_layout.setSpacing(10)
        self._chart_layout.addLayout(header_layout)
        self._chart_layout.addWidget(self.chart.widget, 1)

    def _sync_chart_header_balance(self) -> None:
        """Keep equal header widths on both sides of the centered title."""

        button_width = self._chart_options_button.sizeHint().width()
        self._chart_options_slot.setFixedWidth(button_width)
        self._chart_header_spacer.setFixedWidth(button_width)

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
        chart.set_title_visible(False)
        if not hasattr(self, "_chart_layout"):
            self.chart = chart
            return

        previous_widget = self.chart.widget
        self.chart = chart
        self._chart_layout.removeWidget(previous_widget)
        self._chart_layout.insertWidget(1, self.chart.widget, 1)
        previous_widget.setParent(None)
        previous_widget.deleteLater()
        self._chart_title_label.setText(self.chart.title)
        self.setWindowTitle(self.chart.title)

    def _show_left_panel(self) -> None:
        if not self.left_panel.isHidden():
            return

        self.left_panel.show()
        self._chart_options_button.hide()
        self._apply_splitter_sizes(show_left_panel=True)

    def _hide_left_panel(self) -> None:
        if self.left_panel.isHidden():
            return

        splitter_sizes = self._splitter.sizes()
        if splitter_sizes and splitter_sizes[0] > 0:
            self._left_panel_width = splitter_sizes[0]

        self.left_panel.hide()
        self._chart_options_button.show()
        self._apply_splitter_sizes(show_left_panel=False)

    def _apply_splitter_sizes(self, *, show_left_panel: bool) -> None:
        splitter_sizes = self._splitter.sizes()
        total_width = sum(splitter_sizes) or max(self.width(), 1)
        right_panel_width = splitter_sizes[2] if len(splitter_sizes) >= 3 else 380

        if show_left_panel:
            left_panel_width = max(self.left_panel.minimumWidth(), self._left_panel_width)
            chart_width = max(1, total_width - left_panel_width - right_panel_width)
            self._splitter.setSizes([left_panel_width, chart_width, right_panel_width])
            return

        chart_width = max(1, total_width - right_panel_width)
        self._splitter.setSizes([0, chart_width, right_panel_width])

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
