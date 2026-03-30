from __future__ import annotations

from .day_of_month import FEATURE_INFO as DAY_OF_MONTH_FEATURE_INFO, add_day_of_month, calc_day_of_month
from .day_of_week import FEATURE_INFO as DAY_OF_WEEK_FEATURE_INFO, add_day_of_week, calc_day_of_week
from .day_of_year import FEATURE_INFO as DAY_OF_YEAR_FEATURE_INFO, add_day_of_year, calc_day_of_year
from .hour import FEATURE_INFO as HOUR_FEATURE_INFO, add_hour, calc_hour
from .is_holiday_adjacent import (
    FEATURE_INFO as IS_HOLIDAY_ADJACENT_FEATURE_INFO,
    add_is_holiday_adjacent,
    calc_is_holiday_adjacent,
)
from .is_month_end import FEATURE_INFO as IS_MONTH_END_FEATURE_INFO, add_is_month_end, calc_is_month_end
from .is_month_start import (
    FEATURE_INFO as IS_MONTH_START_FEATURE_INFO,
    add_is_month_start,
    calc_is_month_start,
)
from .month_of_year import FEATURE_INFO as MONTH_OF_YEAR_FEATURE_INFO, add_month_of_year, calc_month_of_year
from .quarter import FEATURE_INFO as QUARTER_FEATURE_INFO, add_quarter, calc_quarter
from .week_of_year import FEATURE_INFO as WEEK_OF_YEAR_FEATURE_INFO, add_week_of_year, calc_week_of_year


FEATURE_INFOS = (
    DAY_OF_WEEK_FEATURE_INFO,
    DAY_OF_MONTH_FEATURE_INFO,
    DAY_OF_YEAR_FEATURE_INFO,
    WEEK_OF_YEAR_FEATURE_INFO,
    MONTH_OF_YEAR_FEATURE_INFO,
    QUARTER_FEATURE_INFO,
    HOUR_FEATURE_INFO,
    IS_MONTH_START_FEATURE_INFO,
    IS_MONTH_END_FEATURE_INFO,
    IS_HOLIDAY_ADJACENT_FEATURE_INFO,
)


__all__ = [
    "FEATURE_INFOS",
    "add_day_of_month",
    "add_day_of_week",
    "add_day_of_year",
    "add_hour",
    "add_is_holiday_adjacent",
    "add_is_month_end",
    "add_is_month_start",
    "add_month_of_year",
    "add_quarter",
    "add_week_of_year",
    "calc_day_of_month",
    "calc_day_of_week",
    "calc_day_of_year",
    "calc_hour",
    "calc_is_holiday_adjacent",
    "calc_is_month_end",
    "calc_is_month_start",
    "calc_month_of_year",
    "calc_quarter",
    "calc_week_of_year",
]
