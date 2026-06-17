from __future__ import annotations

import pytest

from tennisprediction.domain.models import SourceLineage
from tennisprediction.features.differential import build_differential_row
from tennisprediction.features.schemas import PlayerFeatureSnapshot


def _lineage() -> SourceLineage:
    return SourceLineage(
        source_repo="JeffSackmann/tennis_atp",
        source_commit_sha="abcdef1",
        source_file_path="atp_matches_2024.csv",
        source_row_number=2,
        source_snapshot_root="/tmp/raw-snapshot",
    )


def _snapshot(
    *,
    canonical_player_id: str,
    side: str,
    opponent_canonical_player_id: str,
    service_first_won_rate: float | None,
    return_first_won_allowed_rate: float | None,
    ace_rate: float | None,
    stats_match_count: int,
    serve_point_exposure: int,
    stats_missing: bool,
    stats_low_sample: bool,
    head_to_head_match_count: int,
    head_to_head_wins: int,
    head_to_head_losses: int,
    head_to_head_win_rate: float | None,
    head_to_head_missing: bool,
    head_to_head_low_sample: bool,
) -> PlayerFeatureSnapshot:
    return PlayerFeatureSnapshot(
        feature_version="v0-test",
        canonical_match_id="match:synthetic:example-open:20240120:3",
        canonical_player_id=canonical_player_id,
        opponent_canonical_player_id=opponent_canonical_player_id,
        player_a_id="player:sackmann:1",
        player_b_id="player:sackmann:2",
        as_of_date="20240120",
        side=side,
        surface="Hard",
        tourney_level="A",
        round_name="R32",
        best_of=3,
        rank=8 if side == "A" else 15,
        rank_points=1450 if side == "A" else 1100,
        ranking_change=-2 if side == "A" else 1,
        previous_rank=10 if side == "A" else 14,
        previous_rank_points=1380 if side == "A" else 1120,
        previous_ranking_date="20240108",
        rank_missing=False,
        rank_points_missing=False,
        ranking_age_days=5,
        elo_overall=1515.0 if side == "A" else 1485.0,
        elo_surface=1520.0 if side == "A" else 1480.0,
        rest_days=4 if side == "A" else 6,
        form_last_5_win_rate=0.6 if side == "A" else 0.4,
        form_last_10_win_rate=0.6 if side == "A" else 0.4,
        form_last_20_win_rate=0.6 if side == "A" else 0.4,
        form_last_5_count=5,
        form_last_10_count=5,
        form_last_20_count=5,
        service_first_won_rate=service_first_won_rate,
        return_first_won_allowed_rate=return_first_won_allowed_rate,
        ace_rate=ace_rate,
        stats_match_count=stats_match_count,
        serve_point_exposure=serve_point_exposure,
        stats_missing=stats_missing,
        stats_low_sample=stats_low_sample,
        head_to_head_match_count=head_to_head_match_count,
        head_to_head_wins=head_to_head_wins,
        head_to_head_losses=head_to_head_losses,
        head_to_head_win_rate=head_to_head_win_rate,
        head_to_head_missing=head_to_head_missing,
        head_to_head_low_sample=head_to_head_low_sample,
        lineage=_lineage(),
    )


def test_build_differential_row_preserves_stat_and_h2h_missingness() -> None:
    player_a_snapshot = _snapshot(
        canonical_player_id="player:sackmann:1",
        side="A",
        opponent_canonical_player_id="player:sackmann:2",
        service_first_won_rate=None,
        return_first_won_allowed_rate=None,
        ace_rate=None,
        stats_match_count=1,
        serve_point_exposure=32,
        stats_missing=False,
        stats_low_sample=True,
        head_to_head_match_count=1,
        head_to_head_wins=1,
        head_to_head_losses=0,
        head_to_head_win_rate=None,
        head_to_head_missing=False,
        head_to_head_low_sample=True,
    )
    player_b_snapshot = _snapshot(
        canonical_player_id="player:sackmann:2",
        side="B",
        opponent_canonical_player_id="player:sackmann:1",
        service_first_won_rate=0.68,
        return_first_won_allowed_rate=0.62,
        ace_rate=0.09,
        stats_match_count=3,
        serve_point_exposure=150,
        stats_missing=False,
        stats_low_sample=False,
        head_to_head_match_count=1,
        head_to_head_wins=0,
        head_to_head_losses=1,
        head_to_head_win_rate=None,
        head_to_head_missing=False,
        head_to_head_low_sample=True,
    )

    row = build_differential_row(player_a_snapshot, player_b_snapshot)

    assert row.service_first_won_rate_diff is None
    assert row.return_first_won_allowed_rate_diff is None
    assert row.ace_rate_diff is None
    assert row.h2h_win_rate_diff is None
    assert row.h2h_match_count == 1

    complete_player_a_snapshot = _snapshot(
        canonical_player_id="player:sackmann:1",
        side="A",
        opponent_canonical_player_id="player:sackmann:2",
        service_first_won_rate=0.67,
        return_first_won_allowed_rate=0.58,
        ace_rate=0.10,
        stats_match_count=4,
        serve_point_exposure=180,
        stats_missing=False,
        stats_low_sample=False,
        head_to_head_match_count=4,
        head_to_head_wins=3,
        head_to_head_losses=1,
        head_to_head_win_rate=0.75,
        head_to_head_missing=False,
        head_to_head_low_sample=False,
    )
    complete_player_b_snapshot = _snapshot(
        canonical_player_id="player:sackmann:2",
        side="B",
        opponent_canonical_player_id="player:sackmann:1",
        service_first_won_rate=0.63,
        return_first_won_allowed_rate=0.61,
        ace_rate=0.08,
        stats_match_count=5,
        serve_point_exposure=210,
        stats_missing=False,
        stats_low_sample=False,
        head_to_head_match_count=4,
        head_to_head_wins=1,
        head_to_head_losses=3,
        head_to_head_win_rate=0.25,
        head_to_head_missing=False,
        head_to_head_low_sample=False,
    )

    complete_row = build_differential_row(
        complete_player_a_snapshot,
        complete_player_b_snapshot,
    )

    assert complete_row.service_first_won_rate_diff == pytest.approx(0.04)
    assert complete_row.return_first_won_allowed_rate_diff == pytest.approx(-0.03)
    assert complete_row.ace_rate_diff == pytest.approx(0.02)
    assert complete_row.h2h_win_rate_diff == pytest.approx(0.5)
    assert complete_row.h2h_match_count == 4
