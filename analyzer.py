"""analyzer.py - lightweight statistical helpers, no heavy dependencies."""

import numpy as np
import pandas as pd


def _slope_per_year(series: pd.Series) -> float:
    """Least-squares slope of value against the actual year index."""
    x = series.index.values.astype(float)
    return float(np.polyfit(x, series.values.astype(float), 1)[0])


def detect_trend(series: pd.Series, threshold=0.05):
    """Return 'rising', 'falling', or 'stable' based on linear fit slope (units per year)."""
    series = series.dropna().sort_index()
    if len(series) < 2:
        return "insufficient data"
    slope = _slope_per_year(series)
    if slope > threshold:
        return "rising"
    if slope < -threshold:
        return "falling"
    return "stable"


def compute_correlation(a: pd.Series, b: pd.Series):
    """Pearson correlation over the overlapping years of two series."""
    df = pd.concat([a, b], axis=1, join="inner").dropna()
    if len(df) < 3:
        return None
    return round(df.iloc[:, 0].corr(df.iloc[:, 1]), 3)


def find_inflection_years(series: pd.Series, window=1):
    """Years where year-over-year change flips sign (rough structural breaks)."""
    series = series.dropna().sort_index()
    diffs = series.diff().dropna()
    signs = np.sign(diffs)
    flips = signs[signs.diff().fillna(0) != 0].index.tolist()
    return flips


def analyze_series(series: pd.Series, unit: str = "%", stable_band: float = 0.1) -> dict:
    """Return deterministic statistics for a year-indexed time series.

    unit:        unit of the series values ("%" for all current indicators).
    stable_band: a net change smaller than this (in the series' unit) counts as 'stable'.

    Always returns a dict with a "status" key: "ok" or "insufficient_data".

    Two direction fields are returned on purpose, and they can disagree:
      net_direction - first value vs last value
      trend         - best-fit line across every year
    absolute_change is in the series' unit (percentage points for "%" series).
    percentage_change is the relative change from the first value, as a percent.
    It is None when the first value is 0. The absolute value of the first value is
    used as the denominator so a move from -2 to +1 is reported as an increase.
    """
    clean = series.dropna().sort_index()

    if len(clean) < 2:
        return {"status": "insufficient_data", "n_points": int(len(clean))}

    first_year, last_year = int(clean.index[0]), int(clean.index[-1])
    first_value, last_value = float(clean.iloc[0]), float(clean.iloc[-1])
    absolute_change = last_value - first_value

    percentage_change = (
        round(absolute_change / abs(first_value) * 100, 2) if first_value != 0 else None
    )

    if absolute_change > stable_band:
        net_direction = "rising"
    elif absolute_change < -stable_band:
        net_direction = "falling"
    else:
        net_direction = "stable"

    peak_year, trough_year = int(clean.idxmax()), int(clean.idxmin())

    return {
        "status": "ok",
        "unit": unit,
        "n_points": int(len(clean)),
        "first_year": first_year,
        "first_value": round(first_value, 2),
        "last_year": last_year,
        "last_value": round(last_value, 2),
        "absolute_change": round(absolute_change, 2),
        "change_unit": "percentage points" if unit == "%" else unit,
        "percentage_change": percentage_change,
        "net_direction": net_direction,
        "trend": detect_trend(clean),
        "slope_per_year": round(_slope_per_year(clean), 3),
        "peak": {"year": peak_year, "value": round(float(clean.loc[peak_year]), 2)},
        "trough": {"year": trough_year, "value": round(float(clean.loc[trough_year]), 2)},
    }
