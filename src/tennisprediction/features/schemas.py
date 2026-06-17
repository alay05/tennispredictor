from __future__ import annotations

from dataclasses import dataclass

from tennisprediction.domain.models import SourceLineage


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
    lineage: SourceLineage


@dataclass(frozen=True)
class FeatureBuildResult:
    player_snapshots: list[PlayerFeatureSnapshot]
    differential_rows: list[FeatureDifferentialRow]
