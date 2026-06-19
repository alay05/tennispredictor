from __future__ import annotations

from pathlib import Path

import pytest

from tennisprediction.ingestion.sackmann_fetcher import SackmannSourceClient
from tennisprediction.ingestion.storage_layout import RawSnapshotLayout
from tennisprediction.ingestion.validation import ValidatedSnapshot, validate_snapshot


def _build_manifest(tmp_path: Path, file_name: str, content: str):
    layout = RawSnapshotLayout(tmp_path / "raw")
    client = SackmannSourceClient(layout=layout)
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / file_name
    source_file.write_text(content, encoding="utf-8")
    return client.materialize_local_snapshot(
        commit_sha="abcdef1",
        source_files={file_name: source_file},
        attribution_text="Jeff Sackmann tennis_atp",
        license_name="CC BY-NC-SA 4.0",
        license_text="Attribution required",
    )


def test_validation_fails_on_missing_required_columns(tmp_path: Path) -> None:
    manifest = _build_manifest(
        tmp_path,
        "atp_matches_2024.csv",
        (
            "tourney_id,surface,tourney_name,tourney_date,tourney_level,winner_id,score,best_of,round\n"
            "2024-001,Hard,Example,20240115,A,1,6-4 6-4,3,R32\n"
        ),
    )

    with pytest.raises(ValueError, match="missing required columns"):
        validate_snapshot(manifest)


def test_validation_fails_when_parse_rules_drift(tmp_path: Path) -> None:
    manifest = _build_manifest(
        tmp_path,
        "atp_rankings_2024.csv",
        "ranking_date,rank,player,points\n2024-01-15,1,1,1000\n",
    )

    with pytest.raises(ValueError, match="must parse as YYYYMMDD date"):
        validate_snapshot(manifest)


def test_validation_returns_validated_snapshot_before_downstream_use(tmp_path: Path) -> None:
    manifest = _build_manifest(
        tmp_path,
        "atp_players.csv",
        "player_id,name_first,name_last\n1,Roger,Federer\n",
    )

    validated = validate_snapshot(manifest)

    assert isinstance(validated, ValidatedSnapshot)
    assert validated.rows_by_file["atp_players.csv"][0]["name_last"] == "Federer"


def test_validation_tracks_out_of_scope_files_for_quarantine(tmp_path: Path) -> None:
    layout = RawSnapshotLayout(tmp_path / "raw")
    client = SackmannSourceClient(layout=layout)
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    players_file = source_dir / "atp_players.csv"
    players_file.write_text("player_id,name_first,name_last\n1,Roger,Federer\n", encoding="utf-8")
    wta_file = source_dir / "wta_matches_2024.csv"
    wta_file.write_text("ignored\nvalue\n", encoding="utf-8")

    manifest = client.materialize_local_snapshot(
        commit_sha="abcdef1",
        source_files={
            "atp_players.csv": players_file,
            "wta_matches_2024.csv": wta_file,
        },
        attribution_text="Jeff Sackmann tennis_atp",
        license_name="CC BY-NC-SA 4.0",
        license_text="Attribution required",
    )

    validated = validate_snapshot(manifest)

    assert "atp_players.csv" in validated.rows_by_file
    assert validated.quarantined_files["wta_matches_2024.csv"].reason == "out_of_scope_file_family"
