"""Compatibility export for storage backend lookup."""

from app.integrations.storage.service import get_storage_backend

__all__ = ["get_storage_backend"]
