from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SourceFileEntry(BaseModel):
    relative_path: Path
    sha256: str = Field(min_length=64, max_length=64)
    source_url: str
    source_path: str
    size_bytes: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)


class SourceManifest(BaseModel):
    source_repo: str
    commit_sha: str
    acquired_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    snapshot_root: Path
    attribution_text: str
    license_name: str
    license_text: str
    files: list[SourceFileEntry]

    model_config = ConfigDict(frozen=True)

    def file_path(self, entry: SourceFileEntry) -> Path:
        return self.snapshot_root / entry.relative_path

    def verify_checksums(self) -> dict[Path, bool]:
        return {
            entry.relative_path: sha256_file(self.file_path(entry)) == entry.sha256
            for entry in self.files
        }
