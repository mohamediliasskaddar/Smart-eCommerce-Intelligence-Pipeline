"""
pipeline/pipeline_definition.py
Module 3 — Kubeflow Pipeline DSL
Orchestrates all ML steps as a DAG of containerized components.

Run locally  : python pipeline/pipeline_definition.py
Compile YAML : python pipeline/pipeline_definition.py --compile
Submit to KFP: python pipeline/pipeline_definition.py --submit
"""
import argparse
from pathlib import Path

try:
    import kfp
    from kfp import dsl
    from kfp.dsl import component, pipeline, Input, Output, Dataset, Model, Metrics
    KFP_AVAILABLE = True
except ImportError:
    KFP_AVAILABLE = False
    print("⚠  kfp not installed — run: pip install kfp")
    print("   Showing pipeline structure only.\n")


# ══════════════════════════════════════════════════════════════════════
# BASE IMAGE — all components share this
# Build with: docker build -f infra/Dockerfile.pipeline -t ecommerce-pipeline .
# ══════════════════════════════════════════════════════════════════════
BASE_IMAGE = "ecommerce-pipeline:latest"


# ══════════════════════════════════════════════════════════════════════
# COMPONENT 1 — DATA INGESTION
# ══════════════════════════════════════════════════════════════════════
if KFP_AVAILABLE:
    @component(base_image=BASE_IMAGE)
    def ingest_data(
        products_path:   str,
        variants_path:   str,
        output_products: Output[Dataset],
        output_variants: Output[Dataset],
        metrics:         Output[Metrics],
    ):
        """Load and validate raw data from data/processed/products.csv"""
        import pandas as pd
        import shutil

        df = pd.read_csv(products_path)
        dv = pd.read_csv(variants_path)

        # Validate schema
        required_cols = [
            "product_id","source_platform","source_store","name",
            "category","brand","price","discount_pct","rating",
            "review_count","in_stock","stock_qty","shop_country",
            "days_since_publish","is_on_promo","price_segment",
            "popularity_score","topk_label"
        ]
        missing = [c for c in required_cols if c not in df.columns]
        assert len(missing) == 0, f"Missing columns: {missing}"
        assert df.isnull().sum().sum() == 0, "Null values found — run enrichment first"
        assert len(df) >= 2000, f"Only {len(df)} products — need ≥ 2000"

        # Pass through to next step
        shutil.copy(products_path, output_products.path)
        shutil.copy(variants_path, output_variants.path)

        metrics.log_metric("total_products",  len(df))
        metrics.log_metric("total_variants",  len(dv))
        metrics.log_metric("null_values",     int(df.isnull().sum().sum()))
        metrics.log_metric("topk_positive",   int(df["topk_label"].sum()))
        metrics.log_metric("topk_pct",        round(df["topk_label"].mean() * 100, 1))
        print(f"✓ Ingested {len(df)} products, {len(dv)} variants")


    # ══════════════════════════════════════════════════════════════════
    # COMPONENT 2 — FEATURE ENGINEERING
    # ══════════════════════════════════════════════════════════════════
    @component(base_image=BASE_IMAGE)
    def feature_engineering(
        input_products: Input[Dataset],
        output_X_train: Output[Dataset],
        output_X_test:  Output[Dataset],
        output_y_train: Output[Dataset],
        output_y_test:  Output[Dataset],
        output_matrix:  Output[Dataset],
        output_encoders: Output[Model],
        output_scaler:   Output[Model],
        metrics:         Output[Metrics],
        test_size:       float = 0.2,
        random_state:    int   = 42,
    ):
        import pandas as pd
        import numpy as np
        import pickle
        from sklearn.preprocessing import LabelEncoder, StandardScaler
        from sklearn.model_selection import train_test_split

        df = pd.read_csv(input_products.path)

        NUM_FEATURES  = ["price", "discount_pct", "stock_qty", "days_since_publish"]
        CAT_FEATURES  = ["category", "brand", "source_store", "shop_country"]
        BOOL_FEATURES = ["in_stock", "is_on_promo"]
        TARGET        = "topk_label"

        # Label encode
        encoders = {}
        df_enc = df.copy()
        for col in CAT_FEATURES:
            le = LabelEncoder()
            df_enc[f"{col}_enc"] = le.fit_transform(df_enc[col].astype(str))
            encoders[col] = le

        # Feature matrix
        for col in BOOL_FEATURES:
            df_enc[col] = df_enc[col].astype(int)

        encoded_cat = [f"{c}_enc" for c in CAT_FEATURES]
        ALL_FEATURES = NUM_FEATURES + encoded_cat + BOOL_FEATURES

        X = df_enc[ALL_FEATURES].copy()
        y = df_enc[TARGET].copy()

        # Scale
        scaler = StandardScaler()
        X_scaled = X.copy()
        X_scaled[NUM_FEATURES] = scaler.fit_transform(X[NUM_FEATURES])

        # Split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=random_state, stratify=y
        )

        # Save
        X_train.to_csv(output_X_train.path, index=False)
        X_test.to_csv(output_X_test.path,   index=False)
        y_train.to_csv(output_y_train.path, index=False)
        y_test.to_csv(output_y_test.path,   index=False)

        X_scaled_full = X_scaled.copy()
        X_scaled_full["product_id"] = df_enc["product_id"].values
        X_scaled_full["name"]       = df_enc["name"].values
        X_scaled_full.to_csv(output_matrix.path, index=False)

        with open(output_encoders.path, "wb") as f:
            pickle.dump(encoders, f)
        with open(output_scaler.path, "wb") as f:
            pickle.dump(scaler, f)

        metrics.log_metric("n_features",  len(ALL_FEATURES))
        metrics.log_metric("n_train",     len(X_train))
        metrics.log_metric("n_test",      len(X_test))
        metrics.log_metric("train_topk_pct", round(y_train.mean() * 100, 1))
        metrics.log_metric("test_topk_pct",  round(y_test.mean() * 100, 1))
        print(f"✓ Feature engineering done — {len(ALL_FEATURES)} features")


    # ══════════════════════════════════════════════════════════════════
    # COMPONENT 3 — XGBOOST TRAINING
    # ══════════════════════════════════════════════════════════════════
    @component(base_image=BASE_IMAGE)
    def train_xgboost(
        input_X_train:   Input[Dataset],
        input_X_test:    Input[Dataset],
        input_y_train:   Input[Dataset],
        input_y_test:    Input[Dataset],
        output_model:    Output[Model],
        output_importance: Output[Dataset],
        metrics:         Output[Metrics],
        n_estimators:    int   = 300,
        max_depth:       int   = 6,
        learning_rate:   float = 0.05,
    ):
        import pandas as pd
        import pickle
        from xgboost import XGBClassifier
        from sklearn.metrics import accuracy_score, f1_score, roc_auc_score

        X_train = pd.read_csv(input_X_train.path)
        X_test  = pd.read_csv(input_X_test.path)
        y_train = pd.read_csv(input_y_train.path).squeeze()
        y_test  = pd.read_csv(input_y_test.path).squeeze()

        neg = (y_train == 0).sum()
        pos = (y_train == 1).sum()
        scale_weight = round(neg / pos, 2)

        model = XGBClassifier(
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_weight,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
        model.fit(X_train, y_train,
                  eval_set=[(X_test, y_test)], verbose=50)

        y_pred      = model.predict(X_test)
        y_pred_prob = model.predict_proba(X_test)[:, 1]

        acc     = round(accuracy_score(y_test, y_pred), 4)
        f1      = round(f1_score(y_test, y_pred), 4)
        roc_auc = round(roc_auc_score(y_test, y_pred_prob), 4)

        importance_df = pd.DataFrame({
            "feature":    X_train.columns,
            "importance": model.feature_importances_
        }).sort_values("importance", ascending=False)

        with open(output_model.path, "wb") as f:
            pickle.dump(model, f)
        importance_df.to_csv(output_importance.path, index=False)

        metrics.log_metric("accuracy",  acc)
        metrics.log_metric("f1_score",  f1)
        metrics.log_metric("roc_auc",   roc_auc)
        metrics.log_metric("top_feature", importance_df.iloc[0]["feature"])
        print(f"✓ XGBoost — accuracy={acc}  f1={f1}  roc_auc={roc_auc}")


    # ══════════════════════════════════════════════════════════════════
    # COMPONENT 4 — CLUSTERING
    # ══════════════════════════════════════════════════════════════════
    @component(base_image=BASE_IMAGE)
    def run_clustering(
        input_matrix:    Input[Dataset],
        input_products:  Input[Dataset],
        output_clusters: Output[Dataset],
        output_pca:      Output[Dataset],
        output_anomalies:Output[Dataset],
        metrics:         Output[Metrics],
        n_clusters:      int   = 3,
        dbscan_eps:      float = 0.8,
        dbscan_min_samples: int = 5,
    ):
        import pandas as pd
        import numpy as np
        from sklearn.cluster import KMeans, DBSCAN
        from sklearn.decomposition import PCA
        from sklearn.metrics import silhouette_score

        df_matrix   = pd.read_csv(input_matrix.path)
        df_products = pd.read_csv(input_products.path)

        meta_cols    = ["product_id", "name"]
        feature_cols = [c for c in df_matrix.columns if c not in meta_cols]
        X    = df_matrix[feature_cols].values
        meta = df_matrix[["product_id", "name"]]

        # KMeans
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(X)
        sil = round(silhouette_score(X, cluster_labels), 4)

        df_clustered = df_products.copy()
        df_clustered["cluster_id"] = cluster_labels

        price_rank = df_clustered.groupby("cluster_id")["price"].mean().rank().astype(int)
        seg_names  = {price_rank[price_rank == 1].index[0]: "budget",
                      price_rank[price_rank == 2].index[0]: "mid_range",
                      price_rank[price_rank == 3].index[0]: "premium"}
        df_clustered["segment"] = df_clustered["cluster_id"].map(seg_names)

        # DBSCAN
        dbscan    = DBSCAN(eps=dbscan_eps, min_samples=dbscan_min_samples, n_jobs=-1)
        db_labels = dbscan.fit_predict(X)
        df_clustered["is_anomaly"] = (db_labels == -1).astype(int)

        # PCA
        pca   = PCA(n_components=2, random_state=42)
        X_pca = pca.fit_transform(X)
        explained = pca.explained_variance_ratio_

        df_pca = pd.DataFrame({
            "product_id":   meta["product_id"].values,
            "name":         meta["name"].values,
            "PC1":          X_pca[:, 0].round(4),
            "PC2":          X_pca[:, 1].round(4),
            "cluster_id":   cluster_labels,
            "segment":      df_clustered["segment"].values,
            "is_anomaly":   (db_labels == -1).astype(int),
            "price":        df_products["price"].values,
            "rating":       df_products["rating"].values,
            "topk_label":   df_products["topk_label"].values,
            "category":     df_products["category"].values,
            "source_store": df_products["source_store"].values,
        })

        df_clustered[["product_id","cluster_id","segment","is_anomaly"]].to_csv(
            output_clusters.path, index=False
        )
        df_pca.to_csv(output_pca.path, index=False)
        df_clustered[df_clustered["is_anomaly"] == 1].to_csv(
            output_anomalies.path, index=False
        )

        n_anomalies = int((db_labels == -1).sum())
        metrics.log_metric("silhouette_score",   sil)
        metrics.log_metric("n_anomalies",        n_anomalies)
        metrics.log_metric("pca_variance_total", round(float(sum(explained)), 4))
        metrics.log_metric("pca_pc1",            round(float(explained[0]), 4))
        metrics.log_metric("pca_pc2",            round(float(explained[1]), 4))
        print(f"✓ Clustering — silhouette={sil}  anomalies={n_anomalies}")


    # ══════════════════════════════════════════════════════════════════
    # COMPONENT 5 — TOP-K SELECTOR
    # ══════════════════════════════════════════════════════════════════
    @component(base_image=BASE_IMAGE)
    def select_topk(
        input_products:  Input[Dataset],
        input_clusters:  Input[Dataset],
        input_model:     Input[Model],
        input_encoders:  Input[Model],
        output_topk:     Output[Dataset],
        metrics:         Output[Metrics],
        top_k:           int = 100,
    ):
        import pandas as pd
        import pickle

        df       = pd.read_csv(input_products.path)
        clusters = pd.read_csv(input_clusters.path)

        # Merge cluster/segment info
        df = df.merge(clusters[["product_id","segment","is_anomaly"]], on="product_id", how="left")

        # Rank by popularity_score (already computed in preprocess)
        df_topk = (
            df[df["topk_label"] == 1]
            .sort_values("popularity_score", ascending=False)
            .head(top_k)
        )

        # Add rank column
        df_topk = df_topk.copy()
        df_topk.insert(0, "rank", range(1, len(df_topk) + 1))

        df_topk.to_csv(output_topk.path, index=False)

        metrics.log_metric("topk_count",        len(df_topk))
        metrics.log_metric("topk_avg_price",    round(df_topk["price"].mean(), 2))
        metrics.log_metric("topk_avg_rating",   round(df_topk["rating"].mean(), 2))
        metrics.log_metric("topk_avg_reviews",  round(df_topk["review_count"].mean(), 0))
        metrics.log_metric("topk_on_promo_pct", round(df_topk["is_on_promo"].mean() * 100, 1))
        print(f"✓ Top-K selector — {len(df_topk)} products selected")


    # ══════════════════════════════════════════════════════════════════
    # PIPELINE DEFINITION — DAG
    # ══════════════════════════════════════════════════════════════════
    @pipeline(
        name="smart-ecommerce-intelligence",
        description="End-to-end ML pipeline: ingest → features → XGBoost → clustering → Top-K"
    )
    def ecommerce_pipeline(
        products_path:   str   = "data/processed/products.csv",
        variants_path:   str   = "data/raw/variants.csv",
        test_size:       float = 0.2,
        n_estimators:    int   = 300,
        max_depth:       int   = 6,
        learning_rate:   float = 0.05,
        n_clusters:      int   = 3,
        top_k:           int   = 100,
    ):
        # Step 1 — Ingest & validate
        ingest = ingest_data(
            products_path=products_path,
            variants_path=variants_path,
        )

        # Step 2 — Feature engineering (depends on ingest)
        features = feature_engineering(
            input_products=ingest.outputs["output_products"],
            test_size=test_size,
        )

        # Step 3a — XGBoost (depends on feature engineering)
        xgb = train_xgboost(
            input_X_train=features.outputs["output_X_train"],
            input_X_test=features.outputs["output_X_test"],
            input_y_train=features.outputs["output_y_train"],
            input_y_test=features.outputs["output_y_test"],
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
        )

        # Step 3b — Clustering (depends on feature engineering, runs parallel to XGBoost)
        clustering = run_clustering(
            input_matrix=features.outputs["output_matrix"],
            input_products=ingest.outputs["output_products"],
            n_clusters=n_clusters,
        )

        # Step 4 — Top-K selector (depends on both XGBoost + clustering)
        topk = select_topk(
            input_products=ingest.outputs["output_products"],
            input_clusters=clustering.outputs["output_clusters"],
            input_model=xgb.outputs["output_model"],
            input_encoders=features.outputs["output_encoders"],
            top_k=top_k,
        )


# ══════════════════════════════════════════════════════════════════════
# CLI ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--compile", action="store_true", help="Compile to YAML")
    parser.add_argument("--submit",  action="store_true", help="Submit to KFP server")
    parser.add_argument("--host",    default="http://localhost:8080", help="KFP host")
    args = parser.parse_args()

    if not KFP_AVAILABLE:
        print("Pipeline structure:")
        print("  1. ingest_data")
        print("  2. feature_engineering")
        print("  3a. train_xgboost      ┐ parallel")
        print("  3b. run_clustering     ┘")
        print("  4. select_topk")
        exit(0)

    if args.compile:
        from kfp import compiler
        output_file = "infra/k8s/kubeflow-pipeline.yaml"
        Path("infra/k8s").mkdir(parents=True, exist_ok=True)
        compiler.Compiler().compile(ecommerce_pipeline, output_file)
        print(f"✓ Compiled → {output_file}")

    elif args.submit:
        import kfp
        client = kfp.Client(host=args.host)
        run = client.create_run_from_pipeline_func(
            ecommerce_pipeline,
            arguments={
                "products_path": "data/processed/products.csv",
                "variants_path": "data/raw/variants.csv",
                "top_k":         100,
            },
            run_name="ecommerce-run-v1",
        )
        print(f"✓ Submitted → run_id: {run.run_id}")
        print(f"  View at: {args.host}/#/runs/details/{run.run_id}")

    else:
        print("Usage:")
        print("  python pipeline/pipeline_definition.py --compile   # → YAML")
        print("  python pipeline/pipeline_definition.py --submit    # → KFP server")
