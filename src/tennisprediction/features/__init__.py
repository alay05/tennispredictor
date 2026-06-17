"""Leakage-safe feature contracts and chronological runner helpers."""

from tennisprediction.features.differential import build_differential_row
from tennisprediction.features.ordering import ROUND_PRECEDENCE, build_match_cohorts
from tennisprediction.features.rankings import attach_prior_rankings
from tennisprediction.features.runner import build_feature_snapshots
from tennisprediction.features.schemas import (
    FeatureBuildResult,
    FeatureDifferentialRow,
    PlayerFeatureSnapshot,
)

__all__ = [
    "ROUND_PRECEDENCE",
    "PlayerFeatureSnapshot",
    "FeatureDifferentialRow",
    "FeatureBuildResult",
    "attach_prior_rankings",
    "build_differential_row",
    "build_match_cohorts",
    "build_feature_snapshots",
]
