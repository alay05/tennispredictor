from __future__ import annotations

from tennisprediction.domain.models import (
    CanonicalMatch,
    CanonicalMatchStat,
    CanonicalRanking,
    SourceLineage,
)
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
    tourney_date: str,
    round_name: str,
    winner_id: int,
    loser_id: int,
    row_number: int,
) -> CanonicalMatch:
    return CanonicalMatch(
        canonical_match_id=match_id,
        canonical_tournament_id=f"tournament:synthetic:example-open:{tourney_date}",
        winner_canonical_player_id=f"player:sackmann:{winner_id}",
        loser_canonical_player_id=f"player:sackmann:{loser_id}",
        source_tourney_id="2024-001",
        surface="Hard",
        tourney_name="Example Open",
        tourney_level="A",
        tourney_date=tourney_date,
        round_name=round_name,
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


def _match_stat(
    *,
    source_match_id: int,
    first_won_player1: int,
    first_won_player2: int,
    ace_player1: int,
    ace_player2: int,
    serve_points_player1: int,
    serve_points_player2: int,
    row_number: int,
    file_name: str = "atp_matchstats_2024.csv",
) -> CanonicalMatchStat:
    return CanonicalMatchStat(
        canonical_match_stat_id=f"match-stat:sackmann:{source_match_id}",
        source_match_id=source_match_id,
        first_won_player1=first_won_player1,
        first_won_player2=first_won_player2,
        ace_player1=ace_player1,
        ace_player2=ace_player2,
        serve_points_player1=serve_points_player1,
        serve_points_player2=serve_points_player2,
        lineage=_lineage(file_name=file_name, row_number=row_number),
    )


def _synthetic_history(
    *,
    reorder_same_cohort: bool = False,
    include_cross_file_collision: bool = False,
) -> tuple[
    list[CanonicalMatch],
    list[CanonicalRanking],
    list[CanonicalMatchStat],
]:
    same_cohort_target_row = 5 if reorder_same_cohort else 4
    same_cohort_other_row = 4 if reorder_same_cohort else 5
    matches = [
        _match(
            match_id="match:synthetic:example-open:20240101:1",
            tourney_date="20240101",
            round_name="R32",
            winner_id=1,
            loser_id=2,
            row_number=2,
        ),
        _match(
            match_id="match:synthetic:example-open:20240108:2",
            tourney_date="20240108",
            round_name="R16",
            winner_id=2,
            loser_id=1,
            row_number=3,
        ),
        _match(
            match_id="match:synthetic:example-open:20240115:3",
            tourney_date="20240115",
            round_name="QF",
            winner_id=1,
            loser_id=2,
            row_number=same_cohort_target_row,
        ),
        _match(
            match_id="match:synthetic:example-open:20240115:4",
            tourney_date="20240115",
            round_name="QF",
            winner_id=3,
            loser_id=4,
            row_number=same_cohort_other_row,
        ),
        _match(
            match_id="match:synthetic:example-open:20240122:5",
            tourney_date="20240122",
            round_name="SF",
            winner_id=1,
            loser_id=3,
            row_number=6,
        ),
    ]
    rankings = [
        _ranking(player_id=1, ranking_date="20240101", rank=8, points=1450, row_number=2),
        _ranking(player_id=2, ranking_date="20240101", rank=18, points=1125, row_number=3),
        _ranking(player_id=3, ranking_date="20240101", rank=24, points=980, row_number=4),
        _ranking(player_id=4, ranking_date="20240101", rank=31, points=860, row_number=5),
        _ranking(player_id=1, ranking_date="20240108", rank=7, points=1510, row_number=6),
        _ranking(player_id=2, ranking_date="20240108", rank=16, points=1180, row_number=7),
        _ranking(player_id=3, ranking_date="20240108", rank=23, points=1010, row_number=8),
        _ranking(player_id=4, ranking_date="20240108", rank=30, points=885, row_number=9),
    ]
    match_stats = [
        _match_stat(
            source_match_id=101,
            first_won_player1=28,
            first_won_player2=24,
            ace_player1=6,
            ace_player2=4,
            serve_points_player1=38,
            serve_points_player2=36,
            row_number=2,
        ),
        _match_stat(
            source_match_id=102,
            first_won_player1=27,
            first_won_player2=26,
            ace_player1=5,
            ace_player2=3,
            serve_points_player1=37,
            serve_points_player2=35,
            row_number=3,
        ),
        _match_stat(
            source_match_id=103,
            first_won_player1=29,
            first_won_player2=25,
            ace_player1=7,
            ace_player2=4,
            serve_points_player1=39,
            serve_points_player2=34,
            row_number=same_cohort_target_row,
        ),
        _match_stat(
            source_match_id=104,
            first_won_player1=30,
            first_won_player2=21,
            ace_player1=8,
            ace_player2=2,
            serve_points_player1=40,
            serve_points_player2=33,
            row_number=same_cohort_other_row,
        ),
        _match_stat(
            source_match_id=105,
            first_won_player1=31,
            first_won_player2=23,
            ace_player1=9,
            ace_player2=5,
            serve_points_player1=41,
            serve_points_player2=34,
            row_number=6,
        ),
    ]
    if include_cross_file_collision:
        match_stats.append(
            _match_stat(
                source_match_id=205,
                first_won_player1=11,
                first_won_player2=39,
                ace_player1=1,
                ace_player2=12,
                serve_points_player1=70,
                serve_points_player2=60,
                row_number=2,
                file_name="atp_matchstats_2025.csv",
            )
        )
    return matches, rankings, match_stats


def _snapshot_contract(snapshot: object) -> tuple[object, ...]:
    return (
        snapshot.canonical_match_id,
        snapshot.canonical_player_id,
        snapshot.side,
        snapshot.rank,
        snapshot.rank_points,
        snapshot.ranking_change,
        snapshot.previous_rank,
        snapshot.previous_rank_points,
        snapshot.previous_ranking_date,
        snapshot.rank_missing,
        snapshot.rank_points_missing,
        snapshot.ranking_age_days,
        snapshot.elo_overall,
        snapshot.elo_surface,
        snapshot.rest_days,
        snapshot.form_last_5_win_rate,
        snapshot.form_last_10_win_rate,
        snapshot.form_last_20_win_rate,
        snapshot.form_last_5_count,
        snapshot.form_last_10_count,
        snapshot.form_last_20_count,
        snapshot.service_first_won_rate,
        snapshot.return_first_won_allowed_rate,
        snapshot.ace_rate,
        snapshot.stats_match_count,
        snapshot.serve_point_exposure,
        snapshot.stats_missing,
        snapshot.stats_low_sample,
        snapshot.head_to_head_match_count,
        snapshot.head_to_head_wins,
        snapshot.head_to_head_losses,
        snapshot.head_to_head_win_rate,
        snapshot.head_to_head_missing,
        snapshot.head_to_head_low_sample,
    )


def _differential_contract(row: object) -> tuple[object, ...]:
    return (
        row.canonical_match_id,
        row.player_a_id,
        row.player_b_id,
        row.rank_diff,
        row.rank_points_diff,
        row.ranking_change_diff,
        row.elo_diff,
        row.surface_elo_diff,
        row.rest_days_diff,
        row.form_last_5_win_rate_diff,
        row.form_last_10_win_rate_diff,
        row.form_last_20_win_rate_diff,
        row.service_first_won_rate_diff,
        row.return_first_won_allowed_rate_diff,
        row.ace_rate_diff,
        row.h2h_win_rate_diff,
        row.h2h_match_count,
    )


def _aggregate_snapshot_contract(snapshot: object) -> tuple[object, ...]:
    return (
        snapshot.service_first_won_rate,
        snapshot.return_first_won_allowed_rate,
        snapshot.ace_rate,
        snapshot.stats_match_count,
        snapshot.serve_point_exposure,
        snapshot.stats_missing,
        snapshot.stats_low_sample,
    )


def _aggregate_differential_contract(row: object) -> tuple[object, ...]:
    return (
        row.service_first_won_rate_diff,
        row.return_first_won_allowed_rate_diff,
        row.ace_rate_diff,
    )


def _snapshot_by_key(result: object, *, match_id: str, player_id: int, side: str):
    canonical_player_id = f"player:sackmann:{player_id}"
    return next(
        snapshot
        for snapshot in result.player_snapshots
        if snapshot.canonical_match_id == match_id
        and snapshot.canonical_player_id == canonical_player_id
        and snapshot.side == side
    )


def _differential_by_match(result: object, *, match_id: str):
    return next(
        row for row in result.differential_rows if row.canonical_match_id == match_id
    )


def test_build_feature_snapshots_is_invariant_to_future_row_deletion() -> None:
    matches, rankings, match_stats = _synthetic_history()
    full_result = build_feature_snapshots(
        matches=matches,
        rankings=rankings,
        match_stats=match_stats,
        feature_version="02-04-test",
    )
    truncated_result = build_feature_snapshots(
        matches=matches[:-1],
        rankings=rankings,
        match_stats=match_stats[:-1],
        feature_version="02-04-test",
    )

    target_match_id = "match:synthetic:example-open:20240115:3"
    assert _snapshot_contract(
        _snapshot_by_key(full_result, match_id=target_match_id, player_id=1, side="A")
    ) == _snapshot_contract(
        _snapshot_by_key(truncated_result, match_id=target_match_id, player_id=1, side="A")
    )
    assert _snapshot_contract(
        _snapshot_by_key(full_result, match_id=target_match_id, player_id=2, side="B")
    ) == _snapshot_contract(
        _snapshot_by_key(truncated_result, match_id=target_match_id, player_id=2, side="B")
    )
    assert _differential_contract(
        _differential_by_match(full_result, match_id=target_match_id)
    ) == _differential_contract(
        _differential_by_match(truncated_result, match_id=target_match_id)
    )


def test_build_feature_snapshots_is_invariant_to_same_cohort_reordering() -> None:
    canonical_matches, rankings, canonical_match_stats = _synthetic_history()
    reordered_matches, reordered_rankings, reordered_match_stats = _synthetic_history(
        reorder_same_cohort=True
    )
    assert rankings == reordered_rankings

    canonical_result = build_feature_snapshots(
        matches=canonical_matches,
        rankings=rankings,
        match_stats=canonical_match_stats,
        feature_version="02-04-test",
    )
    reordered_result = build_feature_snapshots(
        matches=reordered_matches,
        rankings=reordered_rankings,
        match_stats=reordered_match_stats,
        feature_version="02-04-test",
    )

    target_match_id = "match:synthetic:example-open:20240115:3"
    assert _snapshot_contract(
        _snapshot_by_key(canonical_result, match_id=target_match_id, player_id=1, side="A")
    ) == _snapshot_contract(
        _snapshot_by_key(reordered_result, match_id=target_match_id, player_id=1, side="A")
    )
    assert _snapshot_contract(
        _snapshot_by_key(canonical_result, match_id=target_match_id, player_id=2, side="B")
    ) == _snapshot_contract(
        _snapshot_by_key(reordered_result, match_id=target_match_id, player_id=2, side="B")
    )
    assert _differential_contract(
        _differential_by_match(canonical_result, match_id=target_match_id)
    ) == _differential_contract(
        _differential_by_match(reordered_result, match_id=target_match_id)
    )


def test_build_feature_snapshots_is_invariant_to_cross_file_row_number_collisions() -> None:
    matches, rankings, clean_match_stats = _synthetic_history()
    _, _, colliding_match_stats = _synthetic_history(include_cross_file_collision=True)

    clean_result = build_feature_snapshots(
        matches=matches,
        rankings=rankings,
        match_stats=clean_match_stats,
        feature_version="02-05-test",
    )
    colliding_result = build_feature_snapshots(
        matches=matches,
        rankings=rankings,
        match_stats=colliding_match_stats,
        feature_version="02-05-test",
    )

    target_match_id = "match:synthetic:example-open:20240115:3"
    assert _aggregate_snapshot_contract(
        _snapshot_by_key(clean_result, match_id=target_match_id, player_id=1, side="A")
    ) == _aggregate_snapshot_contract(
        _snapshot_by_key(colliding_result, match_id=target_match_id, player_id=1, side="A")
    )
    assert _aggregate_snapshot_contract(
        _snapshot_by_key(clean_result, match_id=target_match_id, player_id=2, side="B")
    ) == _aggregate_snapshot_contract(
        _snapshot_by_key(colliding_result, match_id=target_match_id, player_id=2, side="B")
    )
    assert _aggregate_differential_contract(
        _differential_by_match(clean_result, match_id=target_match_id)
    ) == _aggregate_differential_contract(
        _differential_by_match(colliding_result, match_id=target_match_id)
    )
