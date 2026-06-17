from __future__ import annotations

from tennisprediction.domain.models import CanonicalMatch, CanonicalMatchStat, CanonicalRanking
from tennisprediction.features.differential import build_differential_row
from tennisprediction.features.ordering import build_match_cohorts
from tennisprediction.features.rankings import attach_prior_rankings
from tennisprediction.features.schemas import (
    FeatureBuildResult,
    PlayerFeatureSnapshot,
)
from tennisprediction.features.state import (
    HeadToHeadState,
    MatchStatAggregateState,
    PlayerFeatureState,
    apply_match_result_batch,
    build_pre_match_head_to_head_snapshot,
    build_pre_match_snapshot,
    build_pre_match_stat_snapshot,
    get_head_to_head_state,
    get_match_stat_state,
    get_player_state,
)


def _build_player_snapshot(
    *,
    match: CanonicalMatch,
    feature_version: str,
    side: str,
    rankings: list[CanonicalRanking],
    player_states: dict[str, PlayerFeatureState],
    match_stat_states: dict[str, MatchStatAggregateState],
    head_to_head_states: dict[tuple[str, str], HeadToHeadState],
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
    state_features = build_pre_match_snapshot(
        state=get_player_state(
            canonical_player_id=canonical_player_id,
            player_states=player_states,
        ),
        as_of_date=match.tourney_date,
        surface=match.surface,
    )
    stat_features = build_pre_match_stat_snapshot(
        state=get_match_stat_state(
            canonical_player_id=canonical_player_id,
            match_stat_states=match_stat_states,
        )
    )
    head_to_head_features = build_pre_match_head_to_head_snapshot(
        canonical_player_id=canonical_player_id,
        opponent_canonical_player_id=opponent_canonical_player_id,
        state=get_head_to_head_state(
            canonical_player_id=canonical_player_id,
            opponent_canonical_player_id=opponent_canonical_player_id,
            head_to_head_states=head_to_head_states,
        ),
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
        elo_overall=state_features.elo_overall,
        elo_surface=state_features.elo_surface,
        rest_days=state_features.rest_days,
        form_last_5_win_rate=state_features.form_last_5_win_rate,
        form_last_10_win_rate=state_features.form_last_10_win_rate,
        form_last_20_win_rate=state_features.form_last_20_win_rate,
        form_last_5_count=state_features.form_last_5_count,
        form_last_10_count=state_features.form_last_10_count,
        form_last_20_count=state_features.form_last_20_count,
        service_first_won_rate=stat_features.service_first_won_rate,
        return_first_won_allowed_rate=stat_features.return_first_won_allowed_rate,
        ace_rate=stat_features.ace_rate,
        stats_match_count=stat_features.stats_match_count,
        serve_point_exposure=stat_features.serve_point_exposure,
        stats_missing=stat_features.stats_missing,
        stats_low_sample=stat_features.stats_low_sample,
        head_to_head_match_count=head_to_head_features.head_to_head_match_count,
        head_to_head_wins=head_to_head_features.head_to_head_wins,
        head_to_head_losses=head_to_head_features.head_to_head_losses,
        head_to_head_win_rate=head_to_head_features.head_to_head_win_rate,
        head_to_head_missing=head_to_head_features.head_to_head_missing,
        head_to_head_low_sample=head_to_head_features.head_to_head_low_sample,
        lineage=match.lineage,
    )


def _index_match_stats(
    match_stats: list[CanonicalMatchStat],
) -> dict[int, CanonicalMatchStat]:
    indexed: dict[int, CanonicalMatchStat] = {}
    for match_stat in match_stats:
        indexed[match_stat.lineage.source_row_number] = match_stat
    return indexed


def build_feature_snapshots(
    *,
    matches: list[CanonicalMatch],
    rankings: list[CanonicalRanking],
    match_stats: list[CanonicalMatchStat] | None = None,
    feature_version: str = "02-03",
) -> FeatureBuildResult:
    player_snapshots: list[PlayerFeatureSnapshot] = []
    differential_rows = []
    state_audit_records = []
    player_states: dict[str, PlayerFeatureState] = {}
    match_stat_states: dict[str, MatchStatAggregateState] = {}
    head_to_head_states: dict[tuple[str, str], HeadToHeadState] = {}
    match_stats_by_row = _index_match_stats(match_stats or [])
    for cohort in build_match_cohorts(matches):
        for match in cohort:
            player_a_snapshot = _build_player_snapshot(
                match=match,
                feature_version=feature_version,
                side="A",
                rankings=rankings,
                player_states=player_states,
                match_stat_states=match_stat_states,
                head_to_head_states=head_to_head_states,
            )
            player_b_snapshot = _build_player_snapshot(
                match=match,
                feature_version=feature_version,
                side="B",
                rankings=rankings,
                player_states=player_states,
                match_stat_states=match_stat_states,
                head_to_head_states=head_to_head_states,
            )
            player_snapshots.extend([player_a_snapshot, player_b_snapshot])
            differential_rows.append(build_differential_row(player_a_snapshot, player_b_snapshot))
        (
            player_states,
            match_stat_states,
            head_to_head_states,
            cohort_audit_records,
        ) = apply_match_result_batch(
            matches=cohort,
            player_states=player_states,
            match_stat_states=match_stat_states,
            head_to_head_states=head_to_head_states,
            match_stats_by_row=match_stats_by_row,
        )
        state_audit_records.extend(cohort_audit_records)

    return FeatureBuildResult(
        player_snapshots=player_snapshots,
        differential_rows=differential_rows,
        state_audit_records=state_audit_records,
    )
