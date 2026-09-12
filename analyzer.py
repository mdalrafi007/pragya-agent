"""analyzer.py - lightweight statistical helpers, no heavy dependencies."""

import numpy as np
import pandas as pd


def detect_trend(series: pd.Series, threshold=0.05):
    """Return 'rising', 'falling', or 'stable' based on linear fit slope."""
    series = series.dropna()
    if len(series) < 2:
        return "insufficient data"
    x = np.arange(len(series))
    slope = np.polyfit(x, series.values, 1)[0]
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
