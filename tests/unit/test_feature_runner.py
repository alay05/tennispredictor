from __future__ import annotations

from tennisprediction.domain.models import CanonicalMatch, CanonicalRanking, SourceLineage
from tennisprediction.features.runner import build_feature_snapshots


def _lineage(*, file_name: str, row_number: int) -> SourceLineage:
    return SourceLineage(
        source_repo="JeffSackmann/tennis_atp",
        source_commit_sha="abcdef1",
        source_file_path=file_name,
        source_row_number=row_number,
        source_snapshot_root="/tmp/raw-snapshot",
    )


def _match(
    *,
    match_id: str,
    winner_id: int,
    loser_id: int,
    row_number: int,
) -> CanonicalMatch:
    return CanonicalMatch(
        canonical_match_id=match_id,
        canonical_tournament_id="tournament:synthetic:example-open:20240115",
        winner_canonical_player_id=f"player:sackmann:{winner_id}",
        loser_canonical_player_id=f"player:sackmann:{loser_id}",
        source_tourney_id="2024-001",
        surface="Hard",
        tourney_name="Example Open",
        tourney_level="A",
        tourney_date="20240115",
        round_name="R32",
        best_of=3,
        score="6-4 6-4",
        lineage=_lineage(file_name="atp_matches_2024.csv", row_number=row_number),
    )


def _ranking(
    *,
    player_id: int,
    ranking_date: str,
    rank: int,
    points: int,
    row_number: int,
) -> CanonicalRanking:
    return CanonicalRanking(
        canonical_ranking_id=f"ranking:synthetic:{player_id}:{ranking_date}",
        canonical_player_id=f"player:sackmann:{player_id}",
        ranking_date=ranking_date,
        rank=rank,
        points=points,
        lineage=_lineage(file_name="atp_rankings_2024.csv", row_number=row_number),
    )


def test_build_feature_snapshots_emits_pre_match_rank_and_context_before_cohort_updates() -> None:
    result = build_feature_snapshots(
        matches=[
            _match(
                match_id="match:synthetic:example-open:20240115:1",
                winner_id=1,
                loser_id=2,
                row_number=2,
            ),
            _match(
                match_id="match:synthetic:example-open:20240115:2",
                winner_id=1,
                loser_id=3,
                row_number=3,
            ),
        ],
        rankings=[
            _ranking(player_id=1, ranking_date="20240101", rank=12, points=1200, row_number=2),
            _ranking(player_id=1, ranking_date="20240115", rank=8, points=1450, row_number=3),
            _ranking(player_id=1, ranking_date="20240122", rank=5, points=1700, row_number=4),
            _ranking(player_id=2, ranking_date="20240115", rank=15, points=1100, row_number=5),
            _ranking(player_id=3, ranking_date="20240115", rank=20, points=900, row_number=6),
        ],
        feature_version="v0-test",
    )

    player_one_snapshots = [
        snapshot
        for snapshot in result.player_snapshots
        if snapshot.canonical_player_id == "player:sackmann:1"
    ]
    assert len(player_one_snapshots) == 2
    assert {snapshot.rank for snapshot in player_one_snapshots} == {8}
    assert {snapshot.previous_rank for snapshot in player_one_snapshots} == {12}
    assert {snapshot.ranking_change for snapshot in player_one_snapshots} == {-4}
    assert {snapshot.surface for snapshot in player_one_snapshots} == {"Hard"}
    assert {snapshot.tourney_level for snapshot in player_one_snapshots} == {"A"}
    assert {snapshot.round_name for snapshot in player_one_snapshots} == {"R32"}
    assert {snapshot.best_of for snapshot in player_one_snapshots} == {3}

    assert len(result.player_snapshots) == 4
    assert len(result.differential_rows) == 2

    first_row = result.differential_rows[0]
    second_row = result.differential_rows[1]
    assert first_row.feature_version == "v0-test"
    assert first_row.as_of_date == "20240115"
    assert first_row.player_a_side == "A"
    assert first_row.player_b_side == "B"
    assert first_row.rank_diff == -7
    assert first_row.rank_points_diff == 350
    assert second_row.rank_diff == -12
    assert second_row.rank_points_diff == 550
