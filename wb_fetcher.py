"""
wb_fetcher.py
Fetches indicators from the World Bank API and caches them locally as JSON.
Works fine on Termux (Android) - only needs `requests` and `pandas`.
"""

import requests
import pandas as pd
import json
from pathlib import Path

CACHE_DIR = Path(__file__).parent / "data_cache"
CACHE_DIR.mkdir(exist_ok=True)

# Friendly name -> World Bank indicator code
INDICATOR_MAP = {
    "youth_unemployment": "SL.UEM.1524.ZS",   # Unemployment, ages 15-24 (% of youth labor force)
    "inflation": "FP.CPI.TOTL.ZG",            # Inflation, consumer prices (annual %)
    "gdp_growth": "NY.GDP.MKTP.KD.ZG",        # GDP growth (annual %)
    "total_unemployment": "SL.UEM.TOTL.ZS",   # Total unemployment (% of labor force)
}


def fetch_worldbank_indicator(indicator_key, country="BGD", start_year=2010, end_year=2024, use_cache=True):
    """
    Fetch a World Bank indicator time series for a country.

    indicator_key: one of the keys in INDICATOR_MAP, or a raw WB indicator code.
    Returns: pandas Series indexed by year (int), sorted ascending. Empty Series on failure.
    """
    code = INDICATOR_MAP.get(indicator_key, indicator_key)
    cache_path = CACHE_DIR / f"{code}_{country}_{start_year}_{end_year}.json"

    if use_cache and cache_path.exists():
        with open(cache_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    else:
        url = (
            f"https://api.worldbank.org/v2/country/{country}/indicator/{code}"
            f"?date={start_year}:{end_year}&format=json&per_page=200"
        )
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            payload = resp.json()
            if len(payload) < 2 or payload[1] is None:
                print(f"[!] No data returned for {code}")
                return pd.Series(dtype=float)
            raw = payload[1]
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(raw, f)
        except requests.RequestException as e:
            print(f"[!] Fetch failed for {code}: {e}")
            return pd.Series(dtype=float)

    records = {}
    for item in raw:
        if item.get("value") is not None:
            records[int(item["date"])] = float(item["value"])

    return pd.Series(records).sort_index()


if __name__ == "__main__":
    s = fetch_worldbank_indicator("youth_unemployment")
    print(s)
