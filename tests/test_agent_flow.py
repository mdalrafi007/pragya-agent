"""Checks that Python computes the statistics before Gemini interprets them.

Gemini and the World Bank are replaced with fakes, so no network or API key is needed.
"""

import os
import sys
from types import SimpleNamespace as NS

import pandas as pd
from google.genai import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import agent

EXAMPLE = pd.Series({2019: 8.2, 2020: 9.1, 2021: 8.4, 2022: 7.9, 2023: 7.5})


def _call(name, args):
    return NS(
        parts=[types.Part.from_function_call(name=name, args=args)],
        text=None,
        function_calls=[NS(name=name, args=args)],
    )


def _run(monkeypatch, tmp_path, series):
    script = [
        _call("fetch_indicator", {"indicator": "youth_unemployment", "start_year": 2019, "end_year": 2023}),
        _call("write_summary", {"summary_en": "summary", "summary_bn": "সারাংশ"}),
    ]
    seen = []

    class FakeModels:
        def generate_content(self, model, contents, config):
            seen.append(list(contents))
            return script[len(seen) - 1]

    monkeypatch.setattr(agent, "client", NS(models=FakeModels()))
    monkeypatch.setattr(agent, "fetch_worldbank_indicator", lambda key, start_year, end_year: series)
    report = agent.run_query("test question", output_dir=str(tmp_path))
    # what Gemini was sent right after its fetch_indicator call
    result = seen[1][-1].parts[0].function_response.response["result"]
    return report, result


def test_gemini_receives_python_computed_analysis(monkeypatch, tmp_path):
    report, result = _run(monkeypatch, tmp_path, EXAMPLE)
    assert os.path.exists(report)
    assert result["validation"]["ok"] is True
    assert result["analysis"]["status"] == "ok"
    assert result["analysis"]["net_direction"] == "falling"
    assert result["analysis"]["absolute_change"] == -0.7
    assert result["analysis"]["first_value"] == 8.2 and result["analysis"]["last_value"] == 7.5


def test_empty_data_reaches_gemini_as_insufficient_not_invented(monkeypatch, tmp_path):
    _, result = _run(monkeypatch, tmp_path, pd.Series(dtype=float))
    assert result["validation"]["ok"] is False
    assert result["analysis"]["status"] == "insufficient_data"
    assert result["values"] == {}
