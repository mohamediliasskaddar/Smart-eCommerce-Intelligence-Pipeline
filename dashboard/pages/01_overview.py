"""
dashboard/pages/01_overview.py
Page 1 — Dataset Overview & KPIs
"""

import streamlit as st
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_loader import load_products, load_source_quality, get_kpis
from dashboard.charts import (
    chart_price_segments, chart_source_breakdown,
    chart_rating_distribution, chart_price_vs_rating,
    chart_stock_status, chart_discount_by_segment,
    chart_popularity_distribution,
)

st.set_page_config(page_title="Overview", page_icon="📊", layout="wide")
st.title("📊 Dataset Overview")
st.caption("Distribution, quality, and coverage across all 10 sources")

df   = load_products()
kpis = get_kpis()

# ── FILTERS (sidebar) ────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    selected_stores = st.multiselect(
        "Source stores", df["source_store"].unique().tolist(),
        default=df["source_store"].unique().tolist()
    )
    selected_segments = st.multiselect(
        "Price segment", ["low", "mid", "high"], default=["low", "mid", "high"]
    )

df_filtered = df[
    df["source_store"].isin(selected_stores) &
    df["price_segment"].isin(selected_segments)
]
st.caption(f"Showing {len(df_filtered):,} of {len(df):,} products")

# ── ROW 1: Price segment + Source breakdown ───────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(chart_price_segments(df_filtered), use_container_width=True)
with col2:
    st.plotly_chart(chart_source_breakdown(df_filtered), use_container_width=True)

# ── ROW 2: Rating + Price vs Rating ──────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(chart_rating_distribution(df_filtered), use_container_width=True)
with col2:
    st.plotly_chart(chart_price_vs_rating(df_filtered), use_container_width=True)

# ── ROW 3: Stock status + Discount by segment ─────────────────────────
col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(chart_stock_status(df_filtered), use_container_width=True)
with col2:
    st.plotly_chart(chart_discount_by_segment(df_filtered), use_container_width=True)

# ── ROW 4: Popularity distribution ───────────────────────────────────
st.plotly_chart(chart_popularity_distribution(df_filtered), use_container_width=True)

# ── SOURCE QUALITY TABLE ──────────────────────────────────────────────
st.subheader("Source Quality Report")
sq = load_source_quality()
display_cols = ["source", "total_products", "quality_score", "recommendation",
                "rating_missing_%", "description_missing_%", "price_zero"]
display_cols = [c for c in display_cols if c in sq.columns]
st.dataframe(
    sq[display_cols].style.background_gradient(
        subset=["quality_score"], cmap="RdYlGn"
    ),
    use_container_width=True, hide_index=True
)
