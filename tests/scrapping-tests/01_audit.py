"""
Script 1 — Dataset Audit
Runs on products.csv and variants.csv
Outputs: console report + audit_report.json
"""
import pandas as pd
import numpy as np
import json
from pathlib import Path

# PRODUCTS_PATH = "data/processed/products.csv"
# VARIANTS_PATH = "data/processed/variants.csv"
PRODUCTS_PATH = "data/raw/products.csv"
VARIANTS_PATH = "data/raw/variants.csv"

# ── LOAD ──────────────────────────────────────────────────────────────
df = pd.read_csv(PRODUCTS_PATH)
dv = pd.read_csv(VARIANTS_PATH)

report = {}

# ── 1. BASIC COUNTS ───────────────────────────────────────────────────
print("\n" + "="*60)
print("  DATASET AUDIT REPORT")
print("="*60)

print(f"\n[1] BASIC COUNTS")
print(f"  Total products       : {len(df)}")
print(f"  Total variants       : {len(dv)}")
print(f"  Unique sources       : {df['source_store'].nunique()} → {df['source_store'].unique().tolist()}")
print(f"  Unique categories    : {df['category'].nunique()}")
print(f"  Unique brands        : {df['brand'].nunique()}")

report["total_products"] = len(df)
report["total_variants"] = len(dv)
report["sources"] = df["source_store"].value_counts().to_dict()

# ── 2. MISSING VALUES ─────────────────────────────────────────────────
print(f"\n[2] MISSING VALUES")
missing = df.isnull().sum()
missing_pct = (df.isnull().sum() / len(df) * 100).round(1)
missing_df = pd.DataFrame({
    "missing_count": missing,
    "missing_%": missing_pct
}).query("missing_count > 0").sort_values("missing_%", ascending=False)

if missing_df.empty:
    print("  No missing values found.")
else:
    print(missing_df.to_string())

report["missing_values"] = missing_df["missing_count"].to_dict()

# ── 3. ZERO / EMPTY VALUES ────────────────────────────────────────────
print(f"\n[3] ZERO / EMPTY VALUES (not null but useless)")
zero_checks = {
    "price == 0":           (df["price"] == 0).sum(),
    "price_original == 0":  (df["price_original"] == 0).sum(),
    "discount_pct == 0":    (df["discount_pct"] == 0).sum(),
    "review_count == 0":    (df["review_count"] == 0).sum() if "review_count" in df else "N/A",
    "stock_qty == 0":       (df["stock_qty"] == 0).sum() if "stock_qty" in df else "N/A",
    "description empty":    (df["description"].fillna("").str.strip() == "").sum(),
    "category uncategorized": (df["category"] == "uncategorized").sum(),
    "brand unknown":        (df["brand"] == "unknown").sum(),
}
for k, v in zero_checks.items():
    flag = " ⚠" if isinstance(v, int) and v > 0 else ""
    print(f"  {k:<30} : {v}{flag}")

report["zero_empty"] = {k: int(v) if isinstance(v, int) else v for k, v in zero_checks.items()}

# ── 4. DISTRIBUTION BY SOURCE ─────────────────────────────────────────
print(f"\n[4] PRODUCTS BY SOURCE STORE")
source_counts = df["source_store"].value_counts()
for store, count in source_counts.items():
    bar = "█" * (count // 10)
    print(f"  {store:<20} : {count:>4}  {bar}")

# ── 5. PRICE ANALYSIS ─────────────────────────────────────────────────
print(f"\n[5] PRICE DISTRIBUTION")
price_stats = df["price"].describe().round(2)
print(price_stats.to_string())

print(f"\n  price_segment breakdown:")
if "price_segment" in df.columns:
    seg = df["price_segment"].value_counts()
    for s, c in seg.items():
        print(f"    {s:<10} : {c} products ({c/len(df)*100:.1f}%)")

# ── 6. RATING COVERAGE ────────────────────────────────────────────────
print(f"\n[6] RATING COVERAGE")
has_rating = df["rating"].notna().sum()
no_rating  = df["rating"].isna().sum()
print(f"  Has rating           : {has_rating} ({has_rating/len(df)*100:.1f}%)")
print(f"  Missing rating       : {no_rating}  ({no_rating/len(df)*100:.1f}%)")
if has_rating > 0:
    print(f"  Rating range         : {df['rating'].min():.1f} → {df['rating'].max():.1f}")
    print(f"  Mean rating          : {df['rating'].mean():.2f}")

# ── 7. STOCK COVERAGE ─────────────────────────────────────────────────
print(f"\n[7] STOCK COVERAGE")
print(f"  in_stock = True      : {df['in_stock'].sum()}")
print(f"  in_stock = False     : {(~df['in_stock'].astype(bool)).sum()}")
if "stock_qty" in df.columns:
    has_qty = df["stock_qty"].notna().sum()
    print(f"  Has stock_qty        : {has_qty} ({has_qty/len(df)*100:.1f}%)")

# ── 8. DUPLICATE CHECK ────────────────────────────────────────────────
print(f"\n[8] DUPLICATES")
dup_ids  = df["product_id"].duplicated().sum()
dup_name = df["name"].duplicated().sum()
print(f"  Duplicate product_id : {dup_ids}")
print(f"  Duplicate names      : {dup_name}")

# ── 9. READINESS SCORE ────────────────────────────────────────────────
print(f"\n[9] ML READINESS SCORE")
checks = {
    "≥ 2000 products":       len(df) >= 2000,
    "price coverage 100%":   (df["price"] > 0).all(),
    "category coverage >90%": (df["category"] != "uncategorized").mean() > 0.9,
    "brand coverage >80%":   (df["brand"] != "unknown").mean() > 0.8,
    "rating coverage >30%":  df["rating"].notna().mean() > 0.3,
    "no duplicate IDs":      dup_ids == 0,
    "price_segment present": "price_segment" in df.columns and df["price_segment"].notna().all(),
}
score = sum(checks.values())
for check, passed in checks.items():
    status = "✓" if passed else "✗"
    print(f"  [{status}] {check}")

print(f"\n  SCORE: {score}/{len(checks)}", end="")
if score == len(checks):
    print("  → Ready for ML pipeline ✓")
elif score >= 5:
    print("  → Minor fixes needed before ML")
else:
    print("  → Significant enrichment required")

print("\n" + "="*60)

# ── SAVE JSON REPORT ──────────────────────────────────────────────────
report["ml_readiness"] = {"score": score, "total": len(checks), "checks": checks}
Path("data/processed").mkdir(parents=True, exist_ok=True)
with open("data/processed/audit_report.json", "w") as f:
    json.dump(report, f, indent=2, default=str)
print("  Saved → data/processed/audit_report.json\n")
