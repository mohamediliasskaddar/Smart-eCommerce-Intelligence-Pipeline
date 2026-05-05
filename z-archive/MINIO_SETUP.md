# MinIO Storage Refactoring — Setup Guide

## Overview
The entire codebase has been refactored to use MinIO (S3-compatible object storage) for all data artifacts, with optional local caching. This eliminates CI/CD issues caused by local volume mounting and improves scalability.

---

## 1. Environment Configuration

### Create `.env` file from template:
```bash
cp .env.example .env
```

### Edit `.env` with your MinIO credentials:
```env
# MinIO Configuration
MINIO_ENDPOINT=localhost:9000          # Docker Compose local
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=smart-ecommerce
MINIO_SECURE=false                     # Use http for local dev

# Data path (local cache)
DATA_PATH=/app/data

# LLM Keys (optional)
GROQ_API_KEY=your_key_here
GOOGLE_API_KEY=your_key_here

ENV=production
```

### For Kubernetes, update endpoints:
```env
MINIO_ENDPOINT=minio.default.svc.cluster.local:9000
MINIO_SECURE=true                      # Use https in K8s
```

---

## 2. Docker Compose Deployment

### Start all services (MinIO + Pipeline + Dashboard):
```bash
docker-compose up -d
```

### MinIO Web Console:
- **URL**: http://localhost:9001
- **Username**: minioadmin
- **Password**: minioadmin

### Pipeline runs with MinIO:
- Agents write to MinIO bucket `smart-ecommerce/raw/`
- Pipeline reads from MinIO and writes outputs to `data/output/`
- All outputs are automatically synced to MinIO
- Local `/app/data` acts as a cache layer

### Verify MinIO is working:
```bash
docker-compose logs minio | tail -20
```

---

## 3. Kubernetes Deployment

### Create ConfigMap and Secret:
```bash
kubectl apply -f infra/k8s/volumes.yaml
```

This creates:
- `minio-config` ConfigMap (endpoint, bucket)
- `minio-secret` Secret (credentials)
- `minio` StatefulSet with persistent storage
- `minio` ClusterIP Service (internal)
- `minio-lb` LoadBalancer Service (external)

### Deploy agents and pipeline:
```bash
kubectl apply -f infra/k8s/agents-deployment.yaml
kubectl apply -f infra/k8s/pipeline-deployment.yaml
kubectl apply -f infra/k8s/dashboard-deployment.yaml
```

### Check deployments:
```bash
kubectl get pods -l app=minio
kubectl get pods -l app=agents
kubectl get pods -l app=pipeline
```

### Access MinIO console from K8s:
```bash
kubectl port-forward svc/minio-lb 9001:9001
```

---

## 4. Code Changes Summary

### New Files:
- **`storage.py`** — Core `StorageManager` class for MinIO/local hybrid storage
  - Auto-detects MinIO configuration via environment variables
  - Falls back to local storage if MinIO is unavailable
  - Supports CSV, JSON, pickle, and text files

### Updated Modules:
- **`agents/agent_coordinator.py`** — Uploads raw products/variants to MinIO
- **`pipeline/steps/preprocess.py`** — Reads raw data from MinIO, writes processed
- **`pipeline/steps/feature_engineering.py`** — Reads/writes training data via MinIO
- **`pipeline/steps/train.py`** — Loads train/test data, saves model and results
- **`pipeline/steps/evaluate.py`** — Loads all evaluation JSON files from MinIO
- **`pipeline/models/clustering.py`** — Reads feature matrix, writes clusters
- **`pipeline/models/association_rules.py`** — Saves rules via MinIO
- **`llm/synthesis.py`** — Saves LLM summaries to MinIO
- **`llm/enrichment.py`** — Saves enriched products to MinIO
- **`llm/mcp_agents.py`** — Added StorageManager import for audit logging
- **`dashboard/data_loader.py`** — Transparently loads data from MinIO or local cache

### Updated Docker Images:
- All `Dockerfile`s now copy `storage.py` into the image
- All services include `.env.example` for configuration
- Removed persistent volume mounts (MinIO handles data)

### Updated Orchestration:
- **`compose.yml`** — Added MinIO service, environment vars, health checks
- **`infra/k8s/volumes.yaml`** — Replaces PVC with MinIO StatefulSet + Services
- **`infra/k8s/agents-deployment.yaml`** — Environment vars, optional emptyDir cache
- **`infra/k8s/pipeline-deployment.yaml`** — Environment vars, optional emptyDir cache
- **`pipeline/kubeflow_pipeline.py`** — Sets environment variables on pipeline components

### Updated Dependencies:
- **`requirements.txt`** — Added `minio==8.5.0`

---

## 5. How It Works

### Data Flow:
```
Agent Scraping
  └─> StorageManager.save_dataframe()
      ├─> Write to local cache: /app/data/raw/products.csv
      └─> Upload to MinIO: s3://smart-ecommerce/raw/products.csv

Preprocessing
  └─> StorageManager.load_dataframe()
      ├─> Check local cache first (fast)
      └─> Download from MinIO if missing (fallback)
  └─> StorageManager.save_dataframe()
      ├─> Write to local cache: /app/data/processed/products.csv
      └─> Upload to MinIO: s3://smart-ecommerce/processed/products.csv

Dashboard
  └─> StorageManager.load_dataframe()
      ├─> Check local cache (populated during pipeline run)
      └─> Pull from MinIO if needed
```

### Storage Manager Behavior:
- **Hybrid Mode**: Always saves to both local AND MinIO
- **Read Priority**: Local cache first (faster), then MinIO (if missing)
- **Fallback**: If MinIO is not configured or unavailable, code still works locally
- **Automatic**: No code changes needed in data-using code, transparent access

---

## 6. CI/CD Benefits

### Before (Local Volumes):
- ❌ Persistent volume conflicts in CI/CD
- ❌ Data lost between pipeline runs
- ❌ No data sharing between environments

### After (MinIO):
- ✅ All data persisted in MinIO bucket
- ✅ Data automatically shared across services
- ✅ Works in local dev, Docker Compose, and Kubernetes
- ✅ Easy scaling: add new services without volume complexity

---

## 7. Troubleshooting

### MinIO Connection Issues:
```bash
# Check MinIO health in Docker Compose
docker-compose logs minio | grep health

# Check in K8s
kubectl logs -l app=minio
kubectl describe svc minio

# Verify connectivity
curl http://localhost:9000/minio/health/live  # local
kubectl exec <pipeline-pod> -- curl http://minio:9000/minio/health/live  # K8s
```

### Missing Data in MinIO:
```bash
# Check bucket exists
# MinIO console: http://localhost:9001 → Buckets → smart-ecommerce

# Check files in bucket
mc ls minio/smart-ecommerce/output/
```

### Local Cache Not Being Populated:
- Ensure `DATA_PATH` env var is set (default: `/app/data`)
- Ensure write permissions in container
- Check Docker logs: `docker-compose logs agents | grep -i storage`

---

## 8. Configuration Checklist

- [ ] `.env` file created and configured
- [ ] MinIO credentials set in `.env`
- [ ] `docker-compose up -d` runs successfully
- [ ] MinIO console accessible at http://localhost:9001
- [ ] Pipeline runs and outputs appear in MinIO bucket
- [ ] Dashboard loads data from MinIO
- [ ] All Docker images built with `storage.py` included
- [ ] K8s ConfigMap and Secret applied
- [ ] K8s deployments running with MinIO env vars
- [ ] No local volume mount errors in CI/CD logs

---

## 9. Advanced: Custom MinIO Configuration

### Use external MinIO service:
```env
MINIO_ENDPOINT=s3.mycompany.com:9000
MINIO_ACCESS_KEY=your_access_key
MINIO_SECRET_KEY=your_secret_key
MINIO_BUCKET=my-bucket
MINIO_SECURE=true
```

### Disable MinIO (local-only):
```env
MINIO_ENDPOINT=
```
(Code will still work, using only local storage)

### Debug MinIO calls:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
# Now all MinIO operations are logged
```

---

## 10. Next Steps

1. **Test locally**: `docker-compose up && docker-compose logs -f`
2. **Deploy to K8s**: `kubectl apply -f infra/k8s/`
3. **Monitor MinIO**: `kubectl port-forward svc/minio-lb 9001:9001`
4. **Validate outputs**: Check bucket contents after pipeline runs

