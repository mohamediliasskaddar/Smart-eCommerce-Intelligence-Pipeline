"""
pipeline/models/association_rules.py
Module 2 — Step 4: Association Rules (Apriori / FP-Growth)
Input  : data/raw/variants.csv  +  data/processed/products.csv
Output : data/output/association_rules.csv
         data/output/association_results.json
"""
import pandas as pd
import json
from pathlib import Path
from mlxtend.frequent_patterns import fpgrowth, association_rules
from mlxtend.preprocessing import TransactionEncoder
import numpy as np

OUTPUT_DIR = Path("data/output")

# ── LOAD ──────────────────────────────────────────────────────────────
df_products = pd.read_csv("data/processed/products.csv")

print(f"Products : {len(df_products):,}")

# ── BUILD PRODUCT-LEVEL TRANSACTIONS ──────────────────────────────────
print("\nBuilding product-level transactions...")

transactions = []
for _, row in df_products.iterrows():
    items = []

    # Category
    cat = str(row.get("category", "")).strip().lower().replace(" ", "_")
    if cat and cat != "uncategorized":
        items.append(f"category:{cat}")

    # Price segment
    seg = str(row.get("price_segment", "")).strip()
    if seg:
        items.append(f"price:{seg}")

    # Store
    store = str(row.get("source_store", "")).strip()
    if store:
        items.append(f"store:{store}")

    # Country
    country = str(row.get("shop_country", "")).strip()
    if country and country != "unknown":
        items.append(f"country:{country}")

    # Promo
    if row.get("is_on_promo"):
        items.append("on_promo:yes")

    # Stock
    if row.get("in_stock"):
        items.append("in_stock:yes")

    # topk — only tag positives
    if row.get("topk_label") == 1:
        items.append("topk:1")

    if len(items) >= 2:
        transactions.append(items)

print(f"Total transactions (products) : {len(transactions)}")

# ── ENCODE ───────────────────────────────────────────────────────────
te = TransactionEncoder()
te_array = te.fit_transform(transactions)
df_te = pd.DataFrame(te_array, columns=te.columns_)

print(f"\nOne-hot matrix : {df_te.shape}")

# ═════════════════════════════════════════════════════════════════════
# FP-GROWTH — DUAL PASS
# ═════════════════════════════════════════════════════════════════════
print("\nRunning FP-Growth (dual pass)...")

MIN_SUPPORT    = 0.05
MIN_CONFIDENCE = 0.55
MIN_LIFT       = 1.5

MIN_SUPPORT_TOPK    = 0.01
MIN_CONFIDENCE_TOPK = 0.45
MIN_LIFT_TOPK       = 1.3
# ── PASS 1: General rules (exclude topk items entirely) ───────────────
print("Running FP-Growth pass 1 (general rules)...")

frequent_general = fpgrowth(df_te, min_support=0.05, use_colnames=True)
rules_general = association_rules(
    frequent_general, metric="confidence", min_threshold=0.55
)
rules_general = rules_general[rules_general["lift"] >= 1.5]

# Remove rules where topk:1 appears anywhere
rules_general = rules_general[
    ~rules_general["antecedents"].apply(lambda x: "topk:1" in x) &
    ~rules_general["consequents"].apply(lambda x: "topk:1" in x)
]

# Remove trivial store-category tautologies
rules_general = rules_general[rules_general["lift"] <= 15]  # lift>15 = likely tautology

print(f"  General rules: {len(rules_general)}")

# ── PASS 2: Topk rules only ────────────────────────────────────────────
print("Running FP-Growth pass 2 (topk:1 rules)...")

frequent_topk = fpgrowth(df_te, min_support=0.01, use_colnames=True)

# Generate rules with metric lift, filter to topk:1 consequents
all_topk_rules = association_rules(frequent_topk, metric="lift", min_threshold=1.2)
topk_rules = all_topk_rules[
    all_topk_rules["consequents"].apply(lambda x: x == frozenset({"topk:1"}))
].copy()

# Sort topk rules by lift descending
topk_rules = topk_rules.sort_values("lift", ascending=False)
print(f"  Topk rules found: {len(topk_rules)}")

if len(topk_rules) > 0:
    print("\n  Top 10 rules → topk:1:")
    for _, r in topk_rules.head(10).iterrows():
        ants = ", ".join(sorted(r["antecedents"]))
        print(f"    {{{ants}}} → topk:1  "
              f"conf={r['confidence']:.2f}  lift={r['lift']:.2f}  "
              f"support={r['support']:.3f}")

# ── MERGE + CLEAN ─────────────────────────────────────────────────────
rules_all = pd.concat([rules_general, topk_rules], ignore_index=True)
rules_all = rules_all.replace([np.inf, -np.inf], 999.0)
rules_all = rules_all.round(4)

# Convert frozensets to strings for CSV/JSON export
rules_all["antecedents"] = rules_all["antecedents"].apply(lambda x: ", ".join(sorted(x)))
rules_all["consequents"] = rules_all["consequents"].apply(lambda x: ", ".join(sorted(x)))

topk_mask = rules_all["consequents"] == "topk:1"
print(f"\nFinal — total rules : {len(rules_all)}")
print(f"Final — topk rules  : {topk_mask.sum()}")

# ── FORMAT FOR EXPORT ────────────────────────────────────────────────
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

rules_all.to_csv(OUTPUT_DIR / "association_rules.csv", index=False)

# Extract topk rules again (string format)
topk_rules_export = rules_all[rules_all["consequents"].str.contains("topk:1")]

results = {
    "min_support_main": 0.05,
    "min_support_topk": 0.01,
    "min_confidence_main": 0.55,
    "min_confidence_topk": 0.45,
    "min_lift_main": 1.5,
    "min_lift_topk": 1.3,
    "total_rules": len(rules_all),
    "topk_rules": len(topk_rules_export),
    "top_rules": rules_all.head(5).to_dict("records"),
}

with open(OUTPUT_DIR / "association_results.json", "w") as f:
    json.dump(results, f, indent=2)

print(f"\nSaved → data/output/association_rules.csv")
print(f"Saved → data/output/association_results.json\n")