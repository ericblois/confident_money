from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets

from gui.chart_window.chart import DataChart
from gui.chart_window.right_panel import ChartRightPanel


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
        self.chart = chart
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

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self.chart.widget)
        splitter.addWidget(self.right_panel)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([1180, 380])

        self.setCentralWidget(splitter)

    def _connect_signals(self) -> None:
        self.right_panel.run_requested.connect(self.run_condition_script)
        self.right_panel.script_changed.connect(self._persist_script_state)

    def _persist_script_state(self, buy_script: str, sell_script: str) -> None:
        self._settings.setValue(self._BUY_SCRIPT_SETTINGS_KEY, buy_script)
        self._settings.setValue(self._SELL_SCRIPT_SETTINGS_KEY, sell_script)

    def run_condition_script(self, buy_script: str, sell_script: str = "") -> None:
        """Evaluate the buy and sell scripts and reflect the matching regions on the chart."""

        buy_script = buy_script.strip()
        sell_script = sell_script.strip()
        if not buy_script and not sell_script:
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
                condition = self.chart.evaluate_condition_script(script)
            except Exception as exc:
                self.chart.clear_condition_regions()
                self.right_panel.show_error(f"{label} condition error: {exc}")
                return

            conditions.append((label, color, condition))

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
        self.chart.run_application()

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self._persist_script_state(
            self.right_panel.script_text(),
            self.right_panel.sell_script_text(),
        )
        self._settings.sync()
        super().closeEvent(event)
