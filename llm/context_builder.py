"""
llm/context_builder.py
Prepares compact, token-efficient context from data files.
Nothing else in the LLM module reads data directly — everything goes through here.
"""
import json
import pandas as pd
from pathlib import Path
from functools import lru_cache

ROOT      = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
OUTPUT    = ROOT / "data" / "output"


# ── LOADERS (cached) ───────────────────────────────────────────────────
@lru_cache(maxsize=1)
def _products() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "products.csv")

@lru_cache(maxsize=1)
def _topk() -> pd.DataFrame:
    df = _products()
    return df[df["topk_label"] == 1].sort_values("popularity_score", ascending=False)

@lru_cache(maxsize=1)
def _xgb_results() -> dict:
    with open(OUTPUT / "xgboost_results.json") as f:
        return json.load(f)

@lru_cache(maxsize=1)
def _clustering_results() -> dict:
    with open(OUTPUT / "clustering_results.json") as f:
        return json.load(f)

@lru_cache(maxsize=1)
def _association_rules() -> pd.DataFrame:
    return pd.read_csv(OUTPUT / "association_rules.csv")

@lru_cache(maxsize=1)
def _anomalies() -> pd.DataFrame:
    return pd.read_csv(OUTPUT / "anomalies.csv")

@lru_cache(maxsize=1)
def _feature_importance() -> pd.DataFrame:
    return pd.read_csv(OUTPUT / "feature_importance.csv")


# ══════════════════════════════════════════════════════════════════════
# PUBLIC CONTEXT BUILDERS
# Each returns a compact string — only what the prompt needs.
# ══════════════════════════════════════════════════════════════════════

def context_topk(n: int = 20) -> str:
    """Top-N products as compact JSON for summarization chains."""
    df = _topk().head(n)
    cols = ["name", "brand", "category", "price", "rating",
            "review_count", "discount_pct", "source_store", "popularity_score"]
    cols = [c for c in cols if c in df.columns]
    records = df[cols].round(2).to_dict("records")
    return json.dumps(records, indent=2)


def context_dataset_stats() -> str:
    """Aggregated dataset statistics — for strategy/overview questions."""
    df = _products()
    xgb = _xgb_results()
    clust = _clustering_results()

    stats = {
        "total_products":    len(df),
        "sources":           df["source_store"].value_counts().to_dict(),
        "categories":        df["category"].value_counts().head(8).to_dict(),
        "price_segments":    df["price_segment"].value_counts().to_dict(),
        "avg_price":         round(df["price"].mean(), 2),
        "avg_rating":        round(df["rating"].mean(), 2),
        "in_stock_pct":      round(df["in_stock"].astype(bool).mean() * 100, 1),
        "on_promo_pct":      round(df["is_on_promo"].astype(bool).mean() * 100, 1),
        "topk_count":        int(df["topk_label"].sum()),
        "topk_pct":          round(df["topk_label"].mean() * 100, 1),
        "xgboost": {
            "roc_auc":       xgb["roc_auc"],
            "accuracy":      xgb["accuracy"],
            "f1_score":      xgb["f1_score"],
            "top_features":  xgb["top_features"][:5],
        },
        "clustering": {
            "silhouette":    clust["kmeans"]["silhouette_score"],
            "n_anomalies":   clust["dbscan"]["n_anomalies"],
        }
    }
    return json.dumps(stats, indent=2)


def context_product(product_id: str) -> str:
    """Single product context for enrichment."""
    df = _products()
    row = df[df["product_id"].astype(str) == str(product_id)]
    if row.empty:
        return f"Product {product_id} not found."
    cols = ["name", "description", "category", "brand", "price",
            "discount_pct", "rating", "review_count", "in_stock",
            "stock_qty", "source_store", "popularity_score"]
    cols = [c for c in cols if c in row.columns]
    return json.dumps(row[cols].iloc[0].to_dict(), indent=2)


def context_association_rules(topk_only: bool = True, n: int = 15) -> str:
    """Top association rules, optionally filtered to topk:1 consequents."""
    rules = _association_rules()
    if topk_only:
        rules = rules[rules["consequents"].str.contains("topk:1", na=False)]
    rules = rules.sort_values("lift", ascending=False).head(n)
    cols = ["antecedents", "consequents", "support", "confidence", "lift"]
    cols = [c for c in cols if c in rules.columns]
    return rules[cols].round(3).to_string(index=False)


def context_anomalies() -> str:
    """Anomaly summary for analysis questions."""
    df = _anomalies()
    if df.empty:
        return "No anomalies detected."
    cols = ["name", "price", "discount_pct", "brand", "category", "source_store"]
    cols = [c for c in cols if c in df.columns]
    summary = {
        "count": len(df),
        "avg_price": round(df["price"].mean(), 2) if "price" in df else "N/A",
        "samples": df[cols].head(5).to_dict("records"),
    }
    return json.dumps(summary, indent=2)


def context_feature_importance() -> str:
    """Feature importance for ML explainability questions."""
    imp = _feature_importance().head(10)
    return imp.to_string(index=False)


def get_context_for_question(question: str) -> str:
    """
    Route a question to the most relevant context.
    Used by the conversational chain to pick context automatically.
    """
    q = question.lower()

    if any(w in q for w in ["top", "best", "popular", "rank", "recommend"]):
        return f"TOP-K PRODUCTS:\n{context_topk(20)}"

    if any(w in q for w in ["association", "rule", "together", "bundle", "basket"]):
        return f"ASSOCIATION RULES:\n{context_association_rules()}"

    if any(w in q for w in ["anomal", "unusual", "outlier", "weird", "strange"]):
        return f"ANOMALIES:\n{context_anomalies()}"

    if any(w in q for w in ["feature", "import", "xgboost", "model", "predict", "accuracy"]):
        return (f"FEATURE IMPORTANCE:\n{context_feature_importance()}\n\n"
                f"MODEL STATS:\n{context_dataset_stats()}")

    if any(w in q for w in ["strategy", "insight", "overview", "summary", "report",
                              "trend", "market", "competi"]):
        return f"DATASET STATISTICS:\n{context_dataset_stats()}"

    # Default: full stats
    return f"DATASET STATISTICS:\n{context_dataset_stats()}"
