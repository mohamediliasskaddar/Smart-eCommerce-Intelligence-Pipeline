"""
pipeline/steps/evaluate.py
Module 2 — Step 5: Unified Evaluation Report
Input  : all data/output/*.json
Output : data/output/evaluation_report.json
console summary
"""

from storage import StorageManager, OUTPUT_PREFIX

storage = StorageManager()

# Safety check: verify at least some outputs exist before generating report
required_outputs = [
    ("xgboost_results.json", "XGBoost training"),
    ("clustering_results.json", "KMeans clustering"),
    ("association_results.json", "Association rules"),
]

missing = []
for fname, stage in required_outputs:
    if not storage.exists(fname, prefix=OUTPUT_PREFIX):
        missing.append(f"{stage} ({fname})")

if missing:
    print("\n⚠  WARNING: Missing analysis outputs:")
    for item in missing:
        print(f"   - {item}")
    print("   → Run pipeline steps: train.py, clustering.py, association_rules.py")

print("\n" + "="*60)
print("  MODULE 2 — EVALUATION REPORT")
print("="*60)

# ── LOAD ALL RESULTS VIA STORAGEMANAGER (no direct file access) ────────
xgb = storage.load_json("xgboost_results.json", prefix=OUTPUT_PREFIX) if storage.exists("xgboost_results.json", prefix=OUTPUT_PREFIX) else None
clust = storage.load_json("clustering_results.json", prefix=OUTPUT_PREFIX) if storage.exists("clustering_results.json", prefix=OUTPUT_PREFIX) else None
assoc = storage.load_json("association_results.json", prefix=OUTPUT_PREFIX) if storage.exists("association_results.json", prefix=OUTPUT_PREFIX) else None

report = {}

# ── XGBOOST ───────────────────────────────────────────────────────────
if xgb:
    print(f"\n[1] CLASSIFICATION — XGBoost")
    print(f"  Accuracy      : {xgb['accuracy']}")
    print(f"  F1 Score      : {xgb['f1_score']}")
    print(f"  ROC-AUC       : {xgb['roc_auc']}")
    print(f"  Top features  : {', '.join(xgb['top_features'])}")

    grade = (
        "EXCELLENT"  if xgb["roc_auc"] >= 0.90 else
        "GOOD"       if xgb["roc_auc"] >= 0.75 else
        "ACCEPTABLE" if xgb["roc_auc"] >= 0.60 else
        "NEEDS WORK"
    )
    print(f"  Grade         : {grade}  (ROC-AUC >= 0.80 = good for ecommerce)")
    report["xgboost"] = {**xgb, "grade": grade}

# ── CLUSTERING ────────────────────────────────────────────────────────
if clust:
    km = clust["kmeans"]
    db = clust["dbscan"]
    pc = clust["pca"]

    print(f"\n[2] CLUSTERING — KMeans (K={km['k']})")
    print(f"  Silhouette score : {km['silhouette_score']}")
    sil = km["silhouette_score"]

    sil_grade = (
        "WELL SEPARATED" if sil >= 0.5 else
        "ACCEPTABLE"     if sil >= 0.3 else
        "OVERLAPPING"
    )
    print(f"  Grade            : {sil_grade}  (≥0.5 = well separated clusters)")

    print(f"\n  DBSCAN Anomalies : {db['n_anomalies']} products ({db['anomaly_pct']}%)")
    anom_note = (
        "normal" if db["anomaly_pct"] < 5 else
        "check anomalies — may indicate data quality issues" if db["anomaly_pct"] > 15 else
        "acceptable"
    )
    print(f"  Note             : {anom_note}")

    print(f"\n  PCA variance explained : {pc['total_explained']:.1%}")
    print(f"  PC1={pc['explained_variance'][0]:.1%}  PC2={pc['explained_variance'][1]:.1%}")

    report["clustering"] = {
        "silhouette": sil,
        "silhouette_grade": sil_grade,
        "anomalies": db["n_anomalies"],
        "anomaly_pct": db["anomaly_pct"],
        "pca_variance": pc["total_explained"]
    }

# ── ASSOCIATION RULES ─────────────────────────────────────────────────
if assoc:
    print(f"\n[3] ASSOCIATION RULES — FP-Growth")

    # Robust handling of schema changes
    freq_main = assoc.get("frequent_itemsets")
    freq_main_alt = assoc.get("frequent_itemsets_main")
    freq_topk = assoc.get("frequent_itemsets_topk")

    if freq_main is not None:
        print(f"  Frequent itemsets       : {freq_main}")
    elif freq_main_alt is not None:
        print(f"  Frequent itemsets (main): {freq_main_alt}")
    else:
        print(f"  Frequent itemsets       : N/A")

    if freq_topk is not None:
        print(f"  Frequent itemsets (topk): {freq_topk}")

    print(f"  Total rules             : {assoc.get('total_rules', 'N/A')}")
    print(f"  Rules → topk:1          : {assoc.get('topk_rules', 'N/A')}")

    total_rules = assoc.get("total_rules", 0)
    rules_grade = (
        "RICH"     if total_rules >= 50 else
        "MODERATE" if total_rules >= 15 else
        "SPARSE"
    )
    print(f"  Grade                   : {rules_grade}")

    report["association_rules"] = {**assoc, "grade": rules_grade}

# ── OVERALL MODULE 2 STATUS ───────────────────────────────────────────
print(f"\n{'='*60}")
print(f"  MODULE 2 COMPLETION")
print(f"{'='*60}")

steps = {
    "Feature engineering (label enc + scaling + split)": True,
    "XGBoost classification": xgb is not None,
    "KMeans segmentation (3 clusters)": clust is not None,
    "DBSCAN anomaly detection": clust is not None,
    "PCA 2D visualization": clust is not None,
    "Association rules (FP-Growth)": assoc is not None,
}

done = sum(steps.values())

for step, completed in steps.items():
    print(f"  [{'✓' if completed else '✗'}] {step}")

print(f"\n  Score  : {done}/{len(steps)}")
print(f"  Status : {'MODULE 2 COMPLETE ✓' if done == len(steps) else 'IN PROGRESS'}")
print(f"  Next   : Module 3 — Kubeflow Pipeline orchestration")
print(f"{'='*60}\n")

# ── SAVE ──────────────────────────────────────────────────────────────
report["module_2_complete"] = done == len(steps)

storage.save_json(report, "evaluation_report.json", prefix=OUTPUT_PREFIX)

print(f"  Saved → output/evaluation_report.json\n")