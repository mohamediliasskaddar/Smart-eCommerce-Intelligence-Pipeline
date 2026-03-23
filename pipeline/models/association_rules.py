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

OUTPUT_DIR = Path("data/output")

# ── LOAD ──────────────────────────────────────────────────────────────
df_variants = pd.read_csv("data/raw/variants.csv")
df_products = pd.read_csv("data/processed/products.csv")

print(f"Variants : {len(df_variants):,}")
print(f"Products : {len(df_products):,}")

# ── MERGE PRODUCT INFO INTO VARIANTS ─────────────────────────────────
df = df_variants.merge(
    df_products[["product_id", "category", "price_segment",
                 "brand", "source_store", "topk_label"]],
    on="product_id",
    how="left"
)

# ══════════════════════════════════════════════════════════════════════
# BUILD TRANSACTIONS
# Each "transaction" = one product
# Each "item" = a meaningful attribute of that product
# Examples:
#   category:sportswear
#   price_segment:mid
#   size:M
#   color:black
#   topk:1
# ══════════════════════════════════════════════════════════════════════
print("\nBuilding transactions...")

def build_items(row) -> list:
    items = []

    # Category
    if pd.notna(row.get("category")):
        items.append(f"category:{str(row['category']).lower().replace(' ','_')}")

    # Price segment
    if pd.notna(row.get("price_segment")):
        items.append(f"price:{row['price_segment']}")

    # Brand (top brands only — avoid too many rare items)
    # Added at product level, not variant level

    # Source store
    if pd.notna(row.get("source_store")):
        items.append(f"store:{row['source_store']}")

    # Top-K label
    if pd.notna(row.get("topk_label")):
        items.append(f"topk:{int(row['topk_label'])}")

    # Variant option (size / color / material)
    option = str(row.get("option_value", "")).strip().lower()
    if option and option not in ("default title", "default", "nan", ""):
        # Classify option type
        sizes   = {"xs","s","m","l","xl","xxl","xxxl","xss","extra small",
                   "small","medium","large","extra large","one size"}
        colors  = {"black","white","grey","gray","blue","red","green",
                   "pink","navy","beige","brown","purple","yellow","orange"}
        numbers = set("0123456789")

        opt_lower = option.lower()
        if opt_lower in sizes or any(s in opt_lower for s in ["small","medium","large"]):
            items.append(f"size:{opt_lower}")
        elif opt_lower in colors or any(c in opt_lower for c in colors):
            items.append(f"color:{opt_lower}")
        elif opt_lower[0] in numbers:
            items.append(f"size_num:{opt_lower}")  # shoe sizes like "8", "9.5"
        else:
            items.append(f"variant:{opt_lower[:20]}")  # cap length

    return [i for i in items if i]  # remove empty

df["items"] = df.apply(build_items, axis=1)

# Group by product_id → one transaction per product
transactions = df.groupby("product_id")["items"].sum().apply(
    lambda x: list(set(x))  # deduplicate items per product
).tolist()

print(f"Total transactions (products): {len(transactions)}")
avg_items = sum(len(t) for t in transactions) / len(transactions)
print(f"Average items per transaction : {avg_items:.1f}")

# Filter out empty transactions
transactions = [t for t in transactions if len(t) >= 2]
print(f"Transactions with ≥2 items    : {len(transactions)}")

# ══════════════════════════════════════════════════════════════════════
# ENCODE → ONE-HOT MATRIX
# ══════════════════════════════════════════════════════════════════════
te = TransactionEncoder()
te_array = te.fit_transform(transactions)
df_te = pd.DataFrame(te_array, columns=te.columns_)
print(f"\nOne-hot matrix : {df_te.shape[0]} transactions × {df_te.shape[1]} items")

# ══════════════════════════════════════════════════════════════════════
# FP-GROWTH (faster than Apriori for large datasets)
# min_support = 0.02 → item appears in at least 2% of transactions
# ══════════════════════════════════════════════════════════════════════
print("\nRunning FP-Growth...")
MIN_SUPPORT    = 0.02
MIN_CONFIDENCE = 0.40
MIN_LIFT       = 1.2

frequent_items = fpgrowth(df_te, min_support=MIN_SUPPORT, use_colnames=True)
print(f"Frequent itemsets found : {len(frequent_items)}")

if len(frequent_items) == 0:
    print("⚠  No frequent itemsets — try lowering min_support")
else:
    rules = association_rules(
        frequent_items,
        metric="confidence",
        min_threshold=MIN_CONFIDENCE
    )
    rules = rules[rules["lift"] >= MIN_LIFT]
    rules = rules.sort_values("lift", ascending=False)

    print(f"Association rules found : {len(rules)}")
    print(f"\nTop 10 rules (by lift):")
    cols = ["antecedents","consequents","support","confidence","lift"]
    print(rules[cols].head(10).to_string(index=False))

    # ── SAVE ──────────────────────────────────────────────────────────
    # Convert frozensets to strings for CSV
    rules["antecedents"] = rules["antecedents"].apply(lambda x: ", ".join(sorted(x)))
    rules["consequents"] = rules["consequents"].apply(lambda x: ", ".join(sorted(x)))
    rules = rules.round(4)

    rules.to_csv(OUTPUT_DIR / "association_rules.csv", index=False)

    # Rules that lead to topk:1 specifically — these are the most valuable
    topk_rules = rules[rules["consequents"].str.contains("topk:1")]
    print(f"\nRules predicting top-k products : {len(topk_rules)}")
    if len(topk_rules) > 0:
        print(topk_rules[["antecedents","support","confidence","lift"]].head(10).to_string(index=False))

    results = {
        "min_support":          MIN_SUPPORT,
        "min_confidence":       MIN_CONFIDENCE,
        "min_lift":             MIN_LIFT,
        "frequent_itemsets":    len(frequent_items),
        "total_rules":          len(rules),
        "topk_rules":           len(topk_rules),
        "top_rules": rules[cols].head(5).assign(
            antecedents=rules["antecedents"].head(5),
            consequents=rules["consequents"].head(5),
        ).to_dict("records"),
    }
    with open(OUTPUT_DIR / "association_results.json", "w") as f:
        json.dump(results, f, indent=2, default=str)

    print(f"\n  Saved → data/output/association_rules.csv")
    print(f"  Saved → data/output/association_results.json\n")
