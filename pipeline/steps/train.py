"""
pipeline/steps/train.py
Module 2 — Step 2: XGBoost Classification
Input  : data/output/X_train.csv, X_test.csv, y_train.csv, y_test.csv
Output : data/output/xgboost_model.pkl
         data/output/xgboost_results.json
         data/output/feature_importance.csv
"""

import pandas as pd

from pathlib import Path
from xgboost import XGBClassifier
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, accuracy_score, f1_score
)
from sklearn.metrics import precision_recall_curve

from storage import StorageManager, OUTPUT_PREFIX

storage = StorageManager()

# Safety check: ensure feature matrices exist before proceeding
required_files = ["X_train.csv", "X_test.csv", "y_train.csv", "y_test.csv"]
for fname in required_files:
    if not storage.exists(fname, prefix=OUTPUT_PREFIX):
        raise FileNotFoundError(
            f"Missing input: output/{fname}. "
            f"Run pipeline/steps/feature_engineering.py first."
        )

# ── LOAD ──────────────────────────────────────────────────────────────
X_train = storage.load_dataframe("X_train.csv", prefix=OUTPUT_PREFIX)
X_test  = storage.load_dataframe("X_test.csv", prefix=OUTPUT_PREFIX)
y_train = storage.load_dataframe("y_train.csv", prefix=OUTPUT_PREFIX).squeeze()
y_test  = storage.load_dataframe("y_test.csv", prefix=OUTPUT_PREFIX).squeeze()

print(f"Train: {X_train.shape}  |  Test: {X_test.shape}")

# ══════════════════════════════════════════════════════════════════════
# XGBOOST MODEL
# scale_pos_weight handles class imbalance (80% = 0, 20% = 1)
# ratio = count(0) / count(1)
# ══════════════════════════════════════════════════════════════════════
neg = (y_train == 0).sum()
pos = (y_train == 1).sum()
scale_weight = round(neg / pos, 2)
print(f"Class balance — neg: {neg}  pos: {pos}  scale_pos_weight: {scale_weight}")

model = XGBClassifier(
    n_estimators      = 300,
    max_depth         = 6,
    learning_rate     = 0.05,
    subsample         = 0.8,
    colsample_bytree  = 0.8,
    scale_pos_weight  = scale_weight,   # handles 80/20 imbalance
    use_label_encoder = False,
    eval_metric       = "logloss",
    random_state      = 42,
    n_jobs            = -1,
)

print("\nTraining XGBoost...")
model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    verbose=50,
)






# ── EVALUATION ────────────────────────────────────────────────────────
y_pred      = model.predict(X_test)
y_pred_prob = model.predict_proba(X_test)[:, 1]

accuracy  = round(accuracy_score(y_test, y_pred), 4)
f1        = round(f1_score(y_test, y_pred), 4)
roc_auc   = round(roc_auc_score(y_test, y_pred_prob), 4)
conf_mat  = confusion_matrix(y_test, y_pred).tolist()


# Find threshold that maximizes F1
precisions, recalls, thresholds = precision_recall_curve(y_test, y_pred_prob)
f1_scores = 2 * precisions * recalls / (precisions + recalls + 1e-8)
best_threshold = thresholds[f1_scores.argmax()]
print(f"Optimal threshold : {best_threshold:.3f}  (default is 0.5)")
# Apply optimal threshold
y_pred_optimal = (y_pred_prob >= best_threshold).astype(int)
f1_optimal = f1_score(y_test, y_pred_optimal)

print(f"\n{'='*50}")
print(f"  XGBOOST RESULTS")
print(f"{'='*50}")
print(f"  Accuracy  : {accuracy}")
print(f"  F1 Score  : {f1}")
print(f"F1 with optimal threshold : {f1_optimal:.4f}")
print(f"  ROC-AUC   : {roc_auc}")
print(f"\n  Confusion Matrix:")
print(f"  TN={conf_mat[0][0]}  FP={conf_mat[0][1]}")
print(f"  FN={conf_mat[1][0]}  TP={conf_mat[1][1]}")
print(f"\n{classification_report(y_test, y_pred, target_names=['not_top','top_k'])}")

# ── FEATURE IMPORTANCE ────────────────────────────────────────────────
import pandas as pd

importance_df = pd.DataFrame({
    "feature":   X_train.columns,
    "importance": model.feature_importances_
}).sort_values("importance", ascending=False)

print("  Top 10 most important features:")
print(importance_df.head(10).to_string(index=False))

# ── SAVE ──────────────────────────────────────────────────────────────
storage.save_pickle(model, "xgboost_model.pkl", prefix=OUTPUT_PREFIX)

storage.save_dataframe(importance_df, "feature_importance.csv", prefix=OUTPUT_PREFIX)

results = {
    "model":       "XGBClassifier",
    "accuracy":    accuracy,
    "f1_score":    f1,
    "roc_auc":     roc_auc,
    "confusion_matrix": conf_mat,
    "n_train":     len(X_train),
    "n_test":      len(X_test),
    "top_features": importance_df.head(5)["feature"].tolist(),
}
storage.save_json(results, "xgboost_results.json", prefix=OUTPUT_PREFIX)

print(f"\n  Saved → output/xgboost_model.pkl")
print(f"  Saved → output/xgboost_results.json")
print(f"  Saved → output/feature_importance.csv\n")
