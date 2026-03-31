from __future__ import annotations

import os
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


try:
    from PySide6 import QtCore, QtWidgets
    from gui.chart_window.chart import DataChart, _AutoFitViewBox, build_condition_region_ranges
    from gui.chart_window.chart_window import ChartWindow
except ImportError:  # pragma: no cover - depends on optional GUI dependencies
    QtCore = None
    QtWidgets = None
    DataChart = None
    ChartWindow = None
    _AutoFitViewBox = None
    build_condition_region_ranges = None


class _FakeWheelEvent:
    def __init__(
        self,
        *,
        delta: int = 0,
        pixel_delta: object | None = None,
        orientation: object | None = None,
    ) -> None:
        self._delta = delta
        self._pixel_delta = pixel_delta
        self._orientation = orientation
        self.accepted = False
        self.ignored = False

    def delta(self) -> int:
        return self._delta

    def pixelDelta(self) -> object | None:
        return self._pixel_delta

    def orientation(self) -> object | None:
        return self._orientation

    def accept(self) -> None:
        self.accepted = True

    def ignore(self) -> None:
        self.ignored = True


@unittest.skipIf(
    build_condition_region_ranges is None,
    "PySide6/pyqtgraph are not available in this environment.",
)
class ConditionRegionRangeTests(unittest.TestCase):
    def test_build_condition_region_ranges_groups_adjacent_rows(self) -> None:
        regions = build_condition_region_ranges(
            [False, True, True, False, True],
            [0.0, 1.0, 2.0, 3.0, 4.0],
        )

        self.assertEqual(regions, [(0.5, 2.5), (3.5, 4.5)])

    def test_build_condition_region_ranges_respects_irregular_spacing(self) -> None:
        regions = build_condition_region_ranges(
            [True, True, False, True],
            [10.0, 20.0, 40.0, 80.0],
        )

        self.assertEqual(regions, [(5.0, 30.0), (60.0, 100.0)])

    def test_build_condition_region_ranges_validates_input_lengths(self) -> None:
        with self.assertRaises(ValueError):
            build_condition_region_ranges([True, False], [1.0])


@unittest.skipIf(
    _AutoFitViewBox is None,
    "PySide6/pyqtgraph are not available in this environment.",
)
class AutoFitViewBoxWheelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_horizontal_pixel_scroll_pans_left_when_scrolling_right(self) -> None:
        view_box = _AutoFitViewBox()
        view_box.setGeometry(QtCore.QRectF(0.0, 0.0, 400.0, 200.0))
        view_box.setRange(xRange=(0.0, 100.0), yRange=(0.0, 1.0), padding=0.0)

        event = _FakeWheelEvent(pixel_delta=QtCore.QPoint(80, 0))
        view_box.wheelEvent(event)

        x_min, x_max = view_box.viewRange()[0]
        self.assertAlmostEqual(x_min, -20.0, places=1)
        self.assertAlmostEqual(x_max - x_min, 100.0, places=3)
        self.assertTrue(event.accepted)
        self.assertFalse(event.ignored)

    def test_horizontal_scroll_on_linked_pane_moves_shared_x_range(self) -> None:
        lead_view = _AutoFitViewBox()
        linked_view = _AutoFitViewBox()
        lead_view.setGeometry(QtCore.QRectF(0.0, 0.0, 400.0, 200.0))
        linked_view.setGeometry(QtCore.QRectF(0.0, 0.0, 400.0, 200.0))
        lead_view.setRange(xRange=(0.0, 100.0), yRange=(0.0, 1.0), padding=0.0)
        linked_view.setRange(xRange=(0.0, 100.0), yRange=(0.0, 1.0), padding=0.0)
        linked_view.setXLink(lead_view)

        event = _FakeWheelEvent(
            delta=120,
            orientation=QtCore.Qt.Orientation.Horizontal,
        )
        linked_view.wheelEvent(event)

        lead_x_min, lead_x_max = lead_view.viewRange()[0]
        self.assertAlmostEqual(lead_x_min, -12.0)
        self.assertAlmostEqual(lead_x_max, 88.0)
        self.assertTrue(event.accepted)

    def test_refit_y_range_uses_only_visible_finite_points(self) -> None:
        view_box = _AutoFitViewBox()
        view_box.setGeometry(QtCore.QRectF(0.0, 0.0, 400.0, 200.0))
        view_box.register_series(
            pd.Series([0.0, 1.0, 2.0, 3.0, 4.0]),
            pd.Series([float("nan"), 10.0, 20.0, float("nan"), 5.0]),
        )
        view_box.setRange(xRange=(0.5, 3.5), yRange=(0.0, 1.0), padding=0.0)
        view_box.refit_y_range()

        y_min, y_max = view_box.viewRange()[1]
        self.assertAlmostEqual(y_min, 10.0 - (10.0 / 18.0), places=3)
        self.assertAlmostEqual(y_max, 20.0 + (10.0 / 18.0), places=3)


@unittest.skipIf(
    DataChart is None,
    "PySide6/pyqtgraph are not available in this environment.",
)
class DataChartAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_chart_preserves_row_order_when_coercing_x_column(self) -> None:
        data = pd.DataFrame(
            {
                "date": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "close": [10.0, 20.0, 30.0],
            },
            index=[2, 0, 1],
        )
        chart = DataChart(data, show_spikes=False)

        pd.testing.assert_series_equal(
            chart.data["date"],
            pd.Series(pd.to_datetime(data["date"]), index=data.index, name="date"),
        )
        pd.testing.assert_series_equal(chart.data["close"], data["close"])

    def test_add_line_aligns_series_to_chart_index(self) -> None:
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3, freq="D"),
                "close": [10.0, 20.0, 30.0],
            },
            index=[2, 0, 1],
        )
        chart = DataChart(data, show_spikes=False)

        chart.add_line(
            name="Aligned Series",
            y=pd.Series([100.0, 200.0, 300.0], index=[0, 1, 2]),
        )

        self.assertEqual(
            chart._hover_series_data[-1].y_values.tolist(),
            [300.0, 100.0, 200.0],
        )

    def test_set_condition_regions_aligns_series_to_chart_index(self) -> None:
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3, freq="D"),
                "close": [10.0, 20.0, 30.0],
            },
            index=[2, 0, 1],
        )
        chart = DataChart(data, show_spikes=False)

        highlighted_ranges = chart.set_condition_regions(
            pd.Series([True, False, False], index=[0, 1, 2]),
        )

        self.assertEqual(highlighted_ranges, 1)
        x_min, x_max = chart._condition_region_items[0].item.getRegion()
        self.assertAlmostEqual(x_min, 0.5)
        self.assertAlmostEqual(x_max, 1.5)


@unittest.skipIf(
    ChartWindow is None,
    "PySide6/pyqtgraph are not available in this environment.",
)
class ChartWindowPersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_chart_window_restores_and_saves_script_drafts(self) -> None:
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=3, freq="D"),
                "close": [100.0, 101.0, 102.0],
            }
        )

        with TemporaryDirectory() as temp_dir:
            settings_path = Path(temp_dir) / "chart_window.ini"
            settings = QtCore.QSettings(
                str(settings_path),
                QtCore.QSettings.Format.IniFormat,
            )
            settings.setValue("chart_window/buy_script", "close > 100")
            settings.setValue("chart_window/sell_script", "close < 100")
            settings.sync()

            chart = DataChart(data, show_spikes=False)
            window = ChartWindow(chart, settings=settings)
            self.addCleanup(window.close)

            self.assertEqual(window.right_panel.script_text(), "close > 100")
            self.assertEqual(window.right_panel.sell_script_text(), "close < 100")

            window.right_panel.set_script_text("close >= 101")
            window.right_panel.set_sell_script_text("close <= 99")
            settings.sync()

            saved_settings = QtCore.QSettings(
                str(settings_path),
                QtCore.QSettings.Format.IniFormat,
            )
            self.assertEqual(
                saved_settings.value("chart_window/buy_script", "", type=str),
                "close >= 101",
            )
            self.assertEqual(
                saved_settings.value("chart_window/sell_script", "", type=str),
                "close <= 99",
            )

    def test_chart_window_plots_distinct_parameterized_features_once_each(self) -> None:
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=8, freq="D"),
                "close": [100.0, 101.0, 102.0, 103.0, 102.0, 101.0, 104.0, 105.0],
                "volume": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
            }
        )

        with TemporaryDirectory() as temp_dir:
            settings = QtCore.QSettings(
                str(Path(temp_dir) / "chart_window.ini"),
                QtCore.QSettings.Format.IniFormat,
            )
            chart = DataChart(data, show_spikes=False)
            window = ChartWindow(
                chart,
                initial_script="vwap(3) > vwap(5)",
                initial_sell_script="vwap(3) < close",
                settings=settings,
            )
            self.addCleanup(window.close)

            plotted_names = [hover_data.name for hover_data in window.chart._hover_series_data]
            self.assertEqual(plotted_names.count("vwap(3)"), 1)
            self.assertEqual(plotted_names.count("vwap(5)"), 1)
            self.assertEqual(
                {
                    hover_data.pane_name
                    for hover_data in window.chart._hover_series_data
                    if hover_data.name.startswith("vwap(")
                },
                {"main"},
            )

    def test_chart_window_uses_source_pane_for_nested_overlay_features(self) -> None:
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=8, freq="D"),
                "close": [100.0, 101.0, 102.0, 103.0, 102.0, 101.0, 104.0, 105.0],
            }
        )

        with TemporaryDirectory() as temp_dir:
            settings = QtCore.QSettings(
                str(Path(temp_dir) / "chart_window.ini"),
                QtCore.QSettings.Format.IniFormat,
            )
            chart = DataChart(data, show_spikes=False)
            window = ChartWindow(
                chart,
                initial_script="mv_avg(vlt(3), 2) > vlt(3)",
                settings=settings,
            )
            self.addCleanup(window.close)

            plotted_by_pane = {
                (hover_data.pane_name, hover_data.name)
                for hover_data in window.chart._hover_series_data
            }
            self.assertIn(("volatility", "vlt(3)"), plotted_by_pane)
            self.assertIn(("volatility", "mv_avg(vlt(3), 2)"), plotted_by_pane)

    def test_chart_window_show_uses_original_application_owner(self) -> None:
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=8, freq="D"),
                "close": [100.0, 101.0, 102.0, 103.0, 102.0, 101.0, 104.0, 105.0],
                "volume": [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0],
            }
        )

        with TemporaryDirectory() as temp_dir:
            settings = QtCore.QSettings(
                str(Path(temp_dir) / "chart_window.ini"),
                QtCore.QSettings.Format.IniFormat,
            )
            chart = DataChart(data, show_spikes=False)
            window = ChartWindow(
                chart,
                initial_script="vwap(3) > close",
                settings=settings,
            )
            self.addCleanup(window.close)

            class _FakeApp:
                def __init__(self) -> None:
                    self.exec_called = False

                def exec(self) -> int:
                    self.exec_called = True
                    return 0

            fake_app = _FakeApp()
            window._application = fake_app
            window._owns_application = True

            with patch.object(window.chart, "refresh_view") as refresh_view:
                window.show()

            refresh_view.assert_called_once_with(auto_range=True)
            self.assertTrue(fake_app.exec_called)

    def test_chart_window_toggles_chart_options_panel(self) -> None:
        data = pd.DataFrame(
            {
                "date": pd.date_range("2024-01-01", periods=4, freq="D"),
                "close": [100.0, 101.0, 102.0, 103.0],
            }
        )

        with TemporaryDirectory() as temp_dir:
            settings = QtCore.QSettings(
                str(Path(temp_dir) / "chart_window.ini"),
                QtCore.QSettings.Format.IniFormat,
            )
            chart = DataChart(data, title="Toggle Test Chart", show_spikes=False)
            window = ChartWindow(chart, settings=settings)
            self.addCleanup(window.close)

            self.assertEqual(window._chart_title_label.text(), "Toggle Test Chart")
            self.assertTrue(window.left_panel.isHidden())
            self.assertFalse(window._chart_options_button.isHidden())

            window._show_left_panel()

            self.assertFalse(window.left_panel.isHidden())
            self.assertTrue(window._chart_options_button.isHidden())

            window._hide_left_panel()

            self.assertTrue(window.left_panel.isHidden())
            self.assertFalse(window._chart_options_button.isHidden())


if __name__ == "__main__":
    unittest.main()
