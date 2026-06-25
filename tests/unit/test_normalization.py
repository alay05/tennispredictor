from __future__ import annotations

from pathlib import Path

import duckdb

from tennisprediction.domain.normalization import normalize_snapshot
from tennisprediction.ingestion.sackmann_fetcher import SackmannSourceClient
from tennisprediction.ingestion.storage_layout import RawSnapshotLayout
from tennisprediction.ingestion.validation import validate_snapshot
from tennisprediction.storage.duckdb import persist_canonical_snapshot


def _build_validated_snapshot(tmp_path: Path):
    layout = RawSnapshotLayout(tmp_path / "raw")
    client = SackmannSourceClient(layout=layout)
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    files = {
        "atp_players.csv": ("player_id,name_first,name_last\n1,Roger,Federer\n2,Rafael,Nadal\n"),
        "atp_rankings_2024.csv": (
            "ranking_date,rank,player,points\n20240115,1,1,1000\n20240115,2,2,900\n"
        ),
        "atp_matches_2024.csv": (
            "tourney_id,surface,tourney_name,tourney_date,tourney_level,winner_id,loser_id,score,best_of,round,comment\n"
            "2024-001,Hard,Example Open,20240115,A,1,2,6-4 6-4,3,R32,\n"
            "2024-001,Hard,Example Open,20240115,A,2,1,6-4 6-4,3,Q1,\n"
        ),
        "atp_matchstats_2024.csv": (
            "match_id,1stWon1,1stWon2,ace1,ace2,svpt1,svpt2\n1001,20,15,5,3,40,38\n"
        ),
        "wta_matches_2024.csv": "ignored\nvalue\n",
    }

    source_files: dict[str, Path] = {}
    for name, content in files.items():
        path = source_dir / name
        path.write_text(content, encoding="utf-8")
        source_files[name] = path

    manifest = client.materialize_local_snapshot(
        commit_sha="abcdef1",
        source_files=source_files,
        attribution_text="Jeff Sackmann tennis_atp",
        license_name="CC BY-NC-SA 4.0",
        license_text="Attribution required",
    )
    return validate_snapshot(manifest)


def test_normalization_reuses_source_player_ids_and_preserves_lineage(tmp_path: Path) -> None:
    validated = _build_validated_snapshot(tmp_path)

    canonical = normalize_snapshot(validated)

    assert canonical.players[0].canonical_player_id == "player:sackmann:1"
    assert canonical.players[1].canonical_player_id == "player:sackmann:2"
    assert canonical.players[0].lineage.source_commit_sha == validated.manifest.commit_sha
    assert canonical.players[0].lineage.source_file_path == "atp_players.csv"
    assert canonical.tournaments[0].canonical_tournament_id.startswith("tournament:synthetic:")
    assert canonical.matches[0].canonical_match_id.startswith("match:synthetic:")
    assert canonical.rankings[0].canonical_ranking_id.startswith("ranking:synthetic:")
    assert canonical.match_stats[0].canonical_match_stat_id == "match-stat:sackmann:1001"


def test_normalization_excludes_quarantined_rows_and_persists_canonical_tables(
    tmp_path: Path,
) -> None:
    validated = _build_validated_snapshot(tmp_path)

    canonical = normalize_snapshot(validated)

    assert len(canonical.matches) == 1
    assert canonical.quarantined_files["wta_matches_2024.csv"].reason == "out_of_scope_file_family"
    assert canonical.quarantined_rows["atp_matches_2024.csv"][0]["_quarantine_reason"] == (
        "excluded_qualifier"
    )

    database_path = persist_canonical_snapshot(
        canonical,
        database_path=tmp_path / "duckdb" / "canonical.duckdb",
    )

    with duckdb.connect(str(database_path)) as connection:
        assert connection.execute("select count(*) from canonical_players").fetchone() == (2,)
        assert connection.execute("select count(*) from canonical_matches").fetchone() == (1,)
        assert connection.execute("select count(*) from canonical_tournaments").fetchone() == (1,)
        assert connection.execute("select count(*) from canonical_rankings").fetchone() == (2,)
        assert connection.execute("select count(*) from canonical_match_stats").fetchone() == (1,)
