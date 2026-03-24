"""
dashboard/pages/02_topk_products.py
Page 2 — Top-K Products + PCA Clusters
"""
import streamlit as st
import plotly.express as px
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from dashboard.data_loader import load_products, load_topk, load_pca, load_clusters
from dashboard.charts import chart_pca_clusters, format_topk_table, SEGMENT_COLORS

st.set_page_config(page_title="Top-K Products", page_icon="🏆", layout="wide")
st.title("🏆 Top-K Products")
st.caption("Best-performing products ranked by popularity score")

df      = load_products()
df_pca  = load_pca()

# ── SIDEBAR CONTROLS ──────────────────────────────────────────────────
with st.sidebar:
    st.header("Controls")
    k = st.slider("Top K", min_value=10, max_value=200, value=100, step=10)
    filter_segment = st.multiselect(
        "Filter by segment", ["budget", "mid_range", "premium"],
        default=["budget", "mid_range", "premium"]
    )
    filter_store = st.multiselect(
        "Filter by store", df["source_store"].unique().tolist(),
        default=df["source_store"].unique().tolist()
    )

df_topk = load_topk(k=k)

# Apply filters
if filter_segment and "segment" in df_topk.columns:
    df_topk = df_topk[df_topk["segment"].isin(filter_segment)]
if filter_store:
    df_topk = df_topk[df_topk["source_store"].isin(filter_store)]

# ── KPI STRIP ─────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Shown",          f"{len(df_topk)}")
col2.metric("Avg Price",      f"€{df_topk['price'].mean():.2f}")
col3.metric("Avg Rating",     f"{df_topk['rating'].mean():.2f} ★")
col4.metric("Avg Reviews",    f"{df_topk['review_count'].mean():.0f}")
col5.metric("On Promo",       f"{df_topk['is_on_promo'].mean()*100:.1f}%")

st.divider()

# ── PCA SCATTER ───────────────────────────────────────────────────────
st.subheader("Product Space — PCA 2D Clustering")
st.caption("Each dot = one product. Color = cluster segment. X = anomaly.")
st.plotly_chart(chart_pca_clusters(df_pca), use_container_width=True)

# Cluster summary
st.subheader("Cluster Profiles")
clusters = load_clusters()
df_with_cluster = df.merge(clusters[["product_id", "segment"]], on="product_id", how="left")
cluster_summary = df_with_cluster.groupby("segment").agg(
    count         = ("product_id",       "count"),
    avg_price     = ("price",            "mean"),
    avg_rating    = ("rating",           "mean"),
    avg_reviews   = ("review_count",     "mean"),
    topk_rate     = ("topk_label",       "mean"),
    on_promo_rate = ("is_on_promo",      "mean"),
).round(2).reset_index()
cluster_summary["topk_rate"]     = (cluster_summary["topk_rate"] * 100).round(1).astype(str) + "%"
cluster_summary["on_promo_rate"] = (cluster_summary["on_promo_rate"] * 100).round(1).astype(str) + "%"
st.dataframe(cluster_summary, use_container_width=True, hide_index=True)

st.divider()

# ── TOP-K TABLE ───────────────────────────────────────────────────────
st.subheader(f"Top-{len(df_topk)} Products Table")

# Search box
search = st.text_input("Search by name or brand", "")
if search:
    mask    = (df_topk["name"].str.contains(search, case=False, na=False) |
               df_topk["brand"].str.contains(search, case=False, na=False))
    df_topk = df_topk[mask]

st.dataframe(
    format_topk_table(df_topk),
    use_container_width=True,
    hide_index=True,
)

# Download button
csv = df_topk.to_csv(index=False).encode("utf-8")
st.download_button(
    "⬇ Download Top-K CSV",
    data=csv,
    file_name=f"topk_{k}_products.csv",
    mime="text/csv",
)

# ── CATEGORY BREAKDOWN IN TOP-K ────────────────────────────────────────
st.divider()
st.subheader("Top-K Breakdown by Category")
cat_counts = df_topk["category"].value_counts().head(15).reset_index()
cat_counts.columns = ["category", "count"]
fig = px.bar(
    cat_counts, x="count", y="category",
    orientation="h",
    color="count",
    color_continuous_scale="Purples",
    labels={"count": "Products in Top-K", "category": ""},
)
fig.update_coloraxes(showscale=False)
fig.update_layout(margin=dict(t=10, b=0))
st.plotly_chart(fig, use_container_width=True)
