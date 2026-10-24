"""Local filesystem storage provider for Phase 3 evidence files.

Stores videos and snapshots on disk outside of SQLite database,
prevents path traversal, and computes storage footprint.
"""

import logging
import os
import shutil
from pathlib import Path

from app.core.config import settings
from app.services.storage.base import StorageProvider

logger = logging.getLogger("fleet.storage.local")


class LocalStorageProvider(StorageProvider):

    def __init__(self, base_dir: Path | str | None = None):
        self.base_dir = Path(base_dir or settings.evidence_storage_dir).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve_safe_path(self, relative_or_abs_path: str) -> Path:
        """Resolves path and enforces that it stays strictly within base_dir."""
        raw_path = Path(relative_or_abs_path)
        if raw_path.is_absolute():
            resolved = raw_path.resolve()
        else:
            resolved = (self.base_dir / raw_path).resolve()

        # Prevent path traversal attacks
        try:
            resolved.relative_to(self.base_dir)
        except ValueError:
            raise ValueError(f"Path traversal detected: '{relative_or_abs_path}' resolves outside storage directory.")
        return resolved

    def store_file(self, source_path: Path, destination_name: str) -> str:
        dest_path = self._resolve_safe_path(destination_name)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.resolve() != dest_path:
            shutil.copy2(source_path, dest_path)
        return str(dest_path)

    def get_file_path(self, storage_reference: str) -> Path | None:
        try:
            path = self._resolve_safe_path(storage_reference)
            return path if path.exists() else None
        except ValueError:
            return None

    def delete_file(self, storage_reference: str) -> bool:
        try:
            path = self._resolve_safe_path(storage_reference)
            if path.exists() and path.is_file():
                path.unlink()
                logger.info("Deleted evidence file: %s", path)
                return True
            return False
        except Exception as e:
            logger.warning("Error deleting evidence file '%s': %s", storage_reference, e)
            return False

    def exists(self, storage_reference: str) -> bool:
        try:
            path = self._resolve_safe_path(storage_reference)
            return path.exists() and path.is_file()
        except ValueError:
            return False

    def get_total_usage_bytes(self) -> int:
        total = 0
        if not self.base_dir.exists():
            return 0
        for entry in self.base_dir.rglob("*"):
            if entry.is_file():
                try:
                    total += entry.stat().st_size
                except OSError:
                    pass
        return total
