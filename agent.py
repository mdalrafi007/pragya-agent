import os
import pandas as pd
from google import genai
from google.genai import types

from wb_fetcher import fetch_worldbank_indicator, INDICATOR_MAP
from validator import validate_series
from analyzer import analyze_series
from report_writer import write_insight_report
from chart_generator import generate_chart

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY") or "not-configured")

MODEL = "gemini-3.6-flash"

FETCH_DECLARATION = types.FunctionDeclaration(
    name="fetch_indicator",
    description="Fetch a Bangladesh economic time series from the World Bank.",
    parameters={
        "type": "object",
        "properties": {
            "indicator": {"type": "string", "enum": list(INDICATOR_MAP.keys())},
            "start_year": {"type": "integer"},
            "end_year": {"type": "integer"},
        },
        "required": ["indicator"],
    },
)

WRITE_SUMMARY_DECLARATION = types.FunctionDeclaration(
    name="write_summary",
    description="Provide the final bilingual (English + Bangla) narrative summary of the analysis.",
    parameters={
        "type": "object",
        "properties": {
            "summary_en": {"type": "string"},
            "summary_bn": {"type": "string"},
        },
        "required": ["summary_en", "summary_bn"],
    },
)

TOOLS = [types.Tool(function_declarations=[FETCH_DECLARATION, WRITE_SUMMARY_DECLARATION])]

SYSTEM_PROMPT = (
    "You are Pragya, a bilingual (English/Bangla) socioeconomic analyst for Bangladesh. "
    "Given a user question, decide which indicators to fetch (youth_unemployment, inflation, "
    "gdp_growth, total_unemployment), call fetch_indicator for each one you need, then once you "
    "have the data described to you, call write_summary with a concise, specific, non-generic "
    "analysis in both English and Bangla. Reference actual years and directions of change. "
    "Keep each summary to 2-4 sentences. "
    "Each fetch_indicator result contains Python-computed statistics under 'analysis' and "
    "data-quality notes under 'validation'. Use the computed figures exactly as given and never "
    "calculate your own changes, averages, or percentages. absolute_change is in percentage points; "
    "percentage_change is the relative change from the first value and must never be described as "
    "percentage points. net_direction compares the first and last values while trend is the "
    "best-fit line, so they can differ; explain a difference briefly if it matters. If "
    "analysis.status is not 'ok', say the data is unavailable or insufficient instead of guessing. "
    "Mention validation warnings that affect the interpretation, such as missing recent years."
)

CONFIG = types.GenerateContentConfig(
    system_instruction=SYSTEM_PROMPT,
    tools=TOOLS,
)


def analyze_indicator(key, series, start, end):
    """Python-only stage between fetching and interpretation.

    Runs automatically after every fetch, so the model never decides whether
    (or how) the basic statistics get calculated.
    """
    return {
        "indicator": key,
        "validation": validate_series(series, start, end),
        "analysis": analyze_series(series, unit="%"),
    }


def build_tool_result(key, series, start, end):
    """What Gemini receives after fetch_indicator: computed analysis plus the raw values."""
    result = analyze_indicator(key, series, start, end)
    result["values"] = {str(int(year)): round(float(value), 2) for year, value in series.items()}
    return result


def run_query(question: str, output_dir="outputs"):
    contents = [types.Content(role="user", parts=[types.Part.from_text(text=question)])]
    fetched = {}
    pending_summary = None
    fallback_text = None

    for _ in range(6):
        response = client.models.generate_content(model=MODEL, contents=contents, config=CONFIG)

        model_parts = response.parts or []
        contents.append(types.Content(role="model", parts=model_parts))

        if response.text:
            fallback_text = response.text

        calls = response.function_calls or []
        if not calls:
            break

        fetched_this_turn = False
        summary_en = summary_bn = None
        response_parts = []

        for call in calls:
            if call.name == "fetch_indicator":
                fetched_this_turn = True
                key = call.args["indicator"]
                start = int(call.args.get("start_year", 2010))
                end = int(call.args.get("end_year", 2024))
                series = fetch_worldbank_indicator(key, start_year=start, end_year=end)
                fetched[key] = series
                response_parts.append(types.Part.from_function_response(
                    name="fetch_indicator",
                    response={"result": build_tool_result(key, series, start, end)},
                ))

            elif call.name == "write_summary":
                summary_en = call.args["summary_en"]
                summary_bn = call.args["summary_bn"]

        if summary_en and fetched_this_turn:
            pending_summary = (summary_en, summary_bn)
            response_parts.append(types.Part.from_function_response(
                name="write_summary",
                response={"result": (
                    "Not recorded yet - you requested new data in this same turn, "
                    "so review the computed analysis above first, then call write_summary "
                    "again (repeating it unchanged is fine if it still holds)."
                )},
            ))
        elif summary_en:
            response_parts.append(types.Part.from_function_response(
                name="write_summary",
                response={"result": "Summary received."},
            ))
            contents.append(types.Content(role="user", parts=response_parts))
            return _finalize(question, summary_en, summary_bn, fetched, output_dir)

        contents.append(types.Content(role="user", parts=response_parts))

    if pending_summary:
        return _finalize(question, pending_summary[0], pending_summary[1], fetched, output_dir)
    if fallback_text:
        return _finalize(question, fallback_text, "(বাংলা অনুবাদ পাওয়া যায়নি)", fetched, output_dir)
    return None


def _finalize(question, summary_en, summary_bn, fetched, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    chart_path = None
    if fetched:
        chart_path = os.path.join(output_dir, "chart_latest.png")
        generate_chart(
            fetched,
            title_en="Pragya Insight",
            title_bn="প্রজ্ঞা বিশ্লেষণ",
            xlabel="Year",
            ylabel="Value",
            out_path=chart_path,
        )

    df = pd.DataFrame(fetched) if fetched else pd.DataFrame()

    return write_insight_report(
        query=question,
        summary_en=summary_en,
        summary_bn=summary_bn,
        chart_path=chart_path,
        data_df=df,
        output_dir=output_dir,
    )


if __name__ == "__main__":
    path = run_query("How has youth unemployment in Bangladesh changed since 2015?")
    print(f"Report written to: {path}")
