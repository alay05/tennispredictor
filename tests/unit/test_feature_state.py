from __future__ import annotations

import pytest

from tennisprediction.domain.models import (
    CanonicalMatch,
    CanonicalMatchStat,
    CanonicalRanking,
    SourceLineage,
)
from tennisprediction.features.runner import build_feature_snapshots
from tennisprediction.features.state import PlayerStateAuditRecord


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
    surface: str,
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
        surface=surface,
        tourney_name="Example Open",
        tourney_level="A",
        tourney_date=tourney_date,
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
    row_number: int,
) -> CanonicalRanking:
    return CanonicalRanking(
        canonical_ranking_id=f"ranking:synthetic:{player_id}:{ranking_date}",
        canonical_player_id=f"player:sackmann:{player_id}",
        ranking_date=ranking_date,
        rank=rank,
        points=2000 - (rank * 10),
        lineage=_lineage(file_name="atp_rankings_2024.csv", row_number=row_number),
    )


def _match_stat(
    *,
    source_match_id: int,
    first_won_player1: int,
    first_won_player2: int,
    ace_player1: int | None,
    ace_player2: int | None,
    serve_points_player1: int | None,
    serve_points_player2: int | None,
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


def _snapshot_for_match(
    result: object,
    *,
    match_id: str,
    player_id: int,
):
    return next(
        snapshot
        for snapshot in result.player_snapshots
        if snapshot.canonical_match_id == match_id
        and snapshot.canonical_player_id == f"player:sackmann:{player_id}"
    )


def _cross_file_row_number_collision_history() -> tuple[
    list[CanonicalMatch],
    list[CanonicalRanking],
    list[CanonicalMatchStat],
]:
    matches = [
        _match(
            match_id="match:synthetic:example-open:20240101:1",
            tourney_date="20240101",
            surface="Hard",
            winner_id=1,
            loser_id=2,
            row_number=2,
        ),
        _match(
            match_id="match:synthetic:example-open:20240108:2",
            tourney_date="20240108",
            surface="Hard",
            winner_id=2,
            loser_id=1,
            row_number=3,
        ),
        _match(
            match_id="match:synthetic:example-open:20240115:3",
            tourney_date="20240115",
            surface="Hard",
            winner_id=1,
            loser_id=2,
            row_number=4,
        ),
    ]
    rankings = [
        _ranking(player_id=1, ranking_date="20240101", rank=8, row_number=2),
        _ranking(player_id=2, ranking_date="20240101", rank=18, row_number=3),
        _ranking(player_id=1, ranking_date="20240108", rank=7, row_number=4),
        _ranking(player_id=2, ranking_date="20240108", rank=16, row_number=5),
    ]
    match_stats = [
        _match_stat(
            source_match_id=1001,
            first_won_player1=35,
            first_won_player2=28,
            ace_player1=8,
            ace_player2=4,
            serve_points_player1=50,
            serve_points_player2=48,
            row_number=2,
            file_name="atp_matchstats_2024.csv",
        ),
        _match_stat(
            source_match_id=1002,
            first_won_player1=30,
            first_won_player2=33,
            ace_player1=5,
            ace_player2=7,
            serve_points_player1=45,
            serve_points_player2=52,
            row_number=3,
            file_name="atp_matchstats_2024.csv",
        ),
        _match_stat(
            source_match_id=2099,
            first_won_player1=14,
            first_won_player2=39,
            ace_player1=1,
            ace_player2=12,
            serve_points_player1=70,
            serve_points_player2=60,
            row_number=2,
            file_name="atp_matchstats_2025.csv",
        ),
    ]
    return matches, rankings, match_stats


def test_build_feature_snapshots_uses_pre_match_elo_and_surface_elo() -> None:
    result = build_feature_snapshots(
        matches=[
            _match(
                match_id="match:synthetic:example-open:20240115:1",
                tourney_date="20240115",
                surface="Hard",
                winner_id=1,
                loser_id=2,
                row_number=2,
            ),
            _match(
                match_id="match:synthetic:example-open:20240115:2",
                tourney_date="20240115",
                surface="Hard",
                winner_id=1,
                loser_id=3,
                row_number=3,
            ),
            _match(
                match_id="match:synthetic:example-open:20240120:3",
                tourney_date="20240120",
                surface="Clay",
                winner_id=4,
                loser_id=1,
                row_number=4,
            ),
            _match(
                match_id="match:synthetic:example-open:20240127:4",
                tourney_date="20240127",
                surface="Hard",
                winner_id=1,
                loser_id=5,
                row_number=5,
            ),
        ],
        rankings=[
            _ranking(player_id=player_id, ranking_date="20240101", rank=rank, row_number=row_number)
            for player_id, rank, row_number in [
                (1, 8, 2),
                (2, 15, 3),
                (3, 22, 4),
                (4, 18, 5),
                (5, 30, 6),
            ]
        ],
        feature_version="v0-test",
    )

    same_round_first = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240115:1",
        player_id=1,
    )
    same_round_second = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240115:2",
        player_id=1,
    )
    clay_follow_up = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240120:3",
        player_id=1,
    )
    hard_follow_up = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240127:4",
        player_id=1,
    )

    assert same_round_first.elo_overall == pytest.approx(1500.0)
    assert same_round_first.elo_surface == pytest.approx(1500.0)
    assert same_round_second.elo_overall == pytest.approx(same_round_first.elo_overall)
    assert same_round_second.elo_surface == pytest.approx(same_round_first.elo_surface)

    assert clay_follow_up.elo_overall > same_round_first.elo_overall
    assert clay_follow_up.elo_surface == pytest.approx(1500.0)
    assert hard_follow_up.elo_surface > same_round_first.elo_surface

    assert result.state_audit_records
    assert isinstance(result.state_audit_records[0], PlayerStateAuditRecord)


def test_build_feature_snapshots_tracks_last_5_10_20_form_and_days_rest_from_prior_matches() -> (
    None
):
    result = build_feature_snapshots(
        matches=[
            _match(
                match_id="match:synthetic:example-open:20240101:1",
                tourney_date="20240101",
                surface="Hard",
                winner_id=1,
                loser_id=2,
                row_number=2,
            ),
            _match(
                match_id="match:synthetic:example-open:20240105:2",
                tourney_date="20240105",
                surface="Hard",
                winner_id=3,
                loser_id=1,
                row_number=3,
            ),
            _match(
                match_id="match:synthetic:example-open:20240110:3",
                tourney_date="20240110",
                surface="Clay",
                winner_id=1,
                loser_id=4,
                row_number=4,
            ),
            _match(
                match_id="match:synthetic:example-open:20240115:4",
                tourney_date="20240115",
                surface="Clay",
                winner_id=1,
                loser_id=5,
                row_number=5,
            ),
            _match(
                match_id="match:synthetic:example-open:20240120:5",
                tourney_date="20240120",
                surface="Hard",
                winner_id=6,
                loser_id=1,
                row_number=6,
            ),
            _match(
                match_id="match:synthetic:example-open:20240125:6",
                tourney_date="20240125",
                surface="Hard",
                winner_id=1,
                loser_id=7,
                row_number=7,
            ),
        ],
        rankings=[
            _ranking(player_id=player_id, ranking_date="20240101", rank=rank, row_number=row_number)
            for player_id, rank, row_number in [
                (1, 8, 2),
                (2, 15, 3),
                (3, 16, 4),
                (4, 17, 5),
                (5, 18, 6),
                (6, 19, 7),
                (7, 20, 8),
            ]
        ],
        feature_version="v0-test",
    )

    opening_snapshot = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240101:1",
        player_id=1,
    )
    midstream_snapshot = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240110:3",
        player_id=1,
    )
    target_snapshot = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240125:6",
        player_id=1,
    )

    assert opening_snapshot.form_last_5_win_rate is None
    assert opening_snapshot.form_last_10_win_rate is None
    assert opening_snapshot.form_last_20_win_rate is None
    assert opening_snapshot.form_last_5_count == 0
    assert opening_snapshot.form_last_10_count == 0
    assert opening_snapshot.form_last_20_count == 0
    assert opening_snapshot.rest_days is None

    assert midstream_snapshot.form_last_5_win_rate == pytest.approx(0.5)
    assert midstream_snapshot.form_last_10_win_rate == pytest.approx(0.5)
    assert midstream_snapshot.form_last_20_win_rate == pytest.approx(0.5)
    assert midstream_snapshot.form_last_5_count == 2
    assert midstream_snapshot.form_last_10_count == 2
    assert midstream_snapshot.form_last_20_count == 2
    assert midstream_snapshot.rest_days == 5

    assert target_snapshot.form_last_5_win_rate == pytest.approx(0.6)
    assert target_snapshot.form_last_10_win_rate == pytest.approx(0.6)
    assert target_snapshot.form_last_20_win_rate == pytest.approx(0.6)
    assert target_snapshot.form_last_5_count == 5
    assert target_snapshot.form_last_10_count == 5
    assert target_snapshot.form_last_20_count == 5
    assert target_snapshot.rest_days == 5


def test_build_feature_snapshots_uses_prior_match_stats_only() -> None:
    result = build_feature_snapshots(
        matches=[
            _match(
                match_id="match:synthetic:example-open:20240101:1",
                tourney_date="20240101",
                surface="Hard",
                winner_id=1,
                loser_id=2,
                row_number=2,
            ),
            _match(
                match_id="match:synthetic:example-open:20240110:2",
                tourney_date="20240110",
                surface="Hard",
                winner_id=2,
                loser_id=1,
                row_number=3,
            ),
            _match(
                match_id="match:synthetic:example-open:20240120:3",
                tourney_date="20240120",
                surface="Hard",
                winner_id=1,
                loser_id=2,
                row_number=4,
            ),
            _match(
                match_id="match:synthetic:example-open:20240125:4",
                tourney_date="20240125",
                surface="Hard",
                winner_id=1,
                loser_id=3,
                row_number=5,
            ),
            _match(
                match_id="match:synthetic:example-open:20240130:5",
                tourney_date="20240130",
                surface="Hard",
                winner_id=1,
                loser_id=4,
                row_number=6,
            ),
        ],
        rankings=[
            _ranking(player_id=player_id, ranking_date="20240101", rank=rank, row_number=row_number)
            for player_id, rank, row_number in [
                (1, 8, 2),
                (2, 15, 3),
                (3, 25, 4),
                (4, 30, 5),
            ]
        ],
        match_stats=[
            _match_stat(
                source_match_id=1001,
                first_won_player1=35,
                first_won_player2=28,
                ace_player1=8,
                ace_player2=4,
                serve_points_player1=50,
                serve_points_player2=48,
                row_number=2,
            ),
            _match_stat(
                source_match_id=1002,
                first_won_player1=30,
                first_won_player2=33,
                ace_player1=5,
                ace_player2=7,
                serve_points_player1=45,
                serve_points_player2=52,
                row_number=3,
            ),
            _match_stat(
                source_match_id=1003,
                first_won_player1=40,
                first_won_player2=34,
                ace_player1=10,
                ace_player2=6,
                serve_points_player1=60,
                serve_points_player2=55,
                row_number=4,
            ),
            _match_stat(
                source_match_id=1004,
                first_won_player1=12,
                first_won_player2=10,
                ace_player1=None,
                ace_player2=None,
                serve_points_player1=20,
                serve_points_player2=18,
                row_number=5,
            ),
            _match_stat(
                source_match_id=1005,
                first_won_player1=25,
                first_won_player2=22,
                ace_player1=6,
                ace_player2=3,
                serve_points_player1=38,
                serve_points_player2=40,
                row_number=6,
            ),
        ],
        feature_version="v0-test",
    )

    opening_snapshot = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240101:1",
        player_id=1,
    )
    rematch_snapshot = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240110:2",
        player_id=1,
    )
    h2h_snapshot = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240120:3",
        player_id=1,
    )
    sparse_snapshot = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240125:4",
        player_id=1,
    )
    missing_ace_history_snapshot = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240130:5",
        player_id=1,
    )

    assert opening_snapshot.service_first_won_rate is None
    assert opening_snapshot.return_first_won_allowed_rate is None
    assert opening_snapshot.ace_rate is None
    assert opening_snapshot.stats_match_count == 0
    assert opening_snapshot.serve_point_exposure == 0
    assert opening_snapshot.stats_missing is True
    assert opening_snapshot.stats_low_sample is False
    assert opening_snapshot.head_to_head_match_count == 0
    assert opening_snapshot.head_to_head_wins == 0
    assert opening_snapshot.head_to_head_losses == 0
    assert opening_snapshot.head_to_head_win_rate is None
    assert opening_snapshot.head_to_head_missing is True
    assert opening_snapshot.head_to_head_low_sample is False

    assert rematch_snapshot.service_first_won_rate == pytest.approx(35 / 50)
    assert rematch_snapshot.return_first_won_allowed_rate == pytest.approx(28 / 48)
    assert rematch_snapshot.ace_rate == pytest.approx(8 / 50)
    assert rematch_snapshot.stats_match_count == 1
    assert rematch_snapshot.serve_point_exposure == 50
    assert rematch_snapshot.stats_missing is False
    assert rematch_snapshot.stats_low_sample is False
    assert rematch_snapshot.head_to_head_match_count == 1
    assert rematch_snapshot.head_to_head_wins == 1
    assert rematch_snapshot.head_to_head_losses == 0
    assert rematch_snapshot.head_to_head_win_rate is None
    assert rematch_snapshot.head_to_head_missing is False
    assert rematch_snapshot.head_to_head_low_sample is True

    assert h2h_snapshot.service_first_won_rate == pytest.approx((35 + 33) / (50 + 52))
    assert h2h_snapshot.return_first_won_allowed_rate == pytest.approx((28 + 30) / (48 + 45))
    assert h2h_snapshot.ace_rate == pytest.approx((8 + 7) / (50 + 52))
    assert h2h_snapshot.stats_match_count == 2
    assert h2h_snapshot.serve_point_exposure == 102
    assert h2h_snapshot.stats_missing is False
    assert h2h_snapshot.stats_low_sample is False
    assert h2h_snapshot.head_to_head_match_count == 2
    assert h2h_snapshot.head_to_head_wins == 1
    assert h2h_snapshot.head_to_head_losses == 1
    assert h2h_snapshot.head_to_head_win_rate == pytest.approx(0.5)
    assert h2h_snapshot.head_to_head_missing is False
    assert h2h_snapshot.head_to_head_low_sample is False

    assert sparse_snapshot.service_first_won_rate == pytest.approx((35 + 33 + 40) / (50 + 52 + 60))
    assert sparse_snapshot.return_first_won_allowed_rate == pytest.approx(
        (28 + 30 + 34) / (48 + 45 + 55)
    )
    assert sparse_snapshot.ace_rate == pytest.approx((8 + 7 + 10) / (50 + 52 + 60))
    assert sparse_snapshot.stats_match_count == 3
    assert sparse_snapshot.serve_point_exposure == 162
    assert sparse_snapshot.stats_missing is False
    assert sparse_snapshot.stats_low_sample is False

    assert missing_ace_history_snapshot.service_first_won_rate == pytest.approx(
        (35 + 33 + 40 + 12) / (50 + 52 + 60 + 20)
    )
    assert missing_ace_history_snapshot.return_first_won_allowed_rate == pytest.approx(
        (28 + 30 + 34 + 10) / (48 + 45 + 55 + 18)
    )
    assert missing_ace_history_snapshot.ace_rate is None
    assert missing_ace_history_snapshot.stats_match_count == 4
    assert missing_ace_history_snapshot.serve_point_exposure == 182
    assert missing_ace_history_snapshot.stats_missing is False
    assert missing_ace_history_snapshot.stats_low_sample is False


def test_build_feature_snapshots_keeps_prior_stats_bound_to_source_file_path_and_row_number() -> (
    None
):
    matches, rankings, match_stats = _cross_file_row_number_collision_history()

    result = build_feature_snapshots(
        matches=matches,
        rankings=rankings,
        match_stats=match_stats,
        feature_version="02-05-test",
    )

    target_snapshot = _snapshot_for_match(
        result,
        match_id="match:synthetic:example-open:20240115:3",
        player_id=1,
    )

    assert target_snapshot.service_first_won_rate == pytest.approx((35 + 33) / (50 + 52))
    assert target_snapshot.return_first_won_allowed_rate == pytest.approx((28 + 30) / (48 + 45))
    assert target_snapshot.ace_rate == pytest.approx((8 + 7) / (50 + 52))
    assert target_snapshot.stats_match_count == 2
    assert target_snapshot.serve_point_exposure == 102
