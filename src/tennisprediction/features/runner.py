from __future__ import annotations

from tennisprediction.domain.models import CanonicalMatch, CanonicalRanking
from tennisprediction.features.differential import build_differential_row
from tennisprediction.features.ordering import build_match_cohorts
from tennisprediction.features.rankings import attach_prior_rankings
from tennisprediction.features.schemas import (
    FeatureBuildResult,
    PlayerFeatureSnapshot,
)


def _build_player_snapshot(
    *,
    match: CanonicalMatch,
    feature_version: str,
    side: str,
    rankings: list[CanonicalRanking],
) -> PlayerFeatureSnapshot:
    player_a_id = match.winner_canonical_player_id
    player_b_id = match.loser_canonical_player_id
    if side == "A":
        canonical_player_id = player_a_id
        opponent_canonical_player_id = player_b_id
    else:
        canonical_player_id = player_b_id
        opponent_canonical_player_id = player_a_id

    ranking = attach_prior_rankings(
        canonical_player_id=canonical_player_id,
        as_of_date=match.tourney_date,
        rankings=rankings,
    )
    return PlayerFeatureSnapshot(
        feature_version=feature_version,
        canonical_match_id=match.canonical_match_id,
        canonical_player_id=canonical_player_id,
        opponent_canonical_player_id=opponent_canonical_player_id,
        player_a_id=player_a_id,
        player_b_id=player_b_id,
        as_of_date=match.tourney_date,
        side=side,
        surface=match.surface,
        tourney_level=match.tourney_level,
        round_name=match.round_name,
        best_of=match.best_of,
        rank=ranking.rank,
        rank_points=ranking.rank_points,
        ranking_change=ranking.ranking_change,
        previous_rank=ranking.previous_rank,
        previous_rank_points=ranking.previous_rank_points,
        previous_ranking_date=ranking.previous_ranking_date,
        rank_missing=ranking.rank_missing,
        rank_points_missing=ranking.rank_points_missing,
        ranking_age_days=ranking.ranking_age_days,
        lineage=match.lineage,
    )


def build_feature_snapshots(
    *,
    matches: list[CanonicalMatch],
    rankings: list[CanonicalRanking],
    feature_version: str = "02-01",
) -> FeatureBuildResult:
    player_snapshots: list[PlayerFeatureSnapshot] = []
    differential_rows = []
    for cohort in build_match_cohorts(matches):
        for match in cohort:
            player_a_snapshot = _build_player_snapshot(
                match=match,
                feature_version=feature_version,
                side="A",
                rankings=rankings,
            )
            player_b_snapshot = _build_player_snapshot(
                match=match,
                feature_version=feature_version,
                side="B",
                rankings=rankings,
            )
            player_snapshots.extend([player_a_snapshot, player_b_snapshot])
            differential_rows.append(build_differential_row(player_a_snapshot, player_b_snapshot))

    return FeatureBuildResult(
        player_snapshots=player_snapshots,
        differential_rows=differential_rows,
    )
