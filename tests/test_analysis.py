import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analyzer import analyze_series, detect_trend
from validator import validate_series

EXAMPLE = pd.Series({2019: 8.2, 2020: 9.1, 2021: 8.4, 2022: 7.9, 2023: 7.5})


def test_analyze_example_series():
    result = analyze_series(EXAMPLE)
    assert result["status"] == "ok"
    assert result["net_direction"] == "falling"
    assert result["trend"] == "falling"
    assert result["absolute_change"] == -0.7
    assert result["percentage_change"] == -8.54
    assert result["change_unit"] == "percentage points"
    assert result["first_year"] == 2019 and result["first_value"] == 8.2
    assert result["last_year"] == 2023 and result["last_value"] == 7.5
    assert result["peak"] == {"year": 2020, "value": 9.1}
    assert result["trough"] == {"year": 2023, "value": 7.5}
    assert result["n_points"] == 5


def test_net_direction_stable_within_band():
    s = pd.Series({2020: 5.0, 2021: 5.05})
    assert analyze_series(s)["net_direction"] == "stable"


def test_unsorted_index_is_handled():
    shuffled = pd.Series({2023: 7.5, 2019: 8.2, 2021: 8.4, 2020: 9.1, 2022: 7.9})
    result = analyze_series(shuffled)
    assert result["first_year"] == 2019 and result["first_value"] == 8.2
    assert result["last_year"] == 2023 and result["last_value"] == 7.5


def test_percentage_change_zero_first_value_is_none():
    assert analyze_series(pd.Series({2020: 0.0, 2021: 2.0}))["percentage_change"] is None


def test_percentage_change_negative_first_value_is_not_inverted():
    # -2 -> +1 is an increase; dividing by -2 directly would report -150.
    result = analyze_series(pd.Series({2020: -2.0, 2021: 1.0}))
    assert result["absolute_change"] == 3.0
    assert result["percentage_change"] == 150.0
    assert result["net_direction"] == "rising"


def test_net_direction_and_trend_can_disagree():
    # rises sharply, then drops to just below the start
    s = pd.Series({2017: 5.0, 2018: 8.0, 2019: 9.0, 2020: 9.0, 2021: 4.8})
    result = analyze_series(s)
    assert result["net_direction"] == "falling"
    assert result["trend"] == "rising"


def test_trend_uses_real_years_not_row_positions():
    # Same +1.0 change: over 1 year the slope is 1.0/yr (rising),
    # over 40 years it is 0.025/yr, under the 0.05 threshold (stable).
    fast = pd.Series({2000: 0.0, 2001: 1.0})
    slow = pd.Series({2000: 0.0, 2040: 1.0})
    assert detect_trend(fast) == "rising"
    assert detect_trend(slow) == "stable"


def test_analyze_needs_two_points():
    assert analyze_series(pd.Series({2020: 1.0})) == {"status": "insufficient_data", "n_points": 1}
    assert analyze_series(pd.Series(dtype=float)) == {"status": "insufficient_data", "n_points": 0}


def test_validate_ok_series():
    v = validate_series(EXAMPLE, 2019, 2023)
    assert v["ok"] and v["missing_years"] == [] and v["errors"] == [] and v["warnings"] == []


def test_validate_empty_series():
    v = validate_series(pd.Series(dtype=float), 2015, 2017)
    assert not v["ok"]
    assert v["missing_years"] == [2015, 2016, 2017]
    assert v["errors"]


def test_validate_single_point_is_blocking():
    v = validate_series(pd.Series({2020: 3.0}), 2020, 2020)
    assert not v["ok"] and v["errors"]


def test_validate_warns_on_stale_latest_year_and_gaps():
    s = pd.Series({2015: 1.0, 2016: 2.0, 2018: 3.0})
    v = validate_series(s, 2015, 2020)
    assert v["ok"]
    assert v["missing_years"] == [2017, 2019, 2020]
    assert any("Latest available year is 2018" in w for w in v["warnings"])
    assert any("Gaps" in w and "2017" in w for w in v["warnings"])
