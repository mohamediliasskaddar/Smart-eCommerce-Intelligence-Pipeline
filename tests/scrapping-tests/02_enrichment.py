"""
Script 2 — Enrichment & Missing Data Handler
Input  : data/processed/products_raw.csv
Output : data/processed/products_clean.csv
"""
import pandas as pd
import numpy as np
import re, html
from pathlib import Path

PRODUCTS_PATH = "data/processed/products_raw.csv"
OUTPUT_PATH   = "data/processed/products_clean.csv"

df = pd.read_csv(PRODUCTS_PATH)
print(f"Loaded {len(df)} products from {PRODUCTS_PATH}")

# ═══════════════════════════════════════════════════════════════════════
# STEP 1 — DEDUPLICATE
# ═══════════════════════════════════════════════════════════════════════
before = len(df)
df = df.drop_duplicates(subset=["product_id", "source_store"])
df = df.drop_duplicates(subset=["name", "brand", "price"])
print(f"[1] Deduplication     : removed {before - len(df)} rows → {len(df)} remaining")

# ═══════════════════════════════════════════════════════════════════════
# STEP 2 — PRICE FIXES
# ═══════════════════════════════════════════════════════════════════════
# Remove rows where price is 0 or null (unusable for ML)
before = len(df)
df = df[df["price"].notna() & (df["price"] > 0)]
print(f"[2] Price filter      : removed {before - len(df)} zero/null price rows")

# Fix price_original: if missing or < price, set = price (no discount)
df["price_original"] = df.apply(
    lambda r: r["price"] if pd.isna(r["price_original"]) or r["price_original"] < r["price"]
    else r["price_original"],
    axis=1
)

# Recompute discount_pct from actual prices (source of truth)
df["discount_pct"] = df.apply(
    lambda r: round((r["price_original"] - r["price"]) / r["price_original"] * 100, 1)
    if r["price_original"] > r["price"] else 0.0,
    axis=1
)

# ═══════════════════════════════════════════════════════════════════════
# STEP 3 — CATEGORY CLEANING
# ═══════════════════════════════════════════════════════════════════════
# Normalize category: lowercase, strip, handle empties
df["category"] = df["category"].fillna("uncategorized").str.strip()
df["category"] = df["category"].replace({"": "uncategorized", " ": "uncategorized"})

# Clean Shopify product_type junk like "Hubs ## Stands" → "Hubs"
df["category"] = df["category"].str.split("##").str[0].str.strip()
df["category"] = df["category"].str.split("/").str[0].str.strip()   # "Sportswear/Accessories/" → "Sportswear"
df["category"] = df["category"].str.lower()

# Manual category normalization map (extend as needed)
CATEGORY_MAP = {
    "womens shorts": "apparel",
    "mens clothing": "apparel",
    "bottoms": "apparel",
    "shoes": "footwear",
    "phone case": "accessories",
    "hubs": "electronics",
    "sample": "other",
    "sportswear": "fitness",
    "": "uncategorized",
}
df["category"] = df["category"].map(lambda x: CATEGORY_MAP.get(x, x))

print(f"[3] Category cleaning : {df['category'].nunique()} unique categories")

# ═══════════════════════════════════════════════════════════════════════
# STEP 4 — BRAND CLEANING
# ═══════════════════════════════════════════════════════════════════════
df["brand"] = df["brand"].fillna("unknown").str.strip()
df["brand"] = df["brand"].replace({"": "unknown"})

# Gymshark vendor comes as "Gymshark | Be a visionary." → clean it
df["brand"] = df["brand"].str.split("|").str[0].str.strip()
df["brand"] = df["brand"].str.split("®").str[0].str.strip()

print(f"[4] Brand cleaning    : {df['brand'].nunique()} unique brands")

# ═══════════════════════════════════════════════════════════════════════
# STEP 5 — DESCRIPTION CLEANING
# ═══════════════════════════════════════════════════════════════════════
def clean_html(raw):
    if not raw or pd.isna(raw):
        return ""
    decoded   = html.unescape(str(raw))
    no_tags   = re.sub(r"<[^>]+>", " ", decoded)
    collapsed = re.sub(r"\s+", " ", no_tags).strip()
    return collapsed[:1000]   # cap for LLM token budget

df["description"] = df["description"].apply(clean_html)
missing_desc = (df["description"] == "").sum()
print(f"[5] Description clean : {missing_desc} products have empty description")

# ═══════════════════════════════════════════════════════════════════════
# STEP 6 — RATING & REVIEW ENRICHMENT (synthetic for Shopify sources)
# ═══════════════════════════════════════════════════════════════════════
# Strategy: calibrate synthetic distribution on dummyjson real values
# dummyjson observed: rating mean=3.9 std=0.8, reviews log-normal

np.random.seed(42)   # reproducible

shopify_mask = df["rating"].isna()
n = shopify_mask.sum()

if n > 0:
    # Rating: normal distribution calibrated on real ecommerce data
    synthetic_ratings = np.clip(np.random.normal(3.9, 0.7, n), 1.0, 5.0).round(1)

    # Review count: log-normal → most products have 10-500 reviews
    # mean=4.5, std=1.2 → geometric mean ≈ 90 reviews
    synthetic_reviews = np.random.lognormal(mean=4.5, sigma=1.2, size=n).astype(int)
    synthetic_reviews = np.clip(synthetic_reviews, 1, 10000)

    df.loc[shopify_mask, "rating"]       = synthetic_ratings
    df.loc[shopify_mask, "review_count"] = synthetic_reviews

    print(f"[6] Rating enrichment : {n} Shopify products enriched with synthetic ratings")
    print(f"    Synthetic rating   : mean={synthetic_ratings.mean():.2f} std={synthetic_ratings.std():.2f}")
    print(f"    Synthetic reviews  : mean={synthetic_reviews.mean():.0f} median={int(np.median(synthetic_reviews))}")
else:
    print("[6] Rating enrichment : all products already have ratings")

# Ensure types
df["rating"]       = df["rating"].round(1)
df["review_count"] = df["review_count"].fillna(0).astype(int)

# ═══════════════════════════════════════════════════════════════════════
# STEP 7 — STOCK QTY ENRICHMENT
# ═══════════════════════════════════════════════════════════════════════
# Shopify doesn't provide stock_qty → infer from in_stock
stock_mask = df["stock_qty"].isna()
n_stock = stock_mask.sum()

if n_stock > 0:
    # In-stock products: gamma distribution (most have 10-200 units)
    in_stock_vals  = df.loc[stock_mask & df["in_stock"].astype(bool)]
    out_stock_vals = df.loc[stock_mask & ~df["in_stock"].astype(bool)]

    df.loc[in_stock_vals.index, "stock_qty"] = (
        np.random.gamma(shape=2.5, scale=40, size=len(in_stock_vals)).astype(int)
    )
    df.loc[out_stock_vals.index, "stock_qty"] = 0

    print(f"[7] Stock enrichment  : {n_stock} products filled (in_stock→gamma, out→0)")

df["stock_qty"] = df["stock_qty"].fillna(0).astype(int)

# ═══════════════════════════════════════════════════════════════════════
# STEP 8 — DAYS SINCE PUBLISH
# ═══════════════════════════════════════════════════════════════════════
# Fill missing with median of same source_store
if "days_since_publish" in df.columns:
    median_days = df.groupby("source_store")["days_since_publish"].transform("median")
    df["days_since_publish"] = df["days_since_publish"].fillna(median_days).fillna(365)
    df["days_since_publish"] = df["days_since_publish"].astype(int)
    print(f"[8] Days enrichment   : filled with per-store median")

# ═══════════════════════════════════════════════════════════════════════
# STEP 9 — RECOMPUTE ENGINEERED COLUMNS
# ═══════════════════════════════════════════════════════════════════════
# is_on_promo
df["is_on_promo"] = df["discount_pct"] > 0

# price_segment (fixed thresholds — document in rapport)
df["price_segment"] = pd.cut(
    df["price"],
    bins=[0, 30, 100, float("inf")],
    labels=["low", "mid", "high"]
).astype(str)

seg_counts = df["price_segment"].value_counts()
print(f"[9] Price segments    : low={seg_counts.get('low',0)} mid={seg_counts.get('mid',0)} high={seg_counts.get('high',0)}")

# ═══════════════════════════════════════════════════════════════════════
# STEP 10 — POPULARITY SCORE & TOP-K LABEL
# ═══════════════════════════════════════════════════════════════════════
# popularity_score = weighted formula
log_reviews = np.log1p(df["review_count"])
rank_inv    = 1 / (df["review_count"].rank(ascending=False, method="min") + 1)

df["popularity_score"] = (
    df["rating"]  * 0.4 +
    log_reviews   * 0.4 +
    rank_inv      * 0.2
).round(3)

# topk_label: top 20% by popularity_score = 1
threshold = df["popularity_score"].quantile(0.80)
df["topk_label"] = (df["popularity_score"] >= threshold).astype(int)

topk_count = df["topk_label"].sum()
print(f"[10] Top-K label      : {topk_count} products labeled 1 (top 20%) threshold={threshold:.3f}")

# ═══════════════════════════════════════════════════════════════════════
# STEP 11 — FINAL TYPE ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════════
df["price"]          = df["price"].round(2)
df["price_original"] = df["price_original"].round(2)
df["discount_pct"]   = df["discount_pct"].round(1)
df["rating"]         = df["rating"].round(1)
df["in_stock"]       = df["in_stock"].astype(bool)
df["is_on_promo"]    = df["is_on_promo"].astype(bool)
df["topk_label"]     = df["topk_label"].astype(int)

# ═══════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "="*60)
print("  ENRICHMENT COMPLETE")
print("="*60)
print(f"  Final row count      : {len(df)}")
print(f"  Null values left     : {df.isnull().sum().sum()}")
print(f"  Rating coverage      : 100% (enriched)")
print(f"  Columns              : {list(df.columns)}")

# Save
Path("data/processed").mkdir(parents=True, exist_ok=True)
df.to_csv(OUTPUT_PATH, index=False)
print(f"\n  Saved → {OUTPUT_PATH}\n")
