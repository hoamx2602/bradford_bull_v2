"""Local-filesystem storage backend."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path
from typing import BinaryIO


class LocalStorage:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, fileobj: BinaryIO, filename: str) -> str:
        suffix = Path(filename).suffix.lower()
        key = f"{uuid.uuid4().hex}{suffix}"
        dest = self.root / key
        with dest.open("wb") as out:
            shutil.copyfileobj(fileobj, out, length=1024 * 1024)
        return key

    def local_path(self, key: str) -> Path:
        return self.root / key

    def delete(self, key: str) -> None:
        p = self.root / key
        if p.exists():
            p.unlink()
