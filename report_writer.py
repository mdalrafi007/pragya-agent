"""report_writer.py - builds a clean, self-contained bilingual HTML report.

The chart is embedded as a base64 data URI (not a relative file path) so the
report renders correctly whether opened directly, embedded in a Streamlit
component, or shown inside a Gradio HTML block - all of which lose track of
relative file paths on disk.
"""

import os
import base64
from datetime import datetime

TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
  body {{ font-family: 'Segoe UI', Arial, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1a1a1a; }}
  h1 {{ font-size: 1.6em; border-bottom: 2px solid #2b6cb0; padding-bottom: 8px; }}
  .meta {{ color: #666; font-size: 0.9em; margin-bottom: 20px; }}
  .summary {{ background: #f7f9fc; padding: 16px; border-left: 4px solid #2b6cb0; border-radius: 4px; margin: 16px 0; }}
  .bn {{ font-family: 'Noto Sans Bengali', Arial, sans-serif; }}
  img {{ max-width: 100%; border-radius: 6px; margin: 20px 0; }}
  pre {{ background: #f4f4f4; padding: 12px; border-radius: 4px; overflow-x: auto; font-size: 0.85em; }}
</style>
</head>
<body>
  <h1>{title}</h1>
  <div class="meta">Generated {date} · Pragya Insight Agent</div>
  <div class="summary">
    <p>{summary_en}</p>
    <p class="bn">{summary_bn}</p>
  </div>
  {chart_tag}
  <h3>Data preview</h3>
  <pre>{data_preview}</pre>
</body>
</html>
"""


def write_insight_report(query, summary_en, summary_bn, chart_path, data_df, output_dir="outputs"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"report_{timestamp}.html"
    filepath = os.path.join(output_dir, filename)

    chart_tag = ""
    if chart_path and os.path.exists(chart_path):
        with open(chart_path, "rb") as img_f:
            b64 = base64.b64encode(img_f.read()).decode("ascii")
        chart_tag = f'<img src="data:image/png;base64,{b64}" alt="Chart">'

    data_preview = data_df.round(2).to_string() if data_df is not None and not data_df.empty else "(no tabular data)"

    html = TEMPLATE.format(
        title=query,
        date=datetime.now().strftime("%B %d, %Y"),
        summary_en=summary_en,
        summary_bn=summary_bn,
        chart_tag=chart_tag,
        data_preview=data_preview,
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filepath
