from __future__ import annotations

import pytest
from tennisprediction.features.state import PlayerStateAuditRecord

from tennisprediction.domain.models import (
    CanonicalMatch,
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


def test_build_feature_snapshots_tracks_last_5_10_20_form_and_days_rest_from_prior_matches(
) -> None:
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
