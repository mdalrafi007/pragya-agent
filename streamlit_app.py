"""
streamlit_app.py - web interface for Pragya, built for Streamlit Community Cloud
(free, no credit card, unlike Hugging Face's current Gradio/Docker tiers).

Entry point Streamlit Cloud runs automatically once deployed.
"""

import streamlit as st
import streamlit.components.v1 as components
from agent import run_query
from usage_limiter import check_and_increment

st.set_page_config(page_title="Pragya — Bangladesh Insight Agent", page_icon="📊")

st.title("Pragya (প্রজ্ঞা)")
st.caption(
    "Ask about Bangladesh's economy — youth unemployment, inflation, GDP growth — "
    "and get a bilingual (English + Bangla), data-backed report."
)

EXAMPLES = [
    "How has youth unemployment in Bangladesh changed since 2015?",
    "Compare inflation and GDP growth in Bangladesh from 2018 to 2024.",
    "Has total unemployment in Bangladesh been rising or falling recently?",
]

with st.expander("Example questions"):
    for ex in EXAMPLES:
        st.markdown(f"- {ex}")

question = st.text_input("Ask a question", placeholder="e.g. How has youth unemployment changed since 2015?")
ask = st.button("Ask Pragya", type="primary")

if ask:
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        allowed, remaining = check_and_increment()
        if not allowed:
            st.error(
                "This demo has hit its free daily question limit — please check "
                "back tomorrow. (This protects the project owner's API budget.)"
            )
        else:
            with st.spinner("Pragya is fetching data and thinking..."):
                try:
                    report_path = run_query(question)
                except Exception as e:
                    report_path = None
                    st.error(f"Something went wrong: {e}")

            if report_path:
                with open(report_path, "r", encoding="utf-8") as f:
                    html = f.read()
                components.html(html, height=800, scrolling=True)
                st.caption(f"{remaining} questions left in today's free quota.")
            elif report_path is None:
                st.info("The agent couldn't produce an answer for that question. Try rephrasing.")
