from __future__ import annotations

from pathlib import Path

from tennisprediction.ingestion.quarantine import classify_row, split_validated_snapshot
from tennisprediction.ingestion.sackmann_fetcher import SackmannSourceClient
from tennisprediction.ingestion.storage_layout import RawSnapshotLayout
from tennisprediction.ingestion.validation import validate_snapshot


def _validated_matches_snapshot(tmp_path: Path, file_name: str, content: str):
    layout = RawSnapshotLayout(tmp_path / "raw")
    client = SackmannSourceClient(layout=layout)
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / file_name
    source_file.write_text(content, encoding="utf-8")
    manifest = client.materialize_local_snapshot(
        commit_sha="abcdef1",
        source_files={file_name: source_file},
        attribution_text="Jeff Sackmann tennis_atp",
        license_name="CC BY-NC-SA 4.0",
        license_text="Attribution required",
    )
    return validate_snapshot(manifest)


def test_non_atp_file_patterns_are_rejected_before_candidates_are_produced(tmp_path: Path) -> None:
    decision = classify_row("atp_matches_qual_chall_2024.csv", {})
    assert decision.accepted is False
    assert decision.reason == "out_of_scope_file_family"

    validated = _validated_matches_snapshot(
        tmp_path,
        "atp_matches_2024.csv",
        (
            "tourney_id,surface,tourney_name,tourney_date,tourney_level,winner_id,loser_id,score,best_of,round,comment\n"
            "2024-001,Hard,Example,20240115,A,1,2,6-4 6-4,3,R32,\n"
        ),
    )
    partitioned = split_validated_snapshot(validated)
    assert len(partitioned.accepted_rows["atp_matches_2024.csv"]) == 1
    assert partitioned.quarantined_rows == {}


def test_excluded_match_types_are_quarantined_with_reason_codes(tmp_path: Path) -> None:
    validated = _validated_matches_snapshot(
        tmp_path,
        "atp_matches_2024.csv",
        (
            "tourney_id,surface,tourney_name,tourney_date,tourney_level,winner_id,loser_id,score,best_of,round,comment\n"
            "2024-001,Hard,Example,20240115,A,1,2,6-4 6-4,3,Q1,\n"
            "2024-002,Clay,Example 2,20240116,A,3,4,6-0 1-0 ret,3,R32,Retired\n"
        ),
    )

    partitioned = split_validated_snapshot(validated)

    assert partitioned.accepted_rows == {}
    reasons = {
        row["_quarantine_reason"] for row in partitioned.quarantined_rows["atp_matches_2024.csv"]
    }
    assert reasons == {"excluded_qualifier", "excluded_retired"}


def test_rankings_decade_archive_files_stay_in_scope(tmp_path: Path) -> None:
    validated = _validated_matches_snapshot(
        tmp_path,
        "atp_rankings_90s.csv",
        "ranking_date,rank,player,points\n19990111,1,1,1000\n",
    )

    assert "atp_rankings_90s.csv" in validated.rows_by_file
