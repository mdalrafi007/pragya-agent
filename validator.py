"""validator.py - deterministic sanity checks on a fetched time series.

Runs after data retrieval and before analysis. It never modifies the data;
it only reports whether the series is usable and what is wrong with it.
"""

import numpy as np
import pandas as pd

MIN_POINTS = 2


def validate_series(series: pd.Series, start_year: int, end_year: int, min_points: int = MIN_POINTS) -> dict:
    """Check a year-indexed series against the requested year range.

    Returns a dict:
      ok             - True if the series can be analyzed
      n_points       - number of usable observations
      first_year     - earliest year with data (None if empty)
      last_year      - latest year with data (None if empty)
      missing_years  - requested years with no data
      errors         - blocking problems (analysis is skipped when non-empty)
      warnings       - non-blocking problems the reader should know about
    """
    result = {
        "ok": False,
        "n_points": 0,
        "first_year": None,
        "last_year": None,
        "missing_years": [],
        "errors": [],
        "warnings": [],
    }

    if series is None or series.empty:
        result["errors"].append("No data returned for this indicator and year range.")
        result["missing_years"] = list(range(start_year, end_year + 1))
        return result

    clean = series.dropna()
    clean = clean[np.isfinite(clean.values.astype(float))]
    if len(clean) < len(series):
        result["warnings"].append("Some non-numeric or missing values were ignored.")

    years = sorted(int(y) for y in clean.index)
    result["n_points"] = len(years)
    if years:
        result["first_year"] = years[0]
        result["last_year"] = years[-1]

    result["missing_years"] = sorted(set(range(start_year, end_year + 1)) - set(years))

    if len(years) < min_points:
        result["errors"].append(
            f"Only {len(years)} data point(s) available; at least {min_points} are needed for analysis."
        )
        return result

    out_of_range = [y for y in years if y < start_year or y > end_year]
    if out_of_range:
        result["warnings"].append(f"Data outside the requested range: {out_of_range}.")

    if years[-1] < end_year:
        result["warnings"].append(
            f"Latest available year is {years[-1]}, but data through {end_year} was requested."
        )

    gaps = [y for y in result["missing_years"] if years[0] < y < years[-1]]
    if gaps:
        result["warnings"].append(f"Gaps inside the covered period: {gaps}.")

    result["ok"] = True
    return result
