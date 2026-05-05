"""
pipeline/models/clustering.py
Module 2 — Step 3: KMeans + DBSCAN + PCA
Input  : data/output/feature_matrix.csv
Output : data/output/clusters.csv
         data/output/pca_2d.csv
         data/output/anomalies.csv
         data/output/clustering_results.json
"""
import pandas as pd
import numpy as np
import json
import pickle
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score

from storage import StorageManager, PROCESSED_PREFIX, OUTPUT_PREFIX

storage = StorageManager()

# Safety check: ensure required data exists before proceeding
if not storage.exists("feature_matrix.csv", prefix=OUTPUT_PREFIX):
    raise FileNotFoundError(
        f"Missing input: output/feature_matrix.csv. "
        f"Run pipeline/steps/feature_engineering.py first."
    )
if not storage.exists("products.csv", prefix=PROCESSED_PREFIX):
    raise FileNotFoundError(
        f"Missing input: processed/products.csv. "
        f"Run pipeline/steps/preprocess.py first."
    )

# ── LOAD ──────────────────────────────────────────────────────────────
df_matrix = storage.load_dataframe("feature_matrix.csv", prefix=OUTPUT_PREFIX)
df_products = storage.load_dataframe("products.csv", prefix=PROCESSED_PREFIX)

# Separate metadata from features
meta_cols    = ["product_id", "name", "popularity_score"]
feature_cols = [c for c in df_matrix.columns if c not in meta_cols]

X = df_matrix[feature_cols].values
meta = df_matrix[meta_cols]

print(f"Feature matrix: {X.shape[0]} products × {X.shape[1]} features")

# ══════════════════════════════════════════════════════════════════════
# 1. KMEANS — 3 CLUSTERS (premium / mid / budget)
# ══════════════════════════════════════════════════════════════════════
print("\n[1] KMeans clustering...")

# Find optimal K using elbow (silhouette) — test K=2..6
sil_scores = {}
for k in range(2, 7):
    km_test = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels  = km_test.fit_predict(X)
    sil     = silhouette_score(X, labels)
    sil_scores[k] = round(sil, 4)
    print(f"   K={k}  silhouette={sil:.4f}")

best_k = max(sil_scores, key=sil_scores.get)
print(f"\n   Best K = {best_k} (silhouette={sil_scores[best_k]})")

# Train final KMeans with best K (we also always keep K=3 for interpretability)
K = 3   # project requires 3 segments: premium / mid / budget
kmeans = KMeans(n_clusters=K, random_state=42, n_init=10)
cluster_labels = kmeans.fit_predict(X)

# Name clusters by their average price (human-readable)
df_clustered = df_products.copy()
df_clustered["cluster_id"] = cluster_labels

cluster_profiles = df_clustered.groupby("cluster_id").agg(
    mean_price    = ("price",            "mean"),
    mean_rating   = ("rating",           "mean"),
    mean_reviews  = ("review_count",     "mean"),
    mean_discount = ("discount_pct",     "mean"),
    count         = ("product_id",       "count"),
    topk_rate     = ("topk_label",       "mean"),
).round(2)

# Assign segment names based on mean price rank
price_rank = cluster_profiles["mean_price"].rank().astype(int)
segment_map = {
    cluster_profiles.index[price_rank == 1][0]: "budget",
    cluster_profiles.index[price_rank == 2][0]: "mid_range",
    cluster_profiles.index[price_rank == 3][0]: "premium",
}
df_clustered["segment"] = df_clustered["cluster_id"].map(segment_map)

print(f"\n   Cluster profiles:")
for cid, row in cluster_profiles.iterrows():
    seg = segment_map.get(cid, "?")
    print(f"   Cluster {cid} [{seg}] — "
          f"n={int(row['count'])}  "
          f"avg_price=${row['mean_price']:.0f}  "
          f"avg_rating={row['mean_rating']:.1f}  "
          f"topk_rate={row['topk_rate']:.1%}")

silhouette_final = round(silhouette_score(X, cluster_labels), 4)
print(f"\n   Final silhouette score: {silhouette_final}")

# ══════════════════════════════════════════════════════════════════════
# 2. DBSCAN — ANOMALY DETECTION (price + discount outliers)
# ══════════════════════════════════════════════════════════════════════
print("\n[2] DBSCAN anomaly detection...")

# Use only price-related features for anomaly detection
# Focus: unusual price/discount combinations
price_features = ["price", "discount_pct", "price_original"]
price_cols_idx = [feature_cols.index(c) for c in price_features if c in feature_cols]
X_price = X[:, price_cols_idx] if price_cols_idx else X[:, :3]

dbscan = DBSCAN(
    eps=0.8,          # neighborhood radius (scaled data)
    min_samples=5,    # minimum neighbors to be a core point
    n_jobs=-1
)
db_labels = dbscan.fit_predict(X_price)

n_anomalies = (db_labels == -1).sum()
n_clusters  = len(set(db_labels)) - (1 if -1 in db_labels else 0)
print(f"   DBSCAN found {n_clusters} dense regions")
print(f"   Anomalies detected: {n_anomalies} products ({n_anomalies/len(X)*100:.1f}%)")

df_clustered["is_anomaly"] = (db_labels == -1).astype(int)
df_anomalies = df_clustered[df_clustered["is_anomaly"] == 1][
    ["product_id", "name", "price", "discount_pct", "price_original",
     "brand", "category", "source_store"]
].copy()

if len(df_anomalies) > 0:
    print(f"\n   Sample anomalies (unusual price/discount):")
    print(df_anomalies[["name","price","discount_pct","source_store"]].head(5).to_string(index=False))

# ══════════════════════════════════════════════════════════════════════
# 3. PCA — 2D VISUALIZATION
# ══════════════════════════════════════════════════════════════════════
print("\n[3] PCA dimensionality reduction...")

pca = PCA(n_components=2, random_state=42)
X_pca = pca.fit_transform(X)

explained = pca.explained_variance_ratio_
print(f"   Explained variance: PC1={explained[0]:.1%}  PC2={explained[1]:.1%}  Total={sum(explained):.1%}")

df_pca = pd.DataFrame({
    "product_id":      meta["product_id"].values,
    "name":            meta["name"].values,
    "PC1":             X_pca[:, 0].round(4),
    "PC2":             X_pca[:, 1].round(4),
    "cluster_id":      cluster_labels,
    "segment":         df_clustered["segment"].values,
    "is_anomaly":      (db_labels == -1).astype(int),
    "price":           df_products["price"].values,
    "rating":          df_products["rating"].values,
    "topk_label":      df_products["topk_label"].values,
    "category":        df_products["category"].values,
    "source_store":    df_products["source_store"].values,
})

# ── SAVE ALL OUTPUTS ──────────────────────────────────────────────────
clusters_out = df_clustered[["product_id", "cluster_id", "segment", "is_anomaly"]]
storage.save_dataframe(clusters_out, "clusters.csv", prefix=OUTPUT_PREFIX)
storage.save_dataframe(df_pca, "pca_2d.csv", prefix=OUTPUT_PREFIX)
storage.save_dataframe(df_anomalies, "anomalies.csv", prefix=OUTPUT_PREFIX)

clustering_results = {
    "kmeans": {
        "k":                  K,
        "silhouette_score":   silhouette_final,
        "silhouette_by_k":    sil_scores,
        "segments":           {str(k): v for k, v in segment_map.items()},
        "cluster_profiles":   cluster_profiles.to_dict(),
    },
    "dbscan": {
        "eps":         0.8,
        "min_samples": 5,
        "n_anomalies": int(n_anomalies),
        "anomaly_pct": round(n_anomalies / len(X) * 100, 2),
    },
    "pca": {
        "n_components":        2,
        "explained_variance":  [round(v, 4) for v in explained],
        "total_explained":     round(sum(explained), 4),
    }
}
storage.save_json(clustering_results, "clustering_results.json", prefix=OUTPUT_PREFIX)

print(f"\n  Saved → output/clusters.csv")
print(f"  Saved → output/pca_2d.csv")
print(f"  Saved → output/anomalies.csv")
print(f"  Saved → output/clustering_results.json\n")
