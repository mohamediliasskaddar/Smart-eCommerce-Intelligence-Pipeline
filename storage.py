import io
import json
import os
import pickle
import logging
from pathlib import Path
from typing import Any, Union

import pandas as pd

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:  # pragma: no cover
    Minio = None
    S3Error = Exception

logger = logging.getLogger(__name__)


def _parse_bool(value: Union[str, bool, None]) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    return str(value).strip().lower() not in {"0", "false", "no", "none"}


class StorageManager:
    """Handle local paths and optional MinIO object storage."""

    def __init__(
        self,
        base_path: Union[str, Path] = None,
        bucket_name: str = None,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        secure: Union[str, bool] = False,# was True
    ):
        self.base_path = Path(base_path or os.getenv("DATA_PATH", "/app/data"))
        self.base_path.mkdir(parents=True, exist_ok=True)

        self.bucket = bucket_name or os.getenv("MINIO_BUCKET", "smart-ecommerce")
        self.endpoint = endpoint or os.getenv("MINIO_ENDPOINT")
        self.access_key = access_key or os.getenv("MINIO_ACCESS_KEY")
        self.secret_key = secret_key or os.getenv("MINIO_SECRET_KEY")
        self.secure = _parse_bool(secure)
        self.use_minio = bool(self.endpoint and self.access_key and self.secret_key and Minio)
        self.client = None

        if self.use_minio:
            try:
                self.client = Minio(
                    self.endpoint,
                    access_key=self.access_key,
                    secret_key=self.secret_key,
                    secure=self.secure,
                )
                self._ensure_bucket()
            except Exception as exc:
                logger.warning("MinIO initialization failed; falling back to local storage: %s", exc)
                self.use_minio = False
                self.client = None

    def _object_name(self, path: Union[str, Path]) -> str:
        path = Path(path)
        try:
            relative = path.relative_to(self.base_path)
        except Exception:
            if path.is_absolute():
                relative = path.name
            else:
                relative = path
        return str(relative.as_posix()).lstrip("/")

    def _ensure_bucket(self) -> None:
        if not self.use_minio or self.client is None:
            return
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
        except Exception as exc:
            raise RuntimeError(f"Unable to ensure MinIO bucket '{self.bucket}': {exc}") from exc

    def local_path(self, path: Union[str, Path]) -> Path:
        local_path = self.base_path / Path(path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        return local_path

    def exists(self, path: Union[str, Path]) -> bool:
        local_path = self.local_path(path)
        if local_path.exists():
            return True
        if self.use_minio and self.client is not None:
            try:
                self.client.stat_object(self.bucket, self._object_name(path))
                return True
            except Exception:
                return False
        return False

    def fetch_local(self, path: Union[str, Path]) -> Path:
        local_path = self.local_path(path)
        if local_path.exists():
            return local_path
        if self.use_minio and self.client is not None and self.exists(path):
            return self.download_file(path, local_path)
        raise FileNotFoundError(f"File not found locally or in MinIO: {path}")

    def upload_file(self, path: Union[str, Path], local_file: Union[str, Path] = None) -> None:
        if not self.use_minio or self.client is None:
            return
        local_file = Path(local_file or self.local_path(path))
        if not local_file.exists():
            raise FileNotFoundError(f"Local file not found for upload: {local_file}")
        try:
            self.client.fput_object(self.bucket, self._object_name(path), str(local_file))
        except Exception as exc:
            logger.warning("Failed to upload %s to MinIO: %s", path, exc)

    def download_file(self, path: Union[str, Path], local_file: Union[str, Path] = None) -> Path:
        if not self.use_minio or self.client is None:
            raise RuntimeError("MinIO is not configured")
        local_file = Path(local_file or self.local_path(path))
        local_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.client.fget_object(self.bucket, self._object_name(path), str(local_file))
        except Exception as exc:
            raise RuntimeError(f"Failed to download {path} from MinIO: {exc}") from exc
        return local_file

    def save_dataframe(self, df: pd.DataFrame, path: Union[str, Path], **kwargs: Any) -> Path:
        local_path = self.local_path(path)
        df.to_csv(local_path, index=False, **kwargs)
        self.upload_file(path, local_path)
        return local_path

    def load_dataframe(self, path: Union[str, Path], **kwargs: Any) -> pd.DataFrame:
        local_path = self.fetch_local(path)
        return pd.read_csv(local_path, **kwargs)

    def save_json(self, data: Any, path: Union[str, Path], **kwargs: Any) -> Path:
        local_path = self.local_path(path)
        with open(local_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2, **kwargs)
        self.upload_file(path, local_path)
        return local_path

    def load_json(self, path: Union[str, Path], **kwargs: Any) -> Any:
        local_path = self.fetch_local(path)
        with open(local_path, encoding="utf-8") as f:
            return json.load(f, **kwargs)

    def save_pickle(self, obj: Any, path: Union[str, Path]) -> Path:
        local_path = self.local_path(path)
        with open(local_path, "wb") as f:
            pickle.dump(obj, f)
        self.upload_file(path, local_path)
        return local_path

    def load_pickle(self, path: Union[str, Path]) -> Any:
        local_path = self.fetch_local(path)
        with open(local_path, "rb") as f:
            return pickle.load(f)

    def save_text(self, text: str, path: Union[str, Path], encoding: str = "utf-8") -> Path:
        local_path = self.local_path(path)
        with open(local_path, "w", encoding=encoding) as f:
            f.write(text)
        self.upload_file(path, local_path)
        return local_path

    def load_text(self, path: Union[str, Path], encoding: str = "utf-8") -> str:
        local_path = self.fetch_local(path)
        return local_path.read_text(encoding=encoding)
