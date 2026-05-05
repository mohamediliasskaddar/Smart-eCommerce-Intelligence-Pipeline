"""
dashboard/pages/04_llm_insights.py
Page 4 — LLM Chat + Association Rules + Anomalies + Synthesis
"""
import os
import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
DATA_PATH = os.getenv("DATA_PATH", "/app/data")

from dashboard.data_loader import (
    load_association_rules, load_anomalies, load_evaluation_report
)
from dashboard.charts import chart_association_rules

st.set_page_config(page_title="LLM Insights", page_icon="💡", layout="wide")
st.title("💡 LLM Insights & Intelligence")

tab1, tab2, tab3, tab4 = st.tabs([
    "🤖 Chat Assistant",
    "📊 Association Rules",
    "⚠️ Anomalies",
    "📄 Auto Reports",
])


# ══════════════════════════════════════════════════════════════════════
# TAB 1 — CHAT ASSISTANT
# ══════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("eCommerce AI Assistant")
    st.caption("Ask questions about your product data. Off-topic questions will be refused.")

    # ── MODEL SELECTOR ────────────────────────────────────────────────
    try:
        from llm.llm_client import list_models, get_llm_with_fallback
        from llm.chains import guard_chain, chat_chain
        from llm.context_builder import get_context_for_question

        col1, col2 = st.columns([2, 1])
        with col1:
            model_label = st.selectbox("Model", list_models(), index=0)
        with col2:
            temperature = st.slider("Temperature", 0.0, 1.0, 0.3, 0.1)

        LLM_AVAILABLE = True
    except ImportError as e:
        st.warning(f"LLM dependencies missing: {e}")
        st.code("pip install langchain-groq langchain-google-genai langchain-core")
        LLM_AVAILABLE = False

    # ── CHAT HISTORY ──────────────────────────────────────────────────
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    # Display history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # ── EXAMPLE QUESTIONS ─────────────────────────────────────────────
    if not st.session_state.chat_history:
        st.markdown("**Try asking:**")
        examples = [
            "What are the top 5 products and why?",
            "Which price segment has the best performance?",
            "What do the association rules tell us about buying patterns?",
            "Are there any unusual pricing anomalies?",
            "Give me a strategic report on our product catalog.",
        ]
        cols = st.columns(len(examples))
        for col, example in zip(cols, examples):
            if col.button(example[:30] + "...", use_container_width=True):
                st.session_state.chat_history.append({"role": "user", "content": example})
                st.rerun()

    # ── CHAT INPUT ────────────────────────────────────────────────────
    if LLM_AVAILABLE:
        if prompt := st.chat_input("Ask about your ecommerce data..."):
            st.session_state.chat_history.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    try:
                        llm = get_llm_with_fallback(model_label, temperature=temperature)

                        # Step 1 — guardrail check (fast)
                        guard = guard_chain(llm)
                        verdict = guard.invoke({"question": prompt}).strip().upper()

                        if "IRRELEVANT" in verdict:
                            response = ("I can only answer questions about the ecommerce "
                                        "dataset and product analysis. Try asking about "
                                        "top products, pricing, trends, or market insights.")
                        else:
                            # Step 2 — get relevant context
                            context = get_context_for_question(prompt)

                            # Step 3 — build history string
                            history = ""
                            if len(st.session_state.chat_history) > 2:
                                recent = st.session_state.chat_history[-4:-1]
                                history = "\n".join(
                                    f"{m['role'].upper()}: {m['content']}"
                                    for m in recent
                                )

                            # Step 4 — run chat chain
                            chain    = chat_chain(llm)
                            response = chain.invoke({
                                "context":    context,
                                "history":    history or "No previous messages.",
                                "question":   prompt,
                                "n_products": 3809,
                            })

                        st.markdown(response)
                        st.session_state.chat_history.append({
                            "role": "assistant", "content": response
                        })

                    except Exception as e:
                        err = f"Error: {e}"
                        st.error(err)
                        st.session_state.chat_history.append({
                            "role": "assistant", "content": err
                        })

        # Clear history button
        if st.session_state.chat_history:
            if st.button("🗑 Clear conversation"):
                st.session_state.chat_history = []
                st.rerun()


# ══════════════════════════════════════════════════════════════════════
# TAB 2 — ASSOCIATION RULES
# ══════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("Association Rules — FP-Growth")
    rules    = load_association_rules()
    report   = load_evaluation_report()
    assoc    = report.get("association_rules", {})

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Rules",   assoc.get("total_rules",   "—"))
    col2.metric("→ Top-K Rules", assoc.get("topk_rules",    "—"))
    col3.metric("Min Lift",      assoc.get("min_lift_main", "—"))

    st.plotly_chart(chart_association_rules(rules), use_container_width=True)

    st.subheader("Rules → topk:1 (Best rules for predicting top products)")
    topk_rules = rules[rules["consequents"].str.contains("topk:1", na=False)]

    if len(topk_rules) == 0:
        st.warning("No topk:1 rules found.")
    else:
        min_lift = st.slider("Minimum lift", 1.0, 10.0, 1.3, 0.1, key="lift_tab2")
        filtered = topk_rules[topk_rules["lift"] >= min_lift].sort_values("lift", ascending=False)
        st.caption(f"{len(filtered)} rules with lift ≥ {min_lift}")

        show = ["antecedents", "consequents", "support", "confidence", "lift"]
        show = [c for c in show if c in filtered.columns]
        st.dataframe(filtered[show], use_container_width=True, hide_index=True)

        if len(filtered) > 0:
            best = filtered.iloc[0]
            st.success(f"**Best rule:** {{{best['antecedents']}}} → topk:1 | "
                       f"conf={best['confidence']:.2f}  lift={best['lift']:.2f}")

    st.subheader("All Rules Explorer")
    search = st.text_input("Search", "", key="search_tab2")
    rules_display = rules.copy()
    if search:
        mask = (rules_display["antecedents"].str.contains(search, case=False, na=False) |
                rules_display["consequents"].str.contains(search, case=False, na=False))
        rules_display = rules_display[mask]
    sort_col = st.selectbox("Sort by", ["lift", "confidence", "support"])
    show = ["antecedents", "consequents", "support", "confidence", "lift"]
    show = [c for c in show if c in rules_display.columns]
    st.dataframe(
        rules_display[show].sort_values(sort_col, ascending=False).head(100),
        use_container_width=True, hide_index=True
    )


# ══════════════════════════════════════════════════════════════════════
# TAB 3 — ANOMALIES
# ══════════════════════════════════════════════════════════════════════
with tab3:
    import plotly.express as px
    st.subheader("Anomaly Detection — DBSCAN")
    anomalies = load_anomalies()

    col1, col2 = st.columns([1, 3])
    col1.metric("Anomalies Found", len(anomalies))

    if len(anomalies) > 0:
        disp = ["name", "price", "discount_pct", "brand", "category", "source_store"]
        disp = [c for c in disp if c in anomalies.columns]
        with col2:
            st.dataframe(anomalies[disp], use_container_width=True, hide_index=True)

        if "price" in anomalies.columns and "discount_pct" in anomalies.columns:
            fig = px.scatter(
                anomalies, x="price", y="discount_pct",
                hover_data=["name", "brand"] if "brand" in anomalies.columns else [],
                color_discrete_sequence=["#ef4444"],
                title="Anomalous Products — Price vs Discount",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No anomalies detected in the dataset.")


# ══════════════════════════════════════════════════════════════════════
# TAB 4 — AUTO REPORTS
# ══════════════════════════════════════════════════════════════════════
with tab4:
    st.subheader("Auto-Generated Reports")
    st.caption(f"LLM-generated executive summaries saved to {Path(DATA_PATH) / 'output'}/")

    OUTPUT_DIR = Path(DATA_PATH) / "output"

    # Generate button
    if LLM_AVAILABLE:
        col1, col2 = st.columns([2, 1])
        with col1:
            report_model = st.selectbox(
                "Model for report generation",
                list_models(), index=0, key="report_model"
            )
        with col2:
            st.write("")
            st.write("")
            if st.button("▶ Generate Reports", type="primary"):
                with st.spinner("Generating reports (may take 30–60 seconds)..."):
                    try:
                        from llm.synthesis import run_synthesis
                        results = run_synthesis(report_model)
                        st.success(f"Reports generated and saved to {Path(DATA_PATH) / 'output'}/")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Generation failed: {e}")

    # Display existing reports
    for fname, title in [
        ("llm_topk_summary.txt",    "Top-K Products Summary"),
        ("llm_strategy_report.txt", "Strategic Market Report"),
    ]:
        fpath = OUTPUT_DIR / fname
        if fpath.exists():
            with st.expander(f"📄 {title}", expanded=True):
                st.markdown(fpath.read_text(encoding="utf-8"))
                st.download_button(
                    f"⬇ Download {fname}",
                    data=fpath.read_bytes(),
                    file_name=fname,
                    mime="text/plain",
                )
        else:
            with st.expander(f"📄 {title} (not yet generated)"):
                st.info("Click 'Generate Reports' above to create this report.")

    # Audit log
    try:
        from llm.mcp_agents import get_audit_log
        log = get_audit_log()
        if log:
            st.subheader("Agent Audit Log (MCP)")
            import pandas as pd
            df_log = pd.DataFrame(log[-20:])
            st.dataframe(df_log, use_container_width=True, hide_index=True)
    except Exception:
        pass
