"""
dashboard/pages/04_llm_insights.py
Page 4 — Association Rules + Anomalies + LLM Insights placeholder
"""
import streamlit as st
import plotly.express as px
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_loader import (
    load_association_rules, load_anomalies,
    load_products, load_evaluation_report
)
from dashboard.charts import chart_association_rules

st.set_page_config(page_title="Insights & Rules", page_icon="💡", layout="wide")
st.title("💡 Insights, Rules & Anomalies")
st.caption("Association rules, anomaly detection, and LLM-generated summaries")

rules     = load_association_rules()
anomalies = load_anomalies()
df        = load_products()
report    = load_evaluation_report()

# ── ASSOCIATION RULES ─────────────────────────────────────────────────
st.subheader("Association Rules — FP-Growth")

assoc = report.get("association_rules", {})
col1, col2, col3 = st.columns(3)
col1.metric("Total Rules",   assoc.get("total_rules",    "—"))
col2.metric("→ Top-K Rules", assoc.get("topk_rules",     "—"))
col3.metric("Min Lift",      assoc.get("min_lift_main",  "—"))

st.plotly_chart(chart_association_rules(rules), use_container_width=True)

# ── TOPK RULES TABLE ─────────────────────────────────────────────────
st.subheader("Rules Predicting Top-K Products")
topk_rules = rules[rules["consequents"].str.contains("topk:1", na=False)]

if len(topk_rules) == 0:
    st.warning("No topk:1 rules found — try lowering min_support in association_rules.py")
else:
    cols = ["antecedents", "consequents", "support", "confidence", "lift"]
    cols = [c for c in cols if c in topk_rules.columns]

    filter_min_lift = st.slider("Min lift", 1.0, 10.0, 1.3, 0.1)
    filtered = topk_rules[topk_rules["lift"] >= filter_min_lift].sort_values(
        "lift", ascending=False
    )
    st.caption(f"{len(filtered)} rules with lift ≥ {filter_min_lift}")
    st.dataframe(filtered[cols], use_container_width=True, hide_index=True)

    # Top rule insight
    if len(filtered) > 0:
        best = filtered.iloc[0]
        st.success(
            f"**Best rule:** {{{best['antecedents']}}} → {best['consequents']}  "
            f"| confidence={best['confidence']:.2f}  lift={best['lift']:.2f}"
        )

st.divider()

# ── ALL RULES EXPLORER ────────────────────────────────────────────────
st.subheader("Rules Explorer")
search_term = st.text_input("Search antecedents or consequents", "")
rules_display = rules.copy()
if search_term:
    rules_display = rules_display[
        rules_display["antecedents"].str.contains(search_term, case=False, na=False) |
        rules_display["consequents"].str.contains(search_term, case=False, na=False)
    ]

sort_by = st.selectbox("Sort by", ["lift", "confidence", "support"], index=0)
rules_display = rules_display.sort_values(sort_by, ascending=False)

show_cols = ["antecedents", "consequents", "support", "confidence", "lift"]
show_cols = [c for c in show_cols if c in rules_display.columns]
st.dataframe(rules_display[show_cols].head(100), use_container_width=True, hide_index=True)

st.divider()

# ── ANOMALIES ─────────────────────────────────────────────────────────
st.subheader("🔍 Anomaly Detection — DBSCAN")
st.caption("Products with unusual price/discount combinations detected by DBSCAN")

col1, col2 = st.columns([1, 3])
col1.metric("Anomalies Found", len(anomalies))
col1.metric("Anomaly Rate",    f"{len(anomalies)/len(df)*100:.2f}%")

if len(anomalies) > 0:
    with col2:
        disp_cols = ["name", "price", "discount_pct", "brand", "category", "source_store"]
        disp_cols = [c for c in disp_cols if c in anomalies.columns]
        st.dataframe(anomalies[disp_cols], use_container_width=True, hide_index=True)

    # Anomaly price distribution
    fig = px.scatter(
        anomalies, x="price", y="discount_pct",
        hover_data=["name", "brand"],
        color_discrete_sequence=["#ef4444"],
        title="Anomalous Products — Price vs Discount",
        labels={"price": "Price (€)", "discount_pct": "Discount %"},
        size_max=10,
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── LLM INSIGHTS (Module 5 placeholder) ──────────────────────────────
st.subheader("🤖 LLM-Generated Insights")
st.info(
    "**Module 5 — LLM Enrichment** will populate this section with:\n"
    "- AI-generated product summaries\n"
    "- Strategic recommendations from Claude/GPT\n"
    "- Sentiment analysis on product descriptions\n"
    "- Auto-generated Top-K narrative report\n\n"
    "Connect `llm/synthesis.py` to generate content and display it here."
)

# Show existing LLM prompt templates
prompts_dir = Path(__file__).parent.parent.parent / "llm" / "prompts"
if prompts_dir.exists():
    st.subheader("Configured LLM Prompts")
    for prompt_file in prompts_dir.glob("*.txt"):
        with st.expander(f"📄 {prompt_file.name}"):
            st.code(prompt_file.read_text(), language="text")
