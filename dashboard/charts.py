"""
dashboard/charts.py
All Plotly chart functions — imported by every page.
No Streamlit imports here — pure chart logic only.
"""
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np

# ── COLOR PALETTE ─────────────────────────────────────────────────────
COLORS = {
    "primary":   "#6366f1",   # indigo
    "success":   "#22c55e",   # green
    "warning":   "#f59e0b",   # amber
    "danger":    "#ef4444",   # red
    "muted":     "#94a3b8",   # slate
    "budget":    "#3b82f6",   # blue
    "mid_range": "#8b5cf6",   # violet
    "premium":   "#f59e0b",   # amber
}

SEGMENT_COLORS = {
    "budget":    COLORS["budget"],
    "mid_range": COLORS["mid_range"],
    "premium":   COLORS["premium"],
}

STORE_COLORS = px.colors.qualitative.Set2


# ── 1. PRICE SEGMENT DONUT ─────────────────────────────────────────────
def chart_price_segments(df: pd.DataFrame) -> go.Figure:
    counts = df["price_segment"].value_counts().reset_index()
    counts.columns = ["segment", "count"]
    fig = px.pie(
        counts, names="segment", values="count",
        hole=0.55,
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        title="Price Segment Distribution",
    )
    fig.update_traces(textposition="outside", textinfo="percent+label")
    fig.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
    return fig


# ── 2. PRODUCTS BY SOURCE (horizontal bar) ────────────────────────────
def chart_source_breakdown(df: pd.DataFrame) -> go.Figure:
    counts = df["source_store"].value_counts().reset_index()
    counts.columns = ["store", "count"]
    counts = counts.sort_values("count")

    fig = px.bar(
        counts, x="count", y="store",
        orientation="h",
        color="count",
        color_continuous_scale="Blues",
        title="Products by Source Store",
        labels={"count": "Products", "store": ""},
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    return fig


# ── 3. RATING DISTRIBUTION (histogram) ────────────────────────────────
def chart_rating_distribution(df: pd.DataFrame) -> go.Figure:
    fig = px.histogram(
        df, x="rating", nbins=30,
        color_discrete_sequence=[COLORS["primary"]],
        title="Rating Distribution",
        labels={"rating": "Rating", "count": "Products"},
    )
    fig.add_vline(
        x=df["rating"].mean(), line_dash="dash",
        line_color=COLORS["warning"],
        annotation_text=f"Mean: {df['rating'].mean():.2f}",
    )
    fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    return fig


# ── 4. PRICE VS RATING SCATTER ─────────────────────────────────────────
def chart_price_vs_rating(df: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        df.sample(min(1000, len(df)), random_state=42),
        x="price", y="rating",
        color="price_segment",
        color_discrete_map=SEGMENT_COLORS,
        size="review_count",
        size_max=20,
        hover_data=["name", "brand", "source_store"],
        title="Price vs Rating (bubble = review count)",
        labels={"price": "Price (€)", "rating": "Rating"},
        opacity=0.7,
    )
    fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    return fig


# ── 5. STOCK STATUS BAR ───────────────────────────────────────────────
def chart_stock_status(df: pd.DataFrame) -> go.Figure:
    stock = df.groupby(["source_store", "in_stock"]).size().reset_index(name="count")
    stock["status"] = stock["in_stock"].map({True: "In Stock", False: "Out of Stock"})

    fig = px.bar(
        stock, x="source_store", y="count",
        color="status",
        color_discrete_map={"In Stock": COLORS["success"], "Out of Stock": COLORS["danger"]},
        title="Stock Status by Store",
        labels={"source_store": "Store", "count": "Products"},
        barmode="stack",
    )
    fig.update_xaxes(tickangle=30)
    fig.update_layout(margin=dict(t=40, b=60, l=0, r=0), legend_title="")
    return fig


# ── 6. PCA SCATTER (clusters) ─────────────────────────────────────────
def chart_pca_clusters(df_pca: pd.DataFrame) -> go.Figure:
    fig = px.scatter(
        df_pca, x="PC1", y="PC2",
        color="segment",
        color_discrete_map=SEGMENT_COLORS,
        symbol="is_anomaly",
        symbol_map={0: "circle", 1: "x"},
        hover_data=["name", "price", "rating", "category"],
        title="PCA 2D — Product Clusters",
        labels={"PC1": "Principal Component 1", "PC2": "Principal Component 2"},
        opacity=0.7,
    )
    fig.update_traces(marker_size=6)
    fig.update_layout(margin=dict(t=40, b=0, l=0, r=0), legend_title="Segment")
    return fig


# ── 7. TOP-K TABLE (styled) ───────────────────────────────────────────
def format_topk_table(df_topk: pd.DataFrame) -> pd.DataFrame:
    cols = ["rank", "name", "brand", "category", "price",
            "rating", "review_count", "discount_pct",
            "price_segment", "source_store", "popularity_score"]
    cols = [c for c in cols if c in df_topk.columns]
    out = df_topk[cols].copy()
    out["price"]           = out["price"].apply(lambda x: f"€{x:.2f}")
    out["rating"]          = out["rating"].apply(lambda x: f"{x:.1f} ★")
    out["discount_pct"]    = out["discount_pct"].apply(lambda x: f"{x:.1f}%")
    out["popularity_score"]= out["popularity_score"].apply(lambda x: f"{x:.3f}")
    out["review_count"]    = out["review_count"].apply(lambda x: f"{x:,}")
    out.columns = [c.replace("_", " ").title() for c in out.columns]
    return out


# ── 8. FEATURE IMPORTANCE BAR ─────────────────────────────────────────
def chart_feature_importance(df_imp: pd.DataFrame, top_n: int = 10) -> go.Figure:
    df = df_imp.head(top_n).sort_values("importance")
    fig = px.bar(
        df, x="importance", y="feature",
        orientation="h",
        color="importance",
        color_continuous_scale="Purples",
        title=f"Top {top_n} Feature Importances (XGBoost)",
        labels={"importance": "Importance Score", "feature": ""},
    )
    fig.update_coloraxes(showscale=False)
    fig.update_layout(margin=dict(t=40, b=0, l=0, r=0))
    return fig


# ── 9. CONFUSION MATRIX ───────────────────────────────────────────────
def chart_confusion_matrix(conf_mat: list) -> go.Figure:
    labels = ["Not Top-K", "Top-K"]
    z      = conf_mat
    text   = [[f"TN={z[0][0]}", f"FP={z[0][1]}"],
               [f"FN={z[1][0]}", f"TP={z[1][1]}"]]

    fig = go.Figure(go.Heatmap(
        z=z, x=labels, y=labels,
        text=text, texttemplate="%{text}",
        colorscale="Blues",
        showscale=False,
    ))
    fig.update_layout(
        title="Confusion Matrix",
        xaxis_title="Predicted",
        yaxis_title="Actual",
        margin=dict(t=40, b=0, l=0, r=0),
    )
    return fig


# ── 10. ASSOCIATION RULES SCATTER ─────────────────────────────────────
def chart_association_rules(df_rules: pd.DataFrame) -> go.Figure:
    topk_mask = df_rules["consequents"].str.contains("topk:1", na=False)
    df_rules  = df_rules.copy()
    df_rules["type"] = topk_mask.map({True: "→ topk:1", False: "other"})

    fig = px.scatter(
        df_rules.head(200),
        x="support", y="confidence",
        size="lift", color="type",
        color_discrete_map={"→ topk:1": COLORS["success"], "other": COLORS["muted"]},
        hover_data=["antecedents", "consequents", "lift"],
        title="Association Rules — Support vs Confidence (size = lift)",
        labels={"support": "Support", "confidence": "Confidence"},
        opacity=0.75,
    )
    fig.update_layout(margin=dict(t=40, b=0, l=0, r=0), legend_title="Rule type")
    return fig


# ── 11. DISCOUNT DISTRIBUTION BY SEGMENT ──────────────────────────────
def chart_discount_by_segment(df: pd.DataFrame) -> go.Figure:
    fig = px.box(
        df[df["discount_pct"] > 0],
        x="price_segment", y="discount_pct",
        color="price_segment",
        color_discrete_map=SEGMENT_COLORS,
        title="Discount % by Price Segment (promo products only)",
        labels={"discount_pct": "Discount %", "price_segment": "Segment"},
        points="outliers",
    )
    fig.update_layout(showlegend=False, margin=dict(t=40, b=0, l=0, r=0))
    return fig


# ── 12. POPULARITY SCORE DISTRIBUTION ────────────────────────────────
def chart_popularity_distribution(df: pd.DataFrame) -> go.Figure:
    fig = make_subplots(rows=1, cols=2, subplot_titles=("All Products", "Top-K vs Rest"))

    fig.add_trace(go.Histogram(
        x=df["popularity_score"], nbinsx=40,
        marker_color=COLORS["primary"], name="All",
        showlegend=False,
    ), row=1, col=1)

    for label, color, name in [(1, COLORS["success"], "Top-K"), (0, COLORS["muted"], "Rest")]:
        fig.add_trace(go.Histogram(
            x=df[df["topk_label"] == label]["popularity_score"],
            nbinsx=30, name=name,
            marker_color=color, opacity=0.7,
        ), row=1, col=2)

    fig.update_layout(
        title_text="Popularity Score Distribution",
        barmode="overlay",
        margin=dict(t=60, b=0, l=0, r=0),
    )
    return fig
