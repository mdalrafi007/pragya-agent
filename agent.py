"""
agent.py - the Pragya agentic loop.
Claude decides which indicators to fetch and how to analyze them,
then we run the tools locally and let Claude write the final bilingual summary.
"""

import os
import json
import anthropic
import pandas as pd

from wb_fetcher import fetch_worldbank_indicator, INDICATOR_MAP
from analyzer import detect_trend, compute_correlation
from chart_generator import generate_chart
from report_writer import write_insight_report

# Use the API key from the environment - never hardcode it in the file.
client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Cheap + fast model, plenty capable for this planning task.
MODEL = "claude-haiku-4-5"

TOOLS = [
    {
        "name": "fetch_indicator",
        "description": "Fetch a Bangladesh economic time series from the World Bank.",
        "input_schema": {
            "type": "object",
            "properties": {
                "indicator": {
                    "type": "string",
                    "enum": list(INDICATOR_MAP.keys()),
                },
                "start_year": {"type": "integer"},
                "end_year": {"type": "integer"},
            },
            "required": ["indicator"],
        },
    },
    {
        "name": "write_summary",
        "description": "Provide the final bilingual (English + Bangla) narrative summary of the analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary_en": {"type": "string"},
                "summary_bn": {"type": "string"},
            },
            "required": ["summary_en", "summary_bn"],
        },
    },
]

SYSTEM_PROMPT = (
    "You are Pragya, a bilingual (English/Bangla) socioeconomic analyst for Bangladesh. "
    "Given a user question, decide which indicators to fetch (youth_unemployment, inflation, "
    "gdp_growth, total_unemployment), call fetch_indicator for each one you need, then once you "
    "have the data described to you, call write_summary with a concise, specific, non-generic "
    "analysis in both English and Bangla. Reference actual years and directions of change. "
    "Keep each summary to 2-4 sentences."
)


def run_query(question: str, output_dir="outputs"):
    """Runs the full agent loop for a single natural-language question. Returns the report path."""
    messages = [{"role": "user", "content": question}]
    fetched = {}  # indicator_key -> pandas Series
    pending_summary = None  # (en, bn) offered before data existed - used only as last-resort fallback
    fallback_text = None  # plain-text answer, used only if Claude never calls a tool at all

    for _ in range(6):  # hard cap so a confused loop can't run forever
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOLS,
            messages=messages,
        )

        messages.append({"role": "assistant", "content": response.content})

        tool_blocks = [b for b in response.content if b.type == "tool_use"]
        text_blocks = [b for b in response.content if b.type == "text"]
        if text_blocks:
            fallback_text = " ".join(b.text for b in text_blocks)

        if not tool_blocks:
            break  # Claude answered in plain text only, or is done

        fetched_this_turn = False
        summary_en = summary_bn = None
        tool_results = []

        for block in tool_blocks:
            if block.name == "fetch_indicator":
                fetched_this_turn = True
                key = block.input["indicator"]
                start = block.input.get("start_year", 2010)
                end = block.input.get("end_year", 2024)
                series = fetch_worldbank_indicator(key, start_year=start, end_year=end)
                fetched[key] = series
                preview = series.round(2).to_dict()
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": json.dumps(preview) if preview else "No data available for that range.",
                })

            elif block.name == "write_summary":
                summary_en = block.input["summary_en"]
                summary_bn = block.input["summary_bn"]

        # Guard: if Claude wrote a summary in the SAME turn it also requested new
        # data, that summary was written blind - it can't have accounted for
        # numbers it hadn't seen yet. Don't finalize on it; nudge Claude to
        # look at the data first, but keep it as a last-resort fallback in case
        # the loop runs out before Claude tries again.
        if summary_en and fetched_this_turn:
            pending_summary = (summary_en, summary_bn)
            write_block = next(b for b in tool_blocks if b.name == "write_summary")
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": write_block.id,
                "content": (
                    "Not recorded yet - you requested new data in this same turn, "
                    "so review the fetched values above first, then call write_summary "
                    "again (repeating it unchanged is fine if it still holds)."
                ),
            })
        elif summary_en:
            messages.append({"role": "user", "content": tool_results + [{
                "type": "tool_result",
                "tool_use_id": next(b for b in tool_blocks if b.name == "write_summary").id,
                "content": "Summary received.",
            }]})
            return _finalize(question, summary_en, summary_bn, fetched, output_dir)

        messages.append({"role": "user", "content": tool_results})

    # Loop exhausted without a clean finalize - use best available fallback.
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
