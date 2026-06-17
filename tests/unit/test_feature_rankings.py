from __future__ import annotations

from tennisprediction.domain.models import CanonicalRanking, SourceLineage
from tennisprediction.features.rankings import attach_prior_rankings


def _lineage(*, row_number: int) -> SourceLineage:
    return SourceLineage(
        source_repo="JeffSackmann/tennis_atp",
        source_commit_sha="abcdef1",
        source_file_path="atp_rankings_2024.csv",
        source_row_number=row_number,
        source_snapshot_root="/tmp/raw-snapshot",
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
        lineage=_lineage(row_number=row_number),
    )


def test_attach_prior_rankings_uses_backward_as_of_only() -> None:
    ranking = attach_prior_rankings(
        canonical_player_id="player:sackmann:1",
        as_of_date="20240120",
        rankings=[
            _ranking(player_id=1, ranking_date="20240101", rank=12, points=1200, row_number=2),
            _ranking(player_id=1, ranking_date="20240115", rank=8, points=1450, row_number=3),
            _ranking(player_id=1, ranking_date="20240201", rank=5, points=1700, row_number=4),
            _ranking(player_id=2, ranking_date="20240115", rank=20, points=900, row_number=5),
        ],
    )

    assert ranking.rank == 8
    assert ranking.rank_points == 1450
    assert ranking.previous_rank == 12
    assert ranking.previous_rank_points == 1200
    assert ranking.previous_ranking_date == "20240101"
    assert ranking.ranking_change == -4
    assert ranking.ranking_age_days == 5
    assert ranking.rank_missing is False
    assert ranking.rank_points_missing is False


def test_attach_prior_rankings_computes_ranking_change_from_immediately_previous_row() -> None:
    ranking = attach_prior_rankings(
        canonical_player_id="player:sackmann:1",
        as_of_date="20240115",
        rankings=[
            _ranking(player_id=1, ranking_date="20240101", rank=20, points=900, row_number=2),
            _ranking(player_id=1, ranking_date="20240108", rank=14, points=1100, row_number=3),
            _ranking(player_id=1, ranking_date="20240115", rank=10, points=1300, row_number=4),
        ],
    )

    assert ranking.rank == 10
    assert ranking.rank_points == 1300
    assert ranking.previous_rank == 14
    assert ranking.previous_rank_points == 1100
    assert ranking.previous_ranking_date == "20240108"
    assert ranking.ranking_change == -4
