import json
import os
import pickle
import logging
from pathlib import Path
from typing import Any, Union, Optional

import pandas as pd

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    Minio = None
    S3Error = Exception

logger = logging.getLogger(__name__)

# Prefixes
RAW_PREFIX = "raw/"
PROCESSED_PREFIX = "processed/"
OUTPUT_PREFIX = "output/"


class StorageManager:
    def __init__(
        self,
        base_path: Optional[Union[str, Path]] = None,
        bucket: str = "smart-ecommerce",
    ):
        # -------------------------
        # Local storage setup
        # -------------------------
        self.base_path = Path(base_path or "/tmp")

        # -------------------------
        # MinIO config (env-driven)
        # -------------------------
        self.endpoint = os.getenv("MINIO_ENDPOINT")
        self.bucket = os.getenv("MINIO_BUCKET", bucket)
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
        self.access_key = os.getenv("MINIO_ACCESS_KEY")
        self.secret_key = os.getenv("MINIO_SECRET_KEY")

        # -------------------------
        # MinIO availability flag
        # -------------------------
        self.use_minio = all([
            self.endpoint,
            self.bucket,
            self.access_key,
            self.secret_key,
            Minio is not None,
        ])

        self.client = None

        if self.use_minio:
            try:
                logger.info(f"Connecting to MinIO at {self.endpoint}, bucket={self.bucket}")

                self.client = Minio(
                    self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=self.secure,
                )

                # Ensure bucket exists
                if not self.client.bucket_exists(self.bucket):
                    self.client.make_bucket(self.bucket)
                    logger.info(f"Created bucket: {self.bucket}")
                else:
                    logger.info(f"Bucket exists: {self.bucket}")

            except Exception as e:
                logger.warning(f"MinIO init failed, falling back to local storage: {e}")
                self.use_minio = False
                self.client = None
        else:
            logger.info("MinIO not configured — using local filesystem only")

    #exist method 
    def exists(self, path: Union[str, Path], prefix: str = "") -> bool:
        local_path = self.local_path(path, prefix)

        if local_path.exists():
            return True

        if self.use_minio and self.client:
            try:
                self.client.stat_object(
                    self.bucket,
                    self._object_name(path, prefix)
                )
                return True
            except Exception:
                return False

        return False

    # =========================================================
    # Path utilities
    # =========================================================

    def local_path(self, path: Union[str, Path], prefix: str = "") -> Path:
        if self.base_path is None:
            self.base_path = Path("/tmp")

        if prefix:
            path = Path(prefix) / Path(path)
        else:
            path = Path(path)

        full_path = self.base_path / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        return full_path

    def _object_name(self, path: Union[str, Path], prefix: str = "") -> str:
        path = Path(path)

        if prefix:
            path = Path(prefix) / path

        return str(path.as_posix()).lstrip("/")

    # =========================================================
    # MinIO helpers
    # =========================================================

    def exists_remote(self, path: Union[str, Path], prefix: str = "") -> bool:
        if not self.use_minio or not self.client:
            return False

        try:
            self.client.stat_object(self.bucket, self._object_name(path, prefix))
            return True
        except Exception:
            return False

    def download_file(self, path: Union[str, Path], local_file: Path, prefix: str = "") -> Path:
        if not self.use_minio or not self.client:
            raise RuntimeError("MinIO not available")

        local_file.parent.mkdir(parents=True, exist_ok=True)

        self.client.fget_object(
            self.bucket,
            self._object_name(path, prefix),
            str(local_file),
        )

        return local_file

    def upload_file(self, path: Union[str, Path], local_file: Path, prefix: str = "") -> None:
        if not self.use_minio or not self.client:
            return

        if not local_file.exists():
            raise FileNotFoundError(local_file)

        self.client.fput_object(
            self.bucket,
            self._object_name(path, prefix),
            str(local_file),
        )

    # =========================================================
    # Core fetch logic (local + fallback)
    # =========================================================

    def fetch_local(self, path: Union[str, Path], prefix: str = "") -> Path:
        local_path = self.local_path(path, prefix)

        if local_path.exists():
            return local_path

        if self.use_minio and self.exists_remote(path, prefix):
            return self.download_file(path, local_path, prefix)

        raise FileNotFoundError(f"File not found: {path}")

    # =========================================================
    # DataFrame ops
    # =========================================================

    def save_dataframe(self, df: pd.DataFrame, path: Union[str, Path], prefix: str = "", **kwargs) -> Path:
        local_path = self.local_path(path, prefix)
        df.to_csv(local_path, index=False, **kwargs)
        self.upload_file(path, local_path, prefix)
        return local_path

    def load_dataframe(self, path: Union[str, Path], prefix: str = "", **kwargs) -> pd.DataFrame:
        local_path = self.fetch_local(path, prefix)
        return pd.read_csv(local_path, **kwargs)

    # =========================================================
    # JSON
    # =========================================================

    def save_json(self, data: Any, path: Union[str, Path], prefix: str = "", **kwargs) -> Path:
        local_path = self.local_path(path, prefix)

        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, **kwargs)

        self.upload_file(path, local_path, prefix)
        return local_path

    def load_json(self, path: Union[str, Path], prefix: str = "", **kwargs) -> Any:
        local_path = self.fetch_local(path, prefix)

        with open(local_path, "r", encoding="utf-8") as f:
            return json.load(f, **kwargs)

    # =========================================================
    # Pickle
    # =========================================================

    def save_pickle(self, obj: Any, path: Union[str, Path], prefix: str = "") -> Path:
        local_path = self.local_path(path, prefix)

        with open(local_path, "wb") as f:
            pickle.dump(obj, f)

        self.upload_file(path, local_path, prefix)
        return local_path

    def load_pickle(self, path: Union[str, Path], prefix: str = "") -> Any:
        local_path = self.fetch_local(path, prefix)

        with open(local_path, "rb") as f:
            return pickle.load(f)

    # =========================================================
    # Text
    # =========================================================

    def save_text(self, text: str, path: Union[str, Path], prefix: str = "", encoding: str = "utf-8") -> Path:
        local_path = self.local_path(path, prefix)

        local_path.write_text(text, encoding=encoding)

        self.upload_file(path, local_path, prefix)
        return local_path

    def load_text(self, path: Union[str, Path], prefix: str = "", encoding: str = "utf-8") -> str:
        local_path = self.fetch_local(path, prefix)
        return local_path.read_text(encoding=encoding)