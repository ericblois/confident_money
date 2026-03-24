from __future__ import annotations

import unittest


try:
    from gui.chart import build_condition_region_ranges
except ImportError:  # pragma: no cover - depends on optional GUI dependencies
    build_condition_region_ranges = None


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


if __name__ == "__main__":
    unittest.main()
