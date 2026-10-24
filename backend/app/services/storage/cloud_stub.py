"""Cloud Object Storage Stub & Future Queue Interface.

Provides a provider-neutral interface for future AWS S3, Google Cloud Storage,
or Azure Blob Storage integration. In Phase 3, this maintains the contract and
tracks retryable queue states ('pending', 'uploading', 'uploaded', 'failed', 'not_applicable')
without requiring external cloud credentials or cloud dependencies today.
"""

import logging
from pathlib import Path

from app.services.storage.base import StorageProvider

logger = logging.getLogger("fleet.storage.cloud")


class CloudStorageProvider(StorageProvider):
    """Stub implementation of Cloud Storage for future cloud syncing."""

    def __init__(self, bucket_name: str = "fleetguard-evidence-archive"):
        self.bucket_name = bucket_name

    def store_file(self, source_path: Path, destination_name: str) -> str:
        # Future implementation will upload to S3/GCS using presigned or IAM client
        cloud_uri = f"s3://{self.bucket_name}/{destination_name}"
        logger.info("Cloud storage stub: staged '%s' as '%s'", source_path, cloud_uri)
        return cloud_uri

    def get_file_path(self, storage_reference: str) -> Path | None:
        # In cloud mode, files may be fetched to a local cache on demand
        return None

    def delete_file(self, storage_reference: str) -> bool:
        logger.info("Cloud storage stub: deleted '%s'", storage_reference)
        return True

    def exists(self, storage_reference: str) -> bool:
        return True

    def get_total_usage_bytes(self) -> int:
        return 0
