"""
dashboard/pages/03_predictions.py
Page 3 — XGBoost Results + Feature Importance + Model Explainability
"""
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_loader import (
    load_xgboost_results, load_feature_importance,
    load_products, load_clusters
)
from dashboard.charts import chart_feature_importance, chart_confusion_matrix

st.set_page_config(page_title="ML Predictions", page_icon="🤖", layout="wide")
st.title("🤖 ML Predictions — XGBoost Classifier")
st.caption("Predicting which products belong to Top-K using structural features only")

xgb = load_xgboost_results()
imp = load_feature_importance()
df  = load_products()

# ── MODEL METRICS ─────────────────────────────────────────────────────
st.subheader("Model Performance")

col1, col2, col3 = st.columns(3)
col1.metric("ROC-AUC",  xgb["accuracy"],
            help="Area under ROC curve — 0.5=random, 1.0=perfect")
col2.metric("F1 Score", xgb["f1_score"],
            help="Harmonic mean of precision and recall")
col3.metric("Accuracy", xgb["accuracy"])

# Grade badge
grade = xgb.get("grade", "N/A")
color = {"EXCELLENT": "green", "GOOD": "blue",
         "ACCEPTABLE": "orange", "NEEDS WORK": "red"}.get(grade, "gray")
st.markdown(f"**Model grade:** :{color}[{grade}]")

st.info(
    "ℹ️ The model uses only structural features (price, brand, store, country, "
    "days since publish, stock, promo status) — **rating and review_count are excluded** "
    "to avoid data leakage from the target variable construction."
)

st.divider()

# ── CONFUSION MATRIX + FEATURE IMPORTANCE ─────────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.subheader("Confusion Matrix")
    st.caption(f"Test set: {xgb['n_test']} products")
    st.plotly_chart(
        chart_confusion_matrix(xgb["confusion_matrix"]),
        use_container_width=True
    )
    cm = xgb["confusion_matrix"]
    tn, fp, fn, tp = cm[0][0], cm[0][1], cm[1][0], cm[1][1]
    precision = round(tp / (tp + fp) * 100, 1) if (tp + fp) > 0 else 0
    recall    = round(tp / (tp + fn) * 100, 1) if (tp + fn) > 0 else 0
    st.markdown(f"""
    | Metric | Value |
    |--------|-------|
    | True Positives  | {tp} |
    | True Negatives  | {tn} |
    | False Positives | {fp} (non-top predicted as top) |
    | False Negatives | {fn} (top missed) |
    | Precision       | {precision}% |
    | Recall          | {recall}% |
    """)

with col2:
    st.subheader("Feature Importance")
    top_n = st.slider("Show top N features", 5, len(imp), 10)
    st.plotly_chart(
        chart_feature_importance(imp, top_n=top_n),
        use_container_width=True
    )

st.divider()

# ── PRICE DISTRIBUTION: TOP-K vs REST ─────────────────────────────────
st.subheader("Price Distribution — Top-K vs Rest")
df_plot = df.copy()
df_plot["group"] = df_plot["topk_label"].map({1: "Top-K ✓", 0: "Rest"})

fig = go.Figure()
for group, color in [("Top-K ✓", "#22c55e"), ("Rest", "#94a3b8")]:
    fig.add_trace(go.Histogram(
        x=df_plot[df_plot["group"] == group]["price"],
        name=group, nbinsx=40,
        marker_color=color, opacity=0.7,
    ))
fig.update_layout(
    barmode="overlay",
    xaxis_title="Price (€)",
    yaxis_title="Products",
    legend_title="",
    margin=dict(t=10, b=0),
)
st.plotly_chart(fig, use_container_width=True)

# ── BRAND ANALYSIS: TOP-K RATE ─────────────────────────────────────────
st.divider()
st.subheader("Top-K Rate by Brand (min. 10 products)")
brand_stats = df.groupby("brand").agg(
    count    = ("product_id", "count"),
    topk_rate= ("topk_label", "mean"),
    avg_price= ("price",      "mean"),
).reset_index()
brand_stats = brand_stats[brand_stats["count"] >= 10].sort_values("topk_rate", ascending=False)
brand_stats["topk_pct"] = (brand_stats["topk_rate"] * 100).round(1)

fig = px.bar(
    brand_stats.head(20), x="brand", y="topk_pct",
    color="avg_price", color_continuous_scale="Viridis",
    labels={"topk_pct": "Top-K Rate (%)", "brand": "Brand", "avg_price": "Avg Price"},
    title="Top-K Rate per Brand (color = avg price)",
)
fig.update_xaxes(tickangle=35)
fig.update_layout(margin=dict(t=40, b=80))
st.plotly_chart(fig, use_container_width=True)

# ── STORE PERFORMANCE ─────────────────────────────────────────────────
st.divider()
st.subheader("Store Performance Summary")
store_stats = df.groupby("source_store").agg(
    products   = ("product_id",   "count"),
    topk_count = ("topk_label",   "sum"),
    topk_rate  = ("topk_label",   "mean"),
    avg_price  = ("price",        "mean"),
    avg_rating = ("rating",       "mean"),
    in_stock   = ("in_stock",     "mean"),
).round(3).reset_index()
store_stats["topk_rate"] = (store_stats["topk_rate"] * 100).round(1).astype(str) + "%"
store_stats["in_stock"]  = (store_stats["in_stock"]  * 100).round(1).astype(str) + "%"
st.dataframe(store_stats, use_container_width=True, hide_index=True)
