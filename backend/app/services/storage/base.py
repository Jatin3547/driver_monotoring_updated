"""Provider-neutral storage abstraction for FLEETGUARD evidence files.

Defines the contract for saving, retrieving, verifying, and deleting
evidence media (MP4 videos and JPEG snapshots). Local filesystem is
the primary implementation for Phase 3; cloud object storage (S3/GCS/Azure)
plugs in via the same interface in future phases.
"""

from abc import ABC, abstractmethod
from pathlib import Path


class StorageProvider(ABC):

    @abstractmethod
    def store_file(self, source_path: Path, destination_name: str) -> str:
        """Stores a file and returns its storage reference / identifier."""
        pass

    @abstractmethod
    def get_file_path(self, storage_reference: str) -> Path | None:
        """Returns the local Path to the file, or None if not found."""
        pass

    @abstractmethod
    def delete_file(self, storage_reference: str) -> bool:
        """Deletes a file given its storage reference. Returns True if deleted."""
        pass

    @abstractmethod
    def exists(self, storage_reference: str) -> bool:
        """Returns True if the stored file exists."""
        pass

    @abstractmethod
    def get_total_usage_bytes(self) -> int:
        """Calculates total bytes occupied by stored evidence files."""
        pass
