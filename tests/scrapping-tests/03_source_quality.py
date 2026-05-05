"""
Script 3 — Per-Source Quality Breakdown
Input  : data/processed/products_raw.csv
Output : console report + data/processed/source_quality_report.csv
"""
import pandas as pd
import numpy as np
from pathlib import Path

PRODUCTS_PATH = "data/raw/products.csv"

df = pd.read_csv(PRODUCTS_PATH)

# ── COLUMNS TO AUDIT PER SOURCE ───────────────────────────────────────
CRITICAL_COLS   = ["price", "category", "brand", "name"]
ENRICHABLE_COLS = ["rating", "review_count", "stock_qty", "description", "days_since_publish"]
ALL_COLS        = CRITICAL_COLS + ENRICHABLE_COLS

SOURCES = df["source_store"].unique()

rows = []
for source in SOURCES:
    sub = df[df["source_store"] == source]
    n   = len(sub)

    row = {"source": source, "total_products": n}

    # Missing % per column
    for col in ALL_COLS:
        if col in sub.columns:
            missing = sub[col].isna().sum()
            # also count empty strings and zeros for specific cols
            if col == "description":
                missing += (sub[col].fillna("").str.strip() == "").sum() - sub[col].isna().sum()
                missing  = max(missing, 0)
            if col in ["price"]:
                missing += (sub[col].fillna(0) == 0).sum() - sub[col].isna().sum()
                missing  = max(missing, 0)
            row[f"{col}_missing_%"] = round(missing / n * 100, 1)
        else:
            row[f"{col}_missing_%"] = 100.0

    # Duplicates within source
    row["dup_names"]     = int(sub["name"].duplicated().sum())
    row["dup_ids"]       = int(sub["product_id"].duplicated().sum())

    # Price issues
    row["price_zero"]    = int((sub["price"].fillna(0) == 0).sum())
    row["on_promo_%"]    = round((sub["discount_pct"].fillna(0) > 0).mean() * 100, 1) if "discount_pct" in sub else 0

    # Rating & review real vs null
    row["has_real_rating"]  = sub["rating"].notna().sum() > 0
    row["in_stock_%"]       = round(sub["in_stock"].astype(bool).mean() * 100, 1) if "in_stock" in sub else "N/A"

    # Compute a DATA QUALITY SCORE (0–100)
    penalties = 0
    # Critical fields missing = heavy penalty
    for col in CRITICAL_COLS:
        penalties += row[f"{col}_missing_%"] * 2      # weight x2
    # Enrichable fields missing = lighter penalty
    for col in ENRICHABLE_COLS:
        penalties += row[f"{col}_missing_%"] * 0.5    # weight x0.5
    # Duplicates
    penalties += (row["dup_ids"] / n * 100) * 3
    penalties += (row["dup_names"] / n * 100) * 1
    # Price zeros
    penalties += (row["price_zero"] / n * 100) * 3

    # Normalize to 0–100 (max theoretical penalty ≈ 700)
    raw_score = max(0, 100 - penalties / 7)
    row["quality_score"] = round(raw_score, 1)

    # Recommendation
    if raw_score >= 75:
        row["recommendation"] = "KEEP ✓"
    elif raw_score >= 50:
        row["recommendation"] = "KEEP + ENRICH ⚠"
    elif raw_score >= 30:
        row["recommendation"] = "PARTIAL USE ⚠⚠"
    else:
        row["recommendation"] = "CONSIDER DROP ✗"

    rows.append(row)

report_df = pd.DataFrame(rows).sort_values("quality_score", ascending=False)

# ── PRINT REPORT ──────────────────────────────────────────────────────
print("\n" + "="*80)
print("  PER-SOURCE DATA QUALITY REPORT")
print("="*80)

# Summary table
print(f"\n{'Source':<18} {'Products':>8} {'Score':>7} {'Recommendation':<22} {'Price∅':>6} {'Cat∅%':>6} {'Brand∅%':>7} {'Rating∅%':>9} {'Desc∅%':>7}")
print("-"*90)
for _, r in report_df.iterrows():
    print(
        f"{r['source']:<18} "
        f"{r['total_products']:>8} "
        f"{r['quality_score']:>7.1f} "
        f"{r['recommendation']:<22} "
        f"{r['price_zero']:>6} "
        f"{r['category_missing_%']:>6.1f} "
        f"{r['brand_missing_%']:>7.1f} "
        f"{r['rating_missing_%']:>9.1f} "
        f"{r['description_missing_%']:>7.1f}"
    )

# ── DETAIL PER SOURCE ─────────────────────────────────────────────────
print(f"\n{'='*80}")
print("  DETAIL BY SOURCE")
print("="*80)

for _, r in report_df.iterrows():
    score = r["quality_score"]
    bar   = "█" * int(score // 5) + "░" * (20 - int(score // 5))
    print(f"\n  [{r['source'].upper()}]  {bar}  {score}/100  →  {r['recommendation']}")
    print(f"    Products       : {r['total_products']}")
    print(f"    In-stock       : {r['in_stock_%']}%")
    print(f"    On promo       : {r['on_promo_%']}%")
    print(f"    Duplicates     : {r['dup_ids']} IDs  |  {r['dup_names']} names")
    print(f"    ── Missing fields ──────────────────────────────")
    for col in ALL_COLS:
        pct = r[f"{col}_missing_%"]
        flag = ""
        if col in CRITICAL_COLS and pct > 20:
            flag = " ← CRITICAL"
        elif col in ENRICHABLE_COLS and pct > 80:
            flag = " ← needs enrichment"
        bar2 = "▓" * int(pct // 10) + "·" * (10 - int(pct // 10))
        print(f"    {col:<22} [{bar2}] {pct:>5.1f}%{flag}")

# ── REMOVAL CANDIDATES ────────────────────────────────────────────────
print(f"\n{'='*80}")
print("  REMOVAL CANDIDATES")
print("="*80)
bad = report_df[report_df["quality_score"] < 30]
if bad.empty:
    print("  No sources recommended for removal.")
else:
    for _, r in bad.iterrows():
        print(f"  ✗  {r['source']:<18}  score={r['quality_score']}  products={r['total_products']}")
        print(f"     Reason: check critical field missing rates above")

# ── DATASET IMPACT IF REMOVED ─────────────────────────────────────────
print(f"\n{'='*80}")
print("  DATASET IMPACT ANALYSIS (if low-quality sources removed)")
print("="*80)
total = len(df)
kept_sources = report_df[report_df["quality_score"] >= 30]["source"].tolist()
kept_n = df[df["source_store"].isin(kept_sources)].shape[0]
print(f"  Keeping {len(kept_sources)} sources ({', '.join(kept_sources)})")
print(f"  Rows kept    : {kept_n} / {total}  ({kept_n/total*100:.1f}%)")
print(f"  Rows removed : {total - kept_n}")
if kept_n < 2000:
    print(f"  ⚠  WARNING: only {kept_n} rows remaining — below 2000 minimum for ML")
else:
    print(f"  ✓  {kept_n} rows is sufficient for full ML pipeline")

# ── SAVE ──────────────────────────────────────────────────────────────
Path("data/processed").mkdir(parents=True, exist_ok=True)
report_df.to_csv("data/processed/source_quality_report.csv", index=False)
print(f"\n  Saved → data/processed/source_quality_report.csv\n")
print("="*80)
