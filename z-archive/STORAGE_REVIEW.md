# Pipeline Storage Layer Code Review

**Date:** April 30, 2026  
**Status:** ✅ COMPLETE — All issues fixed  
**Scope:** `storage.py` + pipeline steps (preprocess, feature_engineering, train, clustering, association_rules, evaluate)

---

## ✅ Issues Fixed

### 1. **StorageManager.save_dataframe() Bug**
**Issue:** Prefix parameter not used when creating local path
```python
# BEFORE (BUG):
def save_dataframe(self, df, path, prefix="", **kwargs):
    local_path = self.local_path(path)  # ❌ prefix ignored
    df.to_csv(local_path, index=False, **kwargs)
    self.upload_file(path, local_path, prefix)

# AFTER (FIXED):
def save_dataframe(self, df, path, prefix="", **kwargs):
    local_path = self.local_path(path, prefix)  # ✅ prefix used
    df.to_csv(local_path, index=False, **kwargs)
    self.upload_file(path, local_path, prefix)
```
**Impact:** Files saved without proper directory structure when using prefixes

---

### 2. **StorageManager.download_file() Bug**
**Issue:** Default local_file parameter ignored prefix
```python
# BEFORE (BUG):
def download_file(self, path, local_file=None, prefix=""):
    local_file = Path(local_file or self.local_path(path))  # ❌ prefix ignored in default

# AFTER (FIXED):
def download_file(self, path, local_file=None, prefix=""):
    local_file = Path(local_file or self.local_path(path, prefix))  # ✅ prefix used
```
**Impact:** Files downloaded to wrong local directory when prefix specified

---

### 3. **Duplicate Imports in preprocess.py**
**Issue:** pandas, numpy, re imported twice
```python
# BEFORE:
import pandas as pd
import numpy as np
import re, html
import pandas as pd  # ❌ DUPLICATE
import numpy as np   # ❌ DUPLICATE
import re, html      # ❌ DUPLICATE

# AFTER:
import pandas as pd
import numpy as np
import re, html
```

---

### 4. **Missing Safety Checks (All Steps)**
**Issue:** Pipeline steps could silently fail or fallback to local filesystem if data missing

**Added to:**
- ✅ `preprocess.py` - checks for raw/products.csv
- ✅ `feature_engineering.py` - checks for processed/products.csv
- ✅ `train.py` - checks for X_train.csv, X_test.csv, y_train.csv, y_test.csv
- ✅ `clustering.py` - checks for feature_matrix.csv and products.csv
- ✅ `association_rules.py` - checks for products.csv
- ✅ `evaluate.py` - warns if outputs missing

**Pattern:**
```python
# ✅ NEW SAFETY CHECK PATTERN:
if not storage.exists(filename, prefix=PREFIX):
    raise FileNotFoundError(
        f"Missing input: {prefix}{filename}. "
        f"Run <previous_step.py> first."
    )
```

---

### 5. **Direct Filesystem Access in evaluate.py**
**Issue:** Custom `load_json(path)` function used `open()` directly
```python
# BEFORE (DANGEROUS):
def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except FileNotFoundError:
        return None

# AFTER (REMOVED):
# Now uses StorageManager only:
xgb = storage.load_json("xgboost_results.json", prefix=OUTPUT_PREFIX) \
    if storage.exists("xgboost_results.json", prefix=OUTPUT_PREFIX) else None
```

---

## ✅ Verified Coverage

### Pipeline Data Flow (All Steps Use Prefixes)

```
Agents
  └─ raw/products.csv, raw/variants.csv  (via RAW_PREFIX)
      ↓
Preprocess
  └─ processed/products.csv  (via PROCESSED_PREFIX)
      ↓
Feature Engineering
  ├─ output/X_train.csv, X_test.csv, y_train.csv, y_test.csv
  ├─ output/feature_matrix.csv
  ├─ output/encoders.pkl
  └─ output/scaler.pkl  (all via OUTPUT_PREFIX)
      ↓
Parallel Steps:
  ├─ Train
  │   └─ output/xgboost_model.pkl, xgboost_results.json, feature_importance.csv
  ├─ Clustering
  │   └─ output/clusters.csv, pca_2d.csv, anomalies.csv, clustering_results.json
  └─ Association Rules
      └─ output/association_rules.csv, association_results.json
      ↓
Evaluate
  └─ output/evaluation_report.json
```

**All operations use:**
- `storage.load_dataframe(filename, prefix=...)`
- `storage.save_dataframe(df, filename, prefix=...)`
- `storage.load_json(filename, prefix=...)`
- `storage.save_json(data, filename, prefix=...)`
- `storage.load_pickle(filename, prefix=...)`
- `storage.save_pickle(obj, filename, prefix=...)`

---

## ✅ No Direct Filesystem Access

**Checked for and removed:**
- ❌ `open(path)` 
- ❌ `json.load(f)`
- ❌ `json.dump(f)`
- ❌ `pd.read_csv("/app/data/...")`
- ❌ Hardcoded paths like `/app/data/raw/...`

**All code now uses relative filenames + prefix system:**
- ✅ `storage.load_dataframe("products.csv", prefix=RAW_PREFIX)`
- ✅ `storage.save_dataframe(df, "output.csv", prefix=OUTPUT_PREFIX)`

---

## ✅ MinIO Native Architecture

**MinIO Bucket Structure:**
```
smart-ecommerce/
├── raw/
│   ├── products.csv
│   └── variants.csv
├── processed/
│   └── products.csv
└── output/
    ├── X_train.csv
    ├── X_test.csv
    ├── y_train.csv
    ├── y_test.csv
    ├── feature_matrix.csv
    ├── encoders.pkl
    ├── scaler.pkl
    ├── xgboost_model.pkl
    ├── xgboost_results.json
    ├── feature_importance.csv
    ├── clusters.csv
    ├── pca_2d.csv
    ├── anomalies.csv
    ├── clustering_results.json
    ├── association_rules.csv
    ├── association_results.json
    └── evaluation_report.json
```

**Local Fallback (when MinIO unavailable):**
```
/app/data/
├── raw/
├── processed/
└── output/
```

---

## ✅ Error Handling

**Pattern - Fail Fast:**
```python
if not storage.exists(filename, prefix=PREFIX):
    raise FileNotFoundError(
        f"Missing input: {prefix_name}/{filename}. "
        f"Run previous_step.py first."
    )
```

**Behavior:**
- ✅ No silent failures
- ✅ No fallback to stale local data
- ✅ Clear error messages guide user to previous step
- ✅ Pipeline stops immediately if dependency missing

---

## ✅ Consistency Checks

| Step | Input Source | Input Prefix | Output Prefix | Status |
|------|---------|---------------|---------------|--------|
| preprocess | raw/ | RAW_PREFIX | PROCESSED_PREFIX | ✅ |
| feature_engineering | processed/ | PROCESSED_PREFIX | OUTPUT_PREFIX | ✅ |
| train | output/ | OUTPUT_PREFIX | OUTPUT_PREFIX | ✅ |
| clustering | output/ + processed/ | OUTPUT_PREFIX + PROCESSED_PREFIX | OUTPUT_PREFIX | ✅ |
| association_rules | processed/ | PROCESSED_PREFIX | OUTPUT_PREFIX | ✅ |
| evaluate | output/ | OUTPUT_PREFIX | OUTPUT_PREFIX | ✅ |

---

## 📋 Files Modified

1. **storage.py**
   - Fixed `save_dataframe()` to use prefix in local_path
   - Fixed `download_file()` to use prefix in local_path default

2. **pipeline/steps/preprocess.py**
   - Removed duplicate imports
   - Added safety check for raw/products.csv

3. **pipeline/steps/feature_engineering.py**
   - Added safety check for processed/products.csv

4. **pipeline/steps/train.py**
   - Added safety checks for X_train.csv, X_test.csv, y_train.csv, y_test.csv

5. **pipeline/models/clustering.py**
   - Added safety checks for feature_matrix.csv, products.csv

6. **pipeline/models/association_rules.py**
   - Added safety check for products.csv

7. **pipeline/steps/evaluate.py**
   - Removed dangerous `load_json()` function with direct file opens
   - Added comprehensive safety checks with informative warnings
   - All file I/O now through StorageManager

---

## 🎯 Result

✅ **Pipeline is now:**
- **MinIO-native:** No direct filesystem access in pipeline code
- **Robust:** Fail-fast with clear error messages
- **Consistent:** All steps use same prefix system
- **Maintainable:** Single source of truth (StorageManager) for all I/O
- **Production-ready:** Handles local + remote storage transparently