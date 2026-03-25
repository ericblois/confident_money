from __future__ import annotations

import unittest


try:
    from PySide6 import QtCore, QtWidgets
    from gui.chart_window.chart import _AutoFitViewBox, build_condition_region_ranges
except ImportError:  # pragma: no cover - depends on optional GUI dependencies
    QtCore = None
    QtWidgets = None
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


if __name__ == "__main__":
    unittest.main()
