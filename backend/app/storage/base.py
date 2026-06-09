"""Storage abstraction.

`save` returns an opaque key; `local_path` materialises that key as a real file
on disk (ultralytics/opencv need a path). An S3 backend would download to a temp
file inside `local_path`, keeping callers unchanged.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO


class StorageBackend(ABC):
    @abstractmethod
    def save(self, fileobj: BinaryIO, filename: str) -> str:
        """Persist a stream, return a storage key."""

    @abstractmethod
    def local_path(self, key: str) -> Path:
        """Return a local filesystem path for the key (downloading if remote)."""

    @abstractmethod
    def delete(self, key: str) -> None:
        ...
