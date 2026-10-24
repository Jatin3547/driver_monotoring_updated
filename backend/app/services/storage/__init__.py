"""Storage service package."""

from app.services.storage.base import StorageProvider
from app.services.storage.local import LocalStorageProvider
from app.services.storage.cloud_stub import CloudStorageProvider

_local_provider: LocalStorageProvider | None = None


def get_storage_provider() -> LocalStorageProvider:
    global _local_provider
    if _local_provider is None:
        _local_provider = LocalStorageProvider()
    return _local_provider


__all__ = [
    "StorageProvider",
    "LocalStorageProvider",
    "CloudStorageProvider",
    "get_storage_provider",
]
