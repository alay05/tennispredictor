from __future__ import annotations

import re
from pathlib import Path

from tennisprediction.config import REPO_ROOT

COMMIT_SHA_RE = re.compile(r"^[0-9a-f]{7,40}$")


class RawSnapshotLayout:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (REPO_ROOT / "data" / "raw" / "tennis_atp")

    @staticmethod
    def validate_commit_sha(commit_sha: str) -> str:
        normalized = commit_sha.strip().lower()
        if not COMMIT_SHA_RE.fullmatch(normalized):
            msg = "commit_sha must be a lowercase git commit SHA, not a branch name"
            raise ValueError(msg)
        return normalized

    def snapshot_dir(self, commit_sha: str) -> Path:
        return self.root / self.validate_commit_sha(commit_sha)

    def file_path(self, commit_sha: str, relative_path: str | Path) -> Path:
        return self.snapshot_dir(commit_sha) / Path(relative_path)

    def ensure_new_snapshot_dir(self, commit_sha: str) -> Path:
        snapshot_dir = self.snapshot_dir(commit_sha)
        if snapshot_dir.exists():
            msg = f"snapshot already exists for commit {commit_sha}"
            raise FileExistsError(msg)
        snapshot_dir.mkdir(parents=True, exist_ok=False)
        return snapshot_dir
