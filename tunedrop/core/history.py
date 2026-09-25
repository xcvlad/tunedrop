"""Registro de lo ya descargado para no repetir canciones."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from .settings import data_dir


class History:
    def __init__(self, path: Path | None = None):
        self._path = path or data_dir() / "history.json"
        self._lock = threading.Lock()
        try:
            self._items: dict[str, dict] = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self._items = {}

    @staticmethod
    def key(source: str, track_id: str) -> str:
        return f"{source}:{track_id}"

    def file_for(self, source: str, track_id: str) -> Path | None:
        """Ruta del archivo descargado, o None si no existe (borrado o movido: se puede repetir)."""
        entry = self._items.get(self.key(source, track_id))
        if not entry:
            return None
        path = Path(entry.get("file", ""))
        return path if path.is_file() else None

    def contains(self, source: str, track_id: str) -> bool:
        return self.file_for(source, track_id) is not None

    def add(self, source: str, track_id: str, file: Path, title: str) -> None:
        with self._lock:
            self._items[self.key(source, track_id)] = {
                "file": str(file), "title": title, "at": int(time.time()),
            }
            tmp = self._path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._items, indent=1, ensure_ascii=False), encoding="utf-8")
            tmp.replace(self._path)
