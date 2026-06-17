from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from tennisprediction.ingestion.manifests import SourceManifest, sha256_file
from tennisprediction.ingestion.storage_layout import RawSnapshotLayout


def test_manifest_records_commit_checksum_attribution_and_license(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "data" / "raw" / "tennis_atp" / "abcdef1"
    snapshot_root.mkdir(parents=True)
    source_file = snapshot_root / "atp_matches_2024.csv"
    source_file.write_text("tourney_id,winner_name\n2024-001,Player A\n", encoding="utf-8")
    acquired_at = datetime(2026, 6, 16, 12, 0, tzinfo=UTC)

    manifest = SourceManifest.model_validate(
        {
            "source_repo": "JeffSackmann/tennis_atp",
            "commit_sha": "abcdef1",
            "acquired_at": acquired_at,
            "snapshot_root": snapshot_root,
            "attribution_text": "Jeff Sackmann tennis_atp",
            "license_name": "CC BY-NC-SA 4.0",
            "license_text": "Attribution required",
            "files": [
                {
                    "relative_path": "atp_matches_2024.csv",
                    "sha256": sha256_file(source_file),
                    "source_url": "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/abcdef1/atp_matches_2024.csv",
                    "source_path": "atp_matches_2024.csv",
                    "size_bytes": source_file.stat().st_size,
                }
            ],
        }
    )

    assert manifest.commit_sha == "abcdef1"
    assert manifest.acquired_at == acquired_at
    assert manifest.attribution_text == "Jeff Sackmann tennis_atp"
    assert manifest.license_name == "CC BY-NC-SA 4.0"
    assert manifest.license_text == "Attribution required"
    assert manifest.verify_checksums() == {Path("atp_matches_2024.csv"): True}


def test_raw_snapshot_layout_is_deterministic_and_immutable(tmp_path: Path) -> None:
    layout = RawSnapshotLayout(tmp_path / "data" / "raw" / "tennis_atp")

    snapshot_dir = layout.ensure_new_snapshot_dir("abcdef1")
    assert snapshot_dir == tmp_path / "data" / "raw" / "tennis_atp" / "abcdef1"
    assert layout.file_path("abcdef1", "players.csv") == snapshot_dir / "players.csv"

    try:
        layout.ensure_new_snapshot_dir("abcdef1")
    except FileExistsError:
        pass
    else:
        raise AssertionError("expected immutable snapshot directory creation to fail")
