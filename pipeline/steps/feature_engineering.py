"""
pipeline/steps/feature_engineering.py
Module 2 — Step 1
Input  : data/processed/products.csv
Output : data/output/X_train.csv, X_test.csv, y_train.csv, y_test.csv
         data/output/feature_matrix.csv   (full, for clustering)
         data/output/encoders.pkl         (saved for dashboard reuse)
"""

from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split

from storage import StorageManager, PROCESSED_PREFIX, OUTPUT_PREFIX

INPUT_FILENAME = "products.csv"

storage = StorageManager()

# Safety check: ensure processed data exists before proceeding
if not storage.exists(INPUT_FILENAME, prefix=PROCESSED_PREFIX):
    raise FileNotFoundError(
        f"Missing input: processed/{INPUT_FILENAME}. "
        f"Run pipeline/steps/preprocess.py first."
    )

df = storage.load_dataframe(INPUT_FILENAME, prefix=PROCESSED_PREFIX)
print(f"Loaded {len(df):,} products — {df.shape[1]} columns")

# ══════════════════════════════════════════════════════════════════════
# STEP 1 — SELECT FEATURES FOR ML
# ══════════════════════════════════════════════════════════════════════
# Numerical features → scale
NUM_FEATURES = [
    "price",
    "discount_pct",
    # "rating",
    # "review_count",
    "stock_qty",
    "days_since_publish",
]

# Categorical features → label encode
CAT_FEATURES = [
    "category",
    "brand",
    "source_store",
    # "price_segment",
    "shop_country",
]

# Boolean features → cast to int (already 0/1 compatible)
BOOL_FEATURES = [
    "in_stock",
    "is_on_promo",
]

TARGET = "topk_label"

# ══════════════════════════════════════════════════════════════════════
# STEP 2 — LABEL ENCODING (categorical → integer)
# ══════════════════════════════════════════════════════════════════════
encoders = {}
df_enc = df.copy()

for col in CAT_FEATURES:
    le = LabelEncoder()
    df_enc[f"{col}_enc"] = le.fit_transform(df_enc[col].astype(str))
    encoders[col] = le
    print(f"  Encoded {col:<20} → {len(le.classes_)} unique classes")

# Save encoders for dashboard + inference reuse
storage.save_pickle(encoders, "encoders.pkl", prefix=OUTPUT_PREFIX)
print(f"\n  Saved encoders → output/encoders.pkl")

# ══════════════════════════════════════════════════════════════════════
# STEP 3 — BUILD FEATURE MATRIX
# ══════════════════════════════════════════════════════════════════════
encoded_cat_cols = [f"{c}_enc" for c in CAT_FEATURES]
bool_int_cols    = BOOL_FEATURES

# Cast booleans
for col in BOOL_FEATURES:
    df_enc[col] = df_enc[col].astype(int)

ALL_FEATURES = NUM_FEATURES + encoded_cat_cols + bool_int_cols

X = df_enc[ALL_FEATURES].copy()
y = df_enc[TARGET].copy()

print(f"\n  Feature matrix shape : {X.shape}")
print(f"  Features used        : {ALL_FEATURES}")

# ══════════════════════════════════════════════════════════════════════
# STEP 4 — SCALING (for KMeans, DBSCAN, PCA — not needed for XGBoost)
# ══════════════════════════════════════════════════════════════════════
scaler = StandardScaler()
X_scaled = X.copy()
X_scaled[NUM_FEATURES] = scaler.fit_transform(X[NUM_FEATURES])

storage.save_pickle(scaler, "scaler.pkl", prefix=OUTPUT_PREFIX)
print(f"  Saved scaler → output/scaler.pkl")

# ══════════════════════════════════════════════════════════════════════════════
# STEP 5 — TRAIN / TEST SPLIT (stratified on topk_label)
# ══════════════════════════════════════════════════════════════════════
X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    random_state=42,
    stratify=y        # preserve 20/80 balance in both splits
)

print(f"\n  Train set : {len(X_train):,} rows  (topk=1: {y_train.sum()}, topk=0: {(y_train==0).sum()})")
print(f"  Test set  : {len(X_test):,}  rows  (topk=1: {y_test.sum()}, topk=0: {(y_test==0).sum()})")

# ══════════════════════════════════════════════════════════════════════
# STEP 6 — SAVE ALL OUTPUTS
# ══════════════════════════════════════════════════════════════════════
storage.save_dataframe(X_train, "X_train.csv", prefix=OUTPUT_PREFIX)
storage.save_dataframe(X_test, "X_test.csv", prefix=OUTPUT_PREFIX)
storage.save_dataframe(y_train.to_frame(name=y_train.name or 'target'), "y_train.csv", prefix=OUTPUT_PREFIX)
storage.save_dataframe(y_test.to_frame(name=y_test.name or 'target'), "y_test.csv", prefix=OUTPUT_PREFIX)

# Full scaled matrix for clustering (no split needed)
X_scaled_full = X_scaled.copy()
X_scaled_full["product_id"]      = df_enc["product_id"].values
X_scaled_full["name"]            = df_enc["name"].values
X_scaled_full["popularity_score"]= df_enc["popularity_score"].values
storage.save_dataframe(X_scaled_full, "feature_matrix.csv", prefix=OUTPUT_PREFIX)

print(f"\n  Saved X_train, X_test, y_train, y_test → output/")
print(f"  Saved feature_matrix.csv (full scaled, for clustering)")
print(f"\n  Ready for: XGBoost, KMeans, DBSCAN, PCA\n")
