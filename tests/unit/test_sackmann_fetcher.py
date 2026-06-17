from __future__ import annotations

from pathlib import Path

import pytest

from tennisprediction.ingestion.sackmann_fetcher import SackmannSourceClient
from tennisprediction.ingestion.storage_layout import RawSnapshotLayout


def test_fetcher_requires_explicit_commit_sha(tmp_path: Path) -> None:
    client = SackmannSourceClient(layout=RawSnapshotLayout(tmp_path / "raw"))

    with pytest.raises(ValueError, match="commit_sha must be a lowercase git commit SHA"):
        client.build_source_url("main", "atp_players.csv")


def test_materialize_and_load_snapshot_returns_manifest_backed_files(tmp_path: Path) -> None:
    layout = RawSnapshotLayout(tmp_path / "raw")
    client = SackmannSourceClient(layout=layout)
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    players_csv = source_dir / "atp_players.csv"
    players_csv.write_text("player_id,name_first,name_last\n1,Roger,Federer\n", encoding="utf-8")

    manifest = client.materialize_local_snapshot(
        commit_sha="abcdef1",
        source_files={"atp_players.csv": players_csv},
        attribution_text="Jeff Sackmann tennis_atp",
        license_name="CC BY-NC-SA 4.0",
        license_text="Attribution required",
    )

    assert manifest.commit_sha == "abcdef1"
    assert manifest.files[0].source_path == "atp_players.csv"
    assert manifest.verify_checksums() == {Path("atp_players.csv"): True}

    loaded_manifest = client.load_snapshot(
        commit_sha="abcdef1",
        attribution_text="Jeff Sackmann tennis_atp",
        license_name="CC BY-NC-SA 4.0",
        license_text="Attribution required",
    )

    assert loaded_manifest.snapshot_root == manifest.snapshot_root
    assert loaded_manifest.files[0].sha256 == manifest.files[0].sha256
