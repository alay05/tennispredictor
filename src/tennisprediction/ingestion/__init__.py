"""Ingestion primitives for raw Jeff Sackmann ATP source snapshots."""

from tennisprediction.ingestion.manifests import SourceFileEntry, SourceManifest
from tennisprediction.ingestion.sackmann_fetcher import SackmannSourceClient
from tennisprediction.ingestion.storage_layout import RawSnapshotLayout

__all__ = [
    "RawSnapshotLayout",
    "SackmannSourceClient",
    "SourceFileEntry",
    "SourceManifest",
]
