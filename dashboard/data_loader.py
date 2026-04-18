"""
dashboard/data_loader.py
Single source of truth — loads all data/output files once.
Every page imports from here. Nothing else reads files directly.
"""
import os
import pandas as pd
import json
import pickle
from pathlib import Path
from functools import lru_cache

# ── PATHS ─────────────────────────────────────────────────────────
BASE_DATA_PATH = Path(os.getenv("DATA_PATH", "/app/data"))
PROCESSED = BASE_DATA_PATH / "processed"
OUTPUT = BASE_DATA_PATH / "output"

BASE_DATA_PATH.mkdir(parents=True, exist_ok=True)
PROCESSED.mkdir(parents=True, exist_ok=True)
OUTPUT.mkdir(parents=True, exist_ok=True)


# ── PRODUCTS (main dataset) ────────────────────────────────────────────
@lru_cache(maxsize=1)
def load_products() -> pd.DataFrame:
    df = pd.read_csv(PROCESSED / "products.csv")
    df["in_stock"]    = df["in_stock"].astype(bool)
    df["is_on_promo"] = df["is_on_promo"].astype(bool)
    df["topk_label"]  = df["topk_label"].astype(int)
    return df


# ── TOP-K PRODUCTS ─────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def load_topk(k: int = 100) -> pd.DataFrame:
    df = load_products()
    clusters = load_clusters()
    df = df.merge(clusters[["product_id", "segment", "is_anomaly"]], on="product_id", how="left")
    topk = (
        df[df["topk_label"] == 1]
        .sort_values("popularity_score", ascending=False)
        .head(k)
        .reset_index(drop=True)
    )
    topk.insert(0, "rank", range(1, len(topk) + 1))
    return topk


# ── CLUSTERS ───────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def load_clusters() -> pd.DataFrame:
    return pd.read_csv(OUTPUT / "clusters.csv")


# ── PCA 2D ─────────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def load_pca() -> pd.DataFrame:
    return pd.read_csv(OUTPUT / "pca_2d.csv")


# ── ANOMALIES ──────────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def load_anomalies() -> pd.DataFrame:
    return pd.read_csv(OUTPUT / "anomalies.csv")


# ── FEATURE IMPORTANCE ─────────────────────────────────────────────────
@lru_cache(maxsize=1)
def load_feature_importance() -> pd.DataFrame:
    return pd.read_csv(OUTPUT / "feature_importance.csv")


# ── ASSOCIATION RULES ──────────────────────────────────────────────────
@lru_cache(maxsize=1)
def load_association_rules() -> pd.DataFrame:
    df = pd.read_csv(OUTPUT / "association_rules.csv")
    df = df.round(4)
    return df


# ── JSON RESULTS ───────────────────────────────────────────────────────
@lru_cache(maxsize=1)
def load_xgboost_results() -> dict:
    with open(OUTPUT / "xgboost_results.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_clustering_results() -> dict:
    with open(OUTPUT / "clustering_results.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_evaluation_report() -> dict:
    with open(OUTPUT / "evaluation_report.json") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def load_source_quality() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "source_quality_report.csv")


# ── COMPUTED KPIs (derived, not stored) ────────────────────────────────
def get_kpis() -> dict:
    df    = load_products()
    xgb   = load_xgboost_results()
    clust = load_clustering_results()

    return {
        "total_products":    len(df),
        "topk_count":        int(df["topk_label"].sum()),
        "topk_pct":          round(df["topk_label"].mean() * 100, 1),
        "avg_rating":        round(df["rating"].mean(), 2),
        "avg_price":         round(df["price"].mean(), 2),
        "in_stock_pct":      round(df["in_stock"].mean() * 100, 1),
        "on_promo_pct":      round(df["is_on_promo"].mean() * 100, 1),
        "n_categories":      df["category"].nunique(),
        "n_brands":          df["brand"].nunique(),
        "n_sources":         df["source_store"].nunique(),
        "xgb_roc_auc":       xgb["roc_auc"],
        "xgb_accuracy":      xgb["accuracy"],
        "silhouette":        clust["kmeans"]["silhouette_score"],
        "n_anomalies":       clust["dbscan"]["n_anomalies"],
    }
