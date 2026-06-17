from __future__ import annotations

from dataclasses import dataclass

from tennisprediction.domain.models import SourceLineage
from tennisprediction.features.state import PlayerStateAuditRecord


@dataclass(frozen=True)
class PlayerFeatureSnapshot:
    feature_version: str
    canonical_match_id: str
    canonical_player_id: str
    opponent_canonical_player_id: str
    player_a_id: str
    player_b_id: str
    as_of_date: str
    side: str
    surface: str
    tourney_level: str
    round_name: str
    best_of: int
    rank: int | None
    rank_points: int | None
    ranking_change: int | None
    previous_rank: int | None
    previous_rank_points: int | None
    previous_ranking_date: str | None
    rank_missing: bool
    rank_points_missing: bool
    ranking_age_days: int | None
    elo_overall: float
    elo_surface: float
    rest_days: int | None
    form_last_5_win_rate: float | None
    form_last_10_win_rate: float | None
    form_last_20_win_rate: float | None
    form_last_5_count: int
    form_last_10_count: int
    form_last_20_count: int
    service_first_won_rate: float | None
    return_first_won_allowed_rate: float | None
    ace_rate: float | None
    stats_match_count: int
    serve_point_exposure: int
    stats_missing: bool
    stats_low_sample: bool
    head_to_head_match_count: int
    head_to_head_wins: int
    head_to_head_losses: int
    head_to_head_win_rate: float | None
    head_to_head_missing: bool
    head_to_head_low_sample: bool
    lineage: SourceLineage


@dataclass(frozen=True)
class FeatureDifferentialRow:
    feature_version: str
    canonical_match_id: str
    player_a_id: str
    player_b_id: str
    as_of_date: str
    player_a_side: str
    player_b_side: str
    surface: str
    tourney_level: str
    round_name: str
    best_of: int
    rank_diff: int | None
    rank_points_diff: int | None
    ranking_change_diff: int | None
    elo_diff: float
    surface_elo_diff: float
    rest_days_diff: int | None
    form_last_5_win_rate_diff: float | None
    form_last_10_win_rate_diff: float | None
    form_last_20_win_rate_diff: float | None
    service_first_won_rate_diff: float | None
    return_first_won_allowed_rate_diff: float | None
    ace_rate_diff: float | None
    h2h_win_rate_diff: float | None
    h2h_match_count: int
    lineage: SourceLineage


@dataclass(frozen=True)
class FeatureBuildResult:
    player_snapshots: list[PlayerFeatureSnapshot]
    differential_rows: list[FeatureDifferentialRow]
    state_audit_records: list[PlayerStateAuditRecord]
