# Code Review: Dashboard & LLM Integration with Storage.py

**Date:** May 4, 2026  
**Review Scope:** Dashboard, LLM modules, Docker, K8s deployment  
**Reviewer:** Code Analysis Agent

---

## Executive Summary

### ⚠️ CRITICAL ISSUES (Must Fix)

1. **`llm/context_builder.py`** — Uses hardcoded filesystem paths instead of StorageManager
   - Will **FAIL in Kubernetes** when MinIO is the only storage
   - Doesn't support MinIO at all

2. **`dashboard/data_loader.py`** — Incorrect path construction for StorageManager
   - Path concatenation with `/` operator will fail
   - Should use prefix parameter instead

3. **`infra/k8s/dashboard-deployment.yaml`** — Missing MinIO environment variables
   - Dashboard can't connect to MinIO without credentials
   - Relies on PVC which is local-only

---

## Detailed Findings

### 1. **`llm/context_builder.py` — 🔴 CRITICAL**

#### Problem
Lines 14-25 use direct file system paths:

```python
ROOT      = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
OUTPUT    = ROOT / "data" / "output"

@lru_cache(maxsize=1)
def _products() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "products.csv")  # ❌ Hard filesystem read
```

**Why this breaks:**
- In Kubernetes, files don't exist locally — they're in MinIO
- `pd.read_csv()` can't read from MinIO bucket
- StorageManager already supports MinIO fallback

#### Solution
Replace all hardcoded loaders with StorageManager (like `enrichment.py` does):

```python
from storage import StorageManager
import os
from pathlib import Path

BASE_DATA_PATH = Path(os.getenv("DATA_PATH", "/app/data"))
storage = StorageManager(base_path=BASE_DATA_PATH)

@lru_cache(maxsize=1)
def _products() -> pd.DataFrame:
    return storage.load_dataframe("products.csv", prefix="processed/")
```

**Impact:** Once fixed, this will auto-work in both local dev + MinIO production.

---

### 2. **`dashboard/data_loader.py` — 🟠 CRITICAL**

#### Problem
Lines 22-25:

```python
BASE_DATA_PATH = Path(os.getenv("DATA_PATH", "/app/data"))
PROCESSED = BASE_DATA_PATH / "processed"
OUTPUT = BASE_DATA_PATH / "output"

storage = StorageManager(base_path=BASE_DATA_PATH)

def load_products() -> pd.DataFrame:
    df = storage.load_dataframe(PROCESSED / "products.csv")  # ❌ Wrong usage
```

**Why this breaks:**
- Passing a full Path object instead of a filename
- Should use the `prefix` parameter:
  ```python
  storage.load_dataframe("products.csv", prefix="processed/")
  ```

#### Current vs. Expected
```python
# ❌ WRONG
df = storage.load_dataframe(PROCESSED / "products.csv")

# ✅ CORRECT
df = storage.load_dataframe("products.csv", prefix=PROCESSED_PREFIX)
```

**Where PROCESSED_PREFIX is defined in storage.py:**
```python
PROCESSED_PREFIX = "processed/"
OUTPUT_PREFIX = "output/"
```

**Impact:** Will work by accident locally, but is semantically wrong and fragile.

---

### 3. **`llm/synthesis.py` — ✅ GOOD EXAMPLE**

Lines 12-17 show the **correct pattern**:

```python
BASE_DATA_PATH = Path(os.getenv("DATA_PATH", "/app/data"))
OUTPUT_DIR = BASE_DATA_PATH / "output"
storage = StorageManager(base_path=BASE_DATA_PATH)

# Later:
storage.save_text(topk_text, OUTPUT_DIR / "llm_topk_summary.txt")
```

**Why this works:**
- Uses StorageManager for all file I/O
- Supports both local and MinIO seamlessly

---

### 4. **`llm/enrichment.py` — ✅ GOOD EXAMPLE**

Lines 11-20 correctly use StorageManager:

```python
from storage import StorageManager

BASE_DATA_PATH = Path(os.getenv("DATA_PATH", "/app/data"))
storage = StorageManager(base_path=BASE_DATA_PATH)

df = storage.load_dataframe(PROCESSED / "products.csv")  # Actually works here
enriched = storage.save_dataframe(df_enriched, output_path)
```

**Note:** This file incorrectly passes a Path object, but it works because StorageManager is forgiving. Should still be fixed for consistency.

---

### 5. **`infra/k8s/dashboard-deployment.yaml` — 🟠 MISCONFIGURED**

#### Problem 1: Missing MinIO Credentials
The deployment doesn't set environment variables for MinIO:

```yaml
spec:
  containers:
    - name: dashboard
      image: mohamediliasskaddar/e-commerce-dashboard:latest
      ports:
        - containerPort: 8501
      volumeMounts:
        - name: data-volume
          mountPath: /app/data
      # ❌ NO ENV VARS for MinIO
```

**Fix:** Add environment variables section:

```yaml
env:
  - name: MINIO_ENDPOINT
    value: "minio.storage.svc.cluster.local:9000"
  - name: MINIO_BUCKET
    value: "smart-ecommerce"
  - name: MINIO_ACCESS_KEY
    value: "minio"  # Or use Secret
  - name: MINIO_SECRET_KEY
    value: "minio123"  # Or use Secret
  - name: MINIO_SECURE
    value: "false"
  - name: DATA_PATH
    value: "/app/data"
```

#### Problem 2: Relies on LocalPath PVC Only
The deployment uses only local PersistentVolumeClaim:

```yaml
volumes:
  - name: data-volume
    persistentVolumeClaim:
      claimName: data-pvc  # Local storage, not MinIO
```

**Context:** Pipeline outputs files to MinIO, but dashboard can't read them without MinIO credentials.

---

### 6. **`infra/docker/dashboard.Dockerfile` — ✅ CORRECT**

The Dockerfile is properly structured:

```dockerfile
COPY requirements/dashboard.txt .
RUN pip install --no-cache-dir -r dashboard.txt  # ✓ Includes minio==7.2.20

COPY dashboard/ ./dashboard/
COPY llm/ ./llm/
COPY storage.py .  # ✓ Storage module copied

CMD ["streamlit", "run", "dashboard/app.py", ...]
```

**Status:** No changes needed here.

---

## Alignment Matrix

| Component | Uses StorageManager? | MinIO Support | K8s Ready | Status |
|-----------|---------------------|---------------|-----------|--------|
| `data_loader.py` | Partial (wrong usage) | Partial | ❌ No | 🟠 Needs fix |
| `context_builder.py` | ❌ No (hardcoded paths) | ❌ No | ❌ No | 🔴 Critical |
| `enrichment.py` | ✅ Yes (minor issue) | ✅ Yes | ✅ Yes | ✅ OK |
| `synthesis.py` | ✅ Yes | ✅ Yes | ✅ Yes | ✅ OK |
| `chains.py` | N/A (LLM logic) | N/A | N/A | ✅ OK |
| `dashboard.Dockerfile` | N/A | Imports OK | ✅ Yes | ✅ OK |
| `dashboard K8s deploy` | N/A | Missing env vars | ❌ No | 🟠 Needs fix |
| `charts.py` | N/A (Pure plotting) | N/A | N/A | ✅ OK |

---

## Data Flow Issues

### Current (Broken) Flow:
```
Pipeline → MinIO (outputs: models, clusters, rules)
                     ↓
Dashboard tries to read from Local PVC (PVC != MinIO)
                     ↓
❌ Data mismatch — Dashboard can't see pipeline outputs
```

### Expected (Fixed) Flow:
```
Pipeline → MinIO (outputs saved)
              ↓
StorageManager (with MinIO config)
              ↓
Dashboard + LLM modules (read via storage.py)
              ↓
✅ All components see same data
```

---

## Required Fixes

### Fix 1: `llm/context_builder.py` (Replace all hardcoded loaders)

**Replace:**
```python
ROOT      = Path(__file__).parent.parent
PROCESSED = ROOT / "data" / "processed"
OUTPUT    = ROOT / "data" / "output"

@lru_cache(maxsize=1)
def _products() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "products.csv")
```

**With:**
```python
from storage import StorageManager
import os
from pathlib import Path

BASE_DATA_PATH = Path(os.getenv("DATA_PATH", "/app/data"))
storage = StorageManager(base_path=BASE_DATA_PATH)

@lru_cache(maxsize=1)
def _products() -> pd.DataFrame:
    return storage.load_dataframe("products.csv", prefix="processed/")
```

**Apply to ALL loaders:** `_topk()`, `_xgb_results()`, `_clustering_results()`, etc.

---

### Fix 2: `dashboard/data_loader.py` (Correct path usage)

**Replace:**
```python
def load_products() -> pd.DataFrame:
    df = storage.load_dataframe(PROCESSED / "products.csv")
```

**With:**
```python
from storage import PROCESSED_PREFIX

def load_products() -> pd.DataFrame:
    df = storage.load_dataframe("products.csv", prefix=PROCESSED_PREFIX)
```

**Apply to all similar calls.**

---

### Fix 3: `infra/k8s/dashboard-deployment.yaml` (Add MinIO env vars)

**In `spec.template.spec.containers[0]`, add:**

```yaml
env:
  - name: MINIO_ENDPOINT
    value: "minio.storage.svc.cluster.local:9000"
  - name: MINIO_BUCKET
    value: "smart-ecommerce"
  - name: MINIO_ACCESS_KEY
    value: "minio"
  - name: MINIO_SECRET_KEY
    value: "minio123"
  - name: MINIO_SECURE
    value: "false"
  - name: DATA_PATH
    value: "/app/data"
```

---

## Testing Checklist

After applying fixes:

- [ ] **Local Dev:** Run dashboard with `.env` file
  ```bash
  streamlit run dashboard/app.py
  ```

- [ ] **K8s Dry-Run:** 
  ```bash
  kubectl apply -f infra/k8s/dashboard-deployment.yaml --dry-run=client
  ```

- [ ] **MinIO Integration Test:**
  ```python
  from storage import StorageManager
  storage = StorageManager()
  # Should read from MinIO if env vars are set
  df = storage.load_dataframe("products.csv", prefix="processed/")
  ```

- [ ] **LLM Context Builder:**
  ```bash
  python -c "from llm.context_builder import context_dataset_stats; print(context_dataset_stats())"
  ```

---

## Summary

### Blockers (Fix Before Deployment)
1. ❌ `context_builder.py` — hardcoded paths prevent MinIO reading
2. ❌ `dashboard K8s` — missing MinIO credentials

### Issues (Fix Soon)
3. 🟠 `data_loader.py` — incorrect path usage (works by accident)

### Status: Good
- ✅ `enrichment.py` — already correct pattern
- ✅ `synthesis.py` — already correct pattern
- ✅ `Dockerfile` — dependencies included

---

## Recommended PR Checklist

```markdown
- [ ] Fix `context_builder.py`: Replace all hardcoded paths with StorageManager
- [ ] Fix `data_loader.py`: Use proper prefix parameter
- [ ] Fix `dashboard-deployment.yaml`: Add MinIO environment variables  
- [ ] Test locally: `streamlit run dashboard/app.py`
- [ ] Test K8s: Deploy and verify dashboard reads data from MinIO
- [ ] Test LLM: Run synthesis pipeline and verify context_builder works
```

---
