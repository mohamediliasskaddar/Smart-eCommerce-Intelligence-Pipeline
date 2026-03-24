"""
dashboard/app.py
Streamlit entry point — run with: streamlit run dashboard/app.py
"""
import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dashboard.data_loader import get_kpis, load_products

st.set_page_config(
    page_title="Smart eCommerce Intelligence",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── SIDEBAR ───────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🛒 eCommerce Intelligence")
    st.caption("Smart ML & BI Dashboard")
    st.divider()
    st.markdown("""
    **Navigate:**
    - 📊 Overview
    - 🏆 Top-K Products
    - 🤖 ML Predictions
    - 💡 Insights & Rules
    """)
    st.divider()

    df = load_products()
    st.metric("Total Products", f"{len(df):,}")
    st.metric("Sources", df["source_store"].nunique())
    st.metric("Categories", df["category"].nunique())

    st.divider()
    st.caption("Data: data/processed/products.csv")
    st.caption("Module 1 → 4 complete")

# ── MAIN PAGE ─────────────────────────────────────────────────────────
st.title("🛒 Smart eCommerce Intelligence")
st.markdown("**ML-powered product analysis across 10 ecommerce sources**")
st.divider()

# ── TOP KPI STRIP ─────────────────────────────────────────────────────
kpis = get_kpis()

col1, col2, col3, col4, col5, col6 = st.columns(6)
col1.metric("Total Products",  f"{kpis['total_products']:,}")
col2.metric("Top-K Products",  f"{kpis['topk_count']}",
            f"{kpis['topk_pct']}% of catalog")
col3.metric("Avg Rating",      f"{kpis['avg_rating']} ★")
col4.metric("Avg Price",       f"€{kpis['avg_price']}")
col5.metric("In Stock",        f"{kpis['in_stock_pct']}%")
col6.metric("On Promo",        f"{kpis['on_promo_pct']}%")

st.divider()

# ── ML RESULTS STRIP ──────────────────────────────────────────────────
st.subheader("ML Pipeline Results")
col1, col2, col3, col4 = st.columns(4)
col1.metric("XGBoost ROC-AUC",   f"{kpis['xgb_roc_auc']}")
col2.metric("XGBoost Accuracy",  f"{kpis['xgb_accuracy']}")
col3.metric("KMeans Silhouette", f"{kpis['silhouette']}")
col4.metric("Anomalies Detected",f"{kpis['n_anomalies']}")

st.divider()
st.info("👈 Use the sidebar to navigate between pages.")
