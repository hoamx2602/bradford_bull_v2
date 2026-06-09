"""Storage backend factory."""
from __future__ import annotations

from app.config import get_settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorage


def get_storage() -> StorageBackend:
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalStorage(settings.storage_dir)
    # Add: if settings.storage_backend == "s3": return S3Storage(...)
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.storage_backend}")
