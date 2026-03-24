from __future__ import annotations

from PySide6 import QtCore, QtWidgets

from condition_script import evaluate_condition
from gui.chart import DataChart
from gui.script_box import ConditionScriptBox


class ChartWindow(QtWidgets.QMainWindow):
    """Display a chart and condition-script side panel in one shared window."""

    def __init__(
        self,
        chart: DataChart,
        *,
        initial_script: str = "",
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.chart = chart
        self.script_box = ConditionScriptBox(initial_script=initial_script)

        self._build_window()
        self._connect_signals()

    def _build_window(self) -> None:
        """Create a resizable side-by-side layout for the chart and script panel."""

        self.setWindowTitle(self.chart.title)
        self.resize(1600, 920)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self.chart.widget)
        splitter.addWidget(self.script_box)
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([1180, 380])

        self.setCentralWidget(splitter)

    def _connect_signals(self) -> None:
        self.script_box.run_requested.connect(self.run_condition_script)

    def run_condition_script(self, script: str) -> None:
        """Evaluate a condition script and reflect the matching regions on the chart."""

        if not script.strip():
            self.chart.clear_condition_regions()
            self.script_box.show_error("Condition scripts cannot be empty.")
            return

        try:
            condition = evaluate_condition(self.chart.data, script)
        except Exception as exc:
            self.chart.clear_condition_regions()
            self.script_box.show_error(str(exc))
            return

        matched_timestamps = int(condition.fillna(False).sum())
        highlighted_ranges = self.chart.set_condition_regions(condition)
        self.chart.refresh_view()

        if highlighted_ranges == 0:
            self.script_box.show_hint("No matching timestamps were found for the current script.")
            return

        timestamp_label = "timestamp" if matched_timestamps == 1 else "timestamps"
        range_label = "range" if highlighted_ranges == 1 else "ranges"
        self.script_box.show_success(
            f"Matched {matched_timestamps} {timestamp_label} across {highlighted_ranges} highlighted {range_label}."
        )

    def show(self) -> None:
        """Show the combined window and start the Qt event loop when needed."""

        super().show()
        self.raise_()
        self.activateWindow()
        self.chart.refresh_view(auto_range=True)
        self.chart.run_application()
