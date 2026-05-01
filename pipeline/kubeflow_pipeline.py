from kfp import dsl
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from storage import StorageManager, RAW_PREFIX, PROCESSED_PREFIX, OUTPUT_PREFIX
import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dsl.component(
    base_image="mohamediliasskaddar/e-commerce-agents:latest"
)
def scraping():
    """Scrape data from all sources and save to MinIO"""
    import sys
    import os
    sys.path.append('/app')
    from agents.agent_coordinator import run_ingestion
    run_ingestion()


@dsl.component(
    base_image="mohamediliasskaddar/e-commerce-pipeline:latest"
)
def preprocess():
    """Preprocess raw data and save processed data to MinIO"""
    import sys
    sys.path.append('/app')
    from storage import StorageManager, RAW_PREFIX, PROCESSED_PREFIX
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    storage = StorageManager()

    # Safety check
    if not storage.exists("products.csv", prefix=RAW_PREFIX):
        raise FileNotFoundError("Missing input: raw/products.csv. Run scraping first.")

    # Load raw data
    df = storage.load_dataframe("products.csv", prefix=RAW_PREFIX)

    # Apply preprocessing logic (simplified - full logic in preprocess.py)
    # Remove duplicates, fix prices, etc.
    df = df.drop_duplicates(subset=['product_id'])
    df = df[df['price'] > 0]  # Remove zero prices

    # Save processed data
    storage.save_dataframe(df, "products.csv", prefix=PROCESSED_PREFIX)
    logger.info("Preprocessed data saved to processed/products.csv")


@dsl.component(
    base_image="mohamediliasskaddar/e-commerce-pipeline:latest"
)
def feature_engineering():
    """Perform feature engineering and save outputs to MinIO"""
    import sys
    sys.path.append('/app')
    from storage import StorageManager, PROCESSED_PREFIX, OUTPUT_PREFIX
    from sklearn.preprocessing import LabelEncoder, StandardScaler
    from sklearn.model_selection import train_test_split
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    storage = StorageManager()

    # Safety check
    if not storage.exists("products.csv", prefix=PROCESSED_PREFIX):
        raise FileNotFoundError("Missing input: processed/products.csv. Run preprocess first.")

    # Load processed data
    df = storage.load_dataframe("products.csv", prefix=PROCESSED_PREFIX)

    # Feature engineering logic (simplified)
    # Encode categorical features
    cat_features = ['category', 'brand', 'source_platform']
    encoders = {}
    for col in cat_features:
        if col in df.columns:
            le = LabelEncoder()
            df[f'{col}_encoded'] = le.fit_transform(df[col].fillna('unknown'))
            encoders[col] = le

    # Scale numerical features
    num_features = ['price', 'rating', 'review_count']
    scaler = StandardScaler()
    df_scaled = df.copy()
    for col in num_features:
        if col in df.columns:
            df_scaled[col] = scaler.fit_transform(df[[col]].fillna(0))

    # Split features and target
    feature_cols = [col for col in df_scaled.columns if col.endswith('_encoded') or col in num_features]
    X = df_scaled[feature_cols]
    y = df_scaled['price']  # Using price as target for demo

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # Save all outputs
    storage.save_pickle(encoders, "encoders.pkl", prefix=OUTPUT_PREFIX)
    storage.save_pickle(scaler, "scaler.pkl", prefix=OUTPUT_PREFIX)
    storage.save_dataframe(X_train, "X_train.csv", prefix=OUTPUT_PREFIX)
    storage.save_dataframe(X_test, "X_test.csv", prefix=OUTPUT_PREFIX)
    storage.save_dataframe(y_train.to_frame(name='target'), "y_train.csv", prefix=OUTPUT_PREFIX)
    storage.save_dataframe(y_test.to_frame(name='target'), "y_test.csv", prefix=OUTPUT_PREFIX)
    storage.save_dataframe(X, "feature_matrix.csv", prefix=OUTPUT_PREFIX)

    logger.info("Feature engineering completed and saved to output/")


@dsl.component(
    base_image="mohamediliasskaddar/e-commerce-pipeline:latest"
)
def train():
    """Train XGBoost model and save results to MinIO"""
    import sys
    import pandas as pd
    sys.path.append('/app')
    from storage import StorageManager, OUTPUT_PREFIX
    from xgboost import XGBRegressor
    from sklearn.metrics import mean_squared_error, r2_score
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    storage = StorageManager()

    # Safety checks
    required_files = ["X_train.csv", "X_test.csv", "y_train.csv", "y_test.csv"]
    for filename in required_files:
        if not storage.exists(filename, prefix=OUTPUT_PREFIX):
            raise FileNotFoundError(f"Missing input: output/{filename}. Run feature_engineering first.")

    # Load data
    X_train = storage.load_dataframe("X_train.csv", prefix=OUTPUT_PREFIX)
    X_test = storage.load_dataframe("X_test.csv", prefix=OUTPUT_PREFIX)
    y_train = storage.load_dataframe("y_train.csv", prefix=OUTPUT_PREFIX).squeeze()
    y_test = storage.load_dataframe("y_test.csv", prefix=OUTPUT_PREFIX).squeeze()

    # Train XGBoost model
    model = XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1, random_state=42)
    model.fit(X_train, y_train)

    # Make predictions and calculate metrics
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    # Feature importance
    importance_df = pd.DataFrame({
        'feature': X_train.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)

    # Save results
    storage.save_pickle(model, "xgboost_model.pkl", prefix=OUTPUT_PREFIX)
    storage.save_dataframe(importance_df, "feature_importance.csv", prefix=OUTPUT_PREFIX)

    results = {
        "model": "XGBoost Regressor",
        "mse": mse,
        "r2_score": r2,
        "n_estimators": 100,
        "max_depth": 6,
        "features_used": len(X_train.columns)
    }
    storage.save_json(results, "xgboost_results.json", prefix=OUTPUT_PREFIX)

    logger.info(f"XGBoost training completed - MSE: {mse:.4f}, R²: {r2:.4f}")


@dsl.component(
    base_image="mohamediliasskaddar/e-commerce-pipeline:latest"
)
def clustering():
    """Perform clustering analysis and save results to MinIO"""
    import sys
    import pandas as pd
    sys.path.append('/app')
    from storage import StorageManager, PROCESSED_PREFIX, OUTPUT_PREFIX
    from sklearn.cluster import KMeans
    from sklearn.decomposition import PCA
    from sklearn.ensemble import IsolationForest
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    storage = StorageManager()

    # Safety checks
    if not storage.exists("feature_matrix.csv", prefix=OUTPUT_PREFIX):
        raise FileNotFoundError("Missing input: output/feature_matrix.csv. Run feature_engineering first.")
    if not storage.exists("products.csv", prefix=PROCESSED_PREFIX):
        raise FileNotFoundError("Missing input: processed/products.csv. Run preprocess first.")

    # Load data
    X = storage.load_dataframe("feature_matrix.csv", prefix=OUTPUT_PREFIX)
    df_products = storage.load_dataframe("products.csv", prefix=PROCESSED_PREFIX)

    # K-Means clustering
    kmeans = KMeans(n_clusters=3, random_state=42)
    clusters = kmeans.fit_predict(X)
    df_products['cluster'] = clusters

    # PCA for 2D visualization
    pca = PCA(n_components=2, random_state=42)
    pca_coords = pca.fit_transform(X)
    df_pca = pd.DataFrame(pca_coords, columns=['pca_1', 'pca_2'])
    df_pca['cluster'] = clusters

    # Anomaly detection
    iso_forest = IsolationForest(contamination=0.1, random_state=42)
    anomalies = iso_forest.fit_predict(X)
    df_products['is_anomaly'] = anomalies == -1

    # Save results
    storage.save_dataframe(df_products[['product_id', 'cluster']], "clusters.csv", prefix=OUTPUT_PREFIX)
    storage.save_dataframe(df_pca, "pca_2d.csv", prefix=OUTPUT_PREFIX)
    storage.save_dataframe(df_products[df_products['is_anomaly']][['product_id', 'name', 'price']], "anomalies.csv", prefix=OUTPUT_PREFIX)

    results = {
        "clustering_method": "K-Means",
        "n_clusters": 3,
        "anomaly_detection": "Isolation Forest",
        "contamination": 0.1,
        "total_products": len(df_products),
        "anomalies_detected": df_products['is_anomaly'].sum()
    }
    storage.save_json(results, "clustering_results.json", prefix=OUTPUT_PREFIX)

    logger.info(f"Clustering completed - {len(df_products)} products, {df_products['is_anomaly'].sum()} anomalies detected")


@dsl.component(
    base_image="mohamediliasskaddar/e-commerce-pipeline:latest"
)
def association_rules():
    """Generate association rules and save results to MinIO"""
    import sys
    import pandas as pd
    sys.path.append('/app')
    from storage import StorageManager, PROCESSED_PREFIX, OUTPUT_PREFIX
    from mlxtend.frequent_patterns import fpgrowth, association_rules as ar
    from mlxtend.preprocessing import TransactionEncoder
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    storage = StorageManager()

    # Safety check
    if not storage.exists("products.csv", prefix=PROCESSED_PREFIX):
        raise FileNotFoundError("Missing input: processed/products.csv. Run preprocess first.")

    # Load data
    df = storage.load_dataframe("products.csv", prefix=PROCESSED_PREFIX)

    # Prepare transaction data for association rules
    # Group products by category/brand combinations as transactions
    transactions = []
    for _, group in df.groupby(['source_platform', 'source_store']):
        # Create transaction as list of categories in this "store"
        transaction = group['category'].dropna().unique().tolist()
        if transaction:
            transactions.append(transaction)

    # Generate association rules using FP-Growth
    te = TransactionEncoder()
    te_ary = te.fit_transform(transactions)
    df_encoded = pd.DataFrame(te_ary, columns=te.columns_)

    # Find frequent itemsets
    frequent_itemsets = fpgrowth(df_encoded, min_support=0.05, use_colnames=True)

    # Generate association rules
    rules = ar(frequent_itemsets, metric="confidence", min_threshold=0.3)
    rules = rules.sort_values('confidence', ascending=False)

    # Save results
    storage.save_dataframe(rules, "association_rules.csv", prefix=OUTPUT_PREFIX)

    results = {
        "algorithm": "FP-Growth",
        "min_support": 0.05,
        "min_confidence": 0.3,
        "total_transactions": len(transactions),
        "total_rules": len(rules),
        "avg_confidence": rules['confidence'].mean() if len(rules) > 0 else 0
    }
    storage.save_json(results, "association_results.json", prefix=OUTPUT_PREFIX)

    logger.info(f"Association rules generated - {len(rules)} rules from {len(transactions)} transactions")


@dsl.component(
    base_image="mohamediliasskaddar/e-commerce-pipeline:latest"
)
def evaluate():
    """Evaluate all models and generate final report to MinIO"""
    import sys
    import pandas as pd
    sys.path.append('/app')
    from storage import StorageManager, OUTPUT_PREFIX
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    storage = StorageManager()

    # Load all available results (graceful handling if some steps failed)
    results = {}

    if storage.exists("xgboost_results.json", prefix=OUTPUT_PREFIX):
        results["xgboost"] = storage.load_json("xgboost_results.json", prefix=OUTPUT_PREFIX)
    else:
        logger.warning("XGBoost results not found - run training step")

    if storage.exists("clustering_results.json", prefix=OUTPUT_PREFIX):
        results["clustering"] = storage.load_json("clustering_results.json", prefix=OUTPUT_PREFIX)
    else:
        logger.warning("Clustering results not found - run clustering step")

    if storage.exists("association_results.json", prefix=OUTPUT_PREFIX):
        results["association_rules"] = storage.load_json("association_results.json", prefix=OUTPUT_PREFIX)
    else:
        logger.warning("Association rules not found - run association_rules step")

    # Generate evaluation report
    report = {
        "pipeline_execution": "completed",
        "models_evaluated": list(results.keys()),
        "timestamp": pd.Timestamp.now().isoformat(),
        "results": results
    }

    # Save final report
    storage.save_json(report, "evaluation_report.json", prefix=OUTPUT_PREFIX)

    logger.info(f"Evaluation completed - {len(results)} models evaluated")


@dsl.pipeline(
    name="ecommerce-ml-pipeline",
    description="End-to-end ML pipeline for ecommerce intelligence with MinIO storage"
)
def pipeline():
    # Scraping task
    scrape_task = scraping()
    scrape_task.set_env_variable("MINIO_ENDPOINT", "minio.storage.svc.cluster.local:9000")
    scrape_task.set_env_variable("MINIO_BUCKET", "smart-ecommerce")
    scrape_task.set_env_variable("MINIO_ACCESS_KEY", "minio")
    scrape_task.set_env_variable("MINIO_SECRET_KEY", "minio123")
    scrape_task.set_env_variable("MINIO_SECURE", "false")

    # Preprocessing task (depends on scraping)
    preprocess_task = preprocess()
    preprocess_task.set_env_variable("MINIO_ENDPOINT", "minio.storage.svc.cluster.local:9000")
    preprocess_task.set_env_variable("MINIO_BUCKET", "smart-ecommerce")
    preprocess_task.set_env_variable("MINIO_ACCESS_KEY", "minio")
    preprocess_task.set_env_variable("MINIO_SECRET_KEY", "minio123")
    preprocess_task.set_env_variable("MINIO_SECURE", "false")
    preprocess_task.after(scrape_task)

    # Feature engineering task (depends on preprocessing)
    feature_task = feature_engineering()
    feature_task.set_env_variable("MINIO_ENDPOINT", "minio.storage.svc.cluster.local:9000")
    feature_task.set_env_variable("MINIO_BUCKET", "smart-ecommerce")
    feature_task.set_env_variable("MINIO_ACCESS_KEY", "minio")
    feature_task.set_env_variable("MINIO_SECRET_KEY", "minio123")
    feature_task.set_env_variable("MINIO_SECURE", "false")
    feature_task.after(preprocess_task)

    # Parallel model training tasks (all depend on feature engineering)
    train_task = train()
    train_task.set_env_variable("MINIO_ENDPOINT", "minio.storage.svc.cluster.local:9000")
    train_task.set_env_variable("MINIO_BUCKET", "smart-ecommerce")
    train_task.set_env_variable("MINIO_ACCESS_KEY", "minio")
    train_task.set_env_variable("MINIO_SECRET_KEY", "minio123")
    train_task.set_env_variable("MINIO_SECURE", "false")
    train_task.after(feature_task)

    cluster_task = clustering()
    cluster_task.set_env_variable("MINIO_ENDPOINT", "minio.storage.svc.cluster.local:9000")
    cluster_task.set_env_variable("MINIO_BUCKET", "smart-ecommerce")
    cluster_task.set_env_variable("MINIO_ACCESS_KEY", "minio")
    cluster_task.set_env_variable("MINIO_SECRET_KEY", "minio123")
    cluster_task.set_env_variable("MINIO_SECURE", "false")
    cluster_task.after(feature_task)

    rules_task = association_rules()
    rules_task.set_env_variable("MINIO_ENDPOINT", "minio.storage.svc.cluster.local:9000")
    rules_task.set_env_variable("MINIO_BUCKET", "smart-ecommerce")
    rules_task.set_env_variable("MINIO_ACCESS_KEY", "minio")
    rules_task.set_env_variable("MINIO_SECRET_KEY", "minio123")
    rules_task.set_env_variable("MINIO_SECURE", "false")
    rules_task.after(preprocess_task)  # Only needs processed data

    # Evaluation task (depends on all model tasks)
    eval_task = evaluate()
    eval_task.set_env_variable("MINIO_ENDPOINT", "minio.storage.svc.cluster.local:9000")
    eval_task.set_env_variable("MINIO_BUCKET", "smart-ecommerce")
    eval_task.set_env_variable("MINIO_ACCESS_KEY", "minio")
    eval_task.set_env_variable("MINIO_SECRET_KEY", "minio123")
    eval_task.set_env_variable("MINIO_SECURE", "false")
    eval_task.after(train_task, cluster_task, rules_task)


from kfp import compiler

if __name__ == "__main__":
    compiler.Compiler().compile(
        pipeline_func=pipeline,
        package_path="ecommerce_pipeline.yaml"
    )