from __future__ import annotations

import shutil
from datetime import UTC, datetime
from pathlib import Path

from tennisprediction.ingestion.manifests import SourceFileEntry, SourceManifest, sha256_file
from tennisprediction.ingestion.storage_layout import RawSnapshotLayout

RAW_BASE_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp"
SOURCE_REPO = "JeffSackmann/tennis_atp"


class SackmannSourceClient:
    def __init__(
        self,
        layout: RawSnapshotLayout | None = None,
        source_repo: str = SOURCE_REPO,
        raw_base_url: str = RAW_BASE_URL,
    ) -> None:
        self.layout = layout or RawSnapshotLayout()
        self.source_repo = source_repo
        self.raw_base_url = raw_base_url.rstrip("/")

    def build_source_url(self, commit_sha: str, relative_path: str | Path) -> str:
        normalized_commit = self.layout.validate_commit_sha(commit_sha)
        return f"{self.raw_base_url}/{normalized_commit}/{Path(relative_path).as_posix()}"

    def materialize_local_snapshot(
        self,
        *,
        commit_sha: str,
        source_files: dict[str, Path],
        attribution_text: str,
        license_name: str,
        license_text: str,
        acquired_at: datetime | None = None,
    ) -> SourceManifest:
        snapshot_root = self.layout.ensure_new_snapshot_dir(commit_sha)
        file_entries: list[SourceFileEntry] = []

        for relative_name, source_path in sorted(source_files.items()):
            relative_path = Path(relative_name)
            destination = snapshot_root / relative_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination)
            file_entries.append(
                SourceFileEntry(
                    relative_path=relative_path,
                    sha256=sha256_file(destination),
                    source_url=self.build_source_url(commit_sha, relative_path),
                    source_path=relative_path.as_posix(),
                    size_bytes=destination.stat().st_size,
                )
            )

        return SourceManifest(
            source_repo=self.source_repo,
            commit_sha=self.layout.validate_commit_sha(commit_sha),
            acquired_at=acquired_at or datetime.now(UTC),
            snapshot_root=snapshot_root,
            attribution_text=attribution_text,
            license_name=license_name,
            license_text=license_text,
            files=file_entries,
        )

    def load_snapshot(
        self,
        *,
        commit_sha: str,
        attribution_text: str,
        license_name: str,
        license_text: str,
    ) -> SourceManifest:
        snapshot_root = self.layout.snapshot_dir(commit_sha)
        if not snapshot_root.exists():
            msg = f"snapshot does not exist for commit {commit_sha}"
            raise FileNotFoundError(msg)

        file_entries: list[SourceFileEntry] = []
        for file_path in sorted(path for path in snapshot_root.rglob("*") if path.is_file()):
            relative_path = file_path.relative_to(snapshot_root)
            file_entries.append(
                SourceFileEntry(
                    relative_path=relative_path,
                    sha256=sha256_file(file_path),
                    source_url=self.build_source_url(commit_sha, relative_path),
                    source_path=relative_path.as_posix(),
                    size_bytes=file_path.stat().st_size,
                )
            )

        manifest = SourceManifest(
            source_repo=self.source_repo,
            commit_sha=self.layout.validate_commit_sha(commit_sha),
            acquired_at=datetime.now(UTC),
            snapshot_root=snapshot_root,
            attribution_text=attribution_text,
            license_name=license_name,
            license_text=license_text,
            files=file_entries,
        )

        if not all(manifest.verify_checksums().values()):
            msg = f"checksum verification failed for commit {commit_sha}"
            raise ValueError(msg)

        return manifest
