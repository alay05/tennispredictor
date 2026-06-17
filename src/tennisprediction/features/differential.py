from __future__ import annotations

from tennisprediction.features.schemas import FeatureDifferentialRow, PlayerFeatureSnapshot


def _diff(left: int | None, right: int | None) -> int | None:
    if left is None or right is None:
        return None
    return left - right


def _float_diff(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    return left - right


def build_differential_row(
    player_a_snapshot: PlayerFeatureSnapshot,
    player_b_snapshot: PlayerFeatureSnapshot,
) -> FeatureDifferentialRow:
    return FeatureDifferentialRow(
        feature_version=player_a_snapshot.feature_version,
        canonical_match_id=player_a_snapshot.canonical_match_id,
        player_a_id=player_a_snapshot.player_a_id,
        player_b_id=player_a_snapshot.player_b_id,
        as_of_date=player_a_snapshot.as_of_date,
        player_a_side=player_a_snapshot.side,
        player_b_side=player_b_snapshot.side,
        surface=player_a_snapshot.surface,
        tourney_level=player_a_snapshot.tourney_level,
        round_name=player_a_snapshot.round_name,
        best_of=player_a_snapshot.best_of,
        rank_diff=_diff(player_a_snapshot.rank, player_b_snapshot.rank),
        rank_points_diff=_diff(player_a_snapshot.rank_points, player_b_snapshot.rank_points),
        ranking_change_diff=_diff(
            player_a_snapshot.ranking_change,
            player_b_snapshot.ranking_change,
        ),
        elo_diff=player_a_snapshot.elo_overall - player_b_snapshot.elo_overall,
        surface_elo_diff=player_a_snapshot.elo_surface - player_b_snapshot.elo_surface,
        rest_days_diff=_diff(player_a_snapshot.rest_days, player_b_snapshot.rest_days),
        form_last_5_win_rate_diff=_float_diff(
            player_a_snapshot.form_last_5_win_rate,
            player_b_snapshot.form_last_5_win_rate,
        ),
        form_last_10_win_rate_diff=_float_diff(
            player_a_snapshot.form_last_10_win_rate,
            player_b_snapshot.form_last_10_win_rate,
        ),
        form_last_20_win_rate_diff=_float_diff(
            player_a_snapshot.form_last_20_win_rate,
            player_b_snapshot.form_last_20_win_rate,
        ),
        lineage=player_a_snapshot.lineage,
    )
