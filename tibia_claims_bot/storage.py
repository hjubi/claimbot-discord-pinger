"""Persists the last raw API payload to disk so state survives restarts."""

from __future__ import annotations

import json
import logging
import os
import tempfile
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SnapshotStore:
    """Simple, atomic, file-based JSON snapshot store."""

    def __init__(self, path: str) -> None:
        self._path = path
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)

    def load(self) -> Optional[dict[str, Any]]:
        if not os.path.exists(self._path):
            return None
        try:
            with open(self._path, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read snapshot file %s (%s); starting fresh.", self._path, exc)
            return None

    def save(self, payload: dict[str, Any]) -> None:
        directory = os.path.dirname(self._path) or "."
        fd, tmp_path = tempfile.mkstemp(dir=directory, prefix=".snapshot_", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(payload, fh, ensure_ascii=False)
            os.replace(tmp_path, self._path)
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
