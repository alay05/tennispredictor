from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal


class BacktestProvenanceLabel(StrEnum):
    actual_kalshi_historical = "actual_kalshi_historical"
    collected_snapshot_replay = "collected_snapshot_replay"
    synthetic_proxy = "synthetic_proxy"


class MarketProbabilitySource(StrEnum):
    normalized_positive_side = "normalized_positive_side"
    normalized_negative_side = "normalized_negative_side"
    normalized_midpoint = "normalized_midpoint"
    manual_fixture = "manual_fixture"


@dataclass(frozen=True)
class ReplayPredictionRow:
    artifact_run_id: str
    model_name: str
    model_family: str
    canonical_match_id: str
    player_a_id: str
    player_b_id: str
    as_of_date: str
    surface: str
    tourney_level: str
    round_name: str
    best_of: int
    player_a_rank: int | None
    player_b_rank: int | None
    rank_diff: int | None
    target: int
    feature_version: str
    split_manifest_id: str
    source_commit_sha: str
    raw_probability: float
    calibrated_probability: float
    favored_side: Literal["A", "B"]
    favored_probability: float


@dataclass(frozen=True)
class ReplayRunResult:
    artifact_run_id: str
    artifact_dir: Path
    feature_version: str
    split_manifest_id: str
    source_commit_sha: str
    rows: list[ReplayPredictionRow]
    parity_checked: bool


@dataclass(frozen=True)
class DecisionThresholds:
    min_edge: float
    min_confidence: float
    min_liquidity: float
    fee_per_contract: float = 0.0
    slippage_per_contract: float = 0.0
    assumption_notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedMarketInput:
    canonical_match_id: str
    market_probability: float | None
    market_probability_source: str | MarketProbabilitySource
    available_liquidity_dollars: float | None
    liquidity_source: str
    provenance_label: BacktestProvenanceLabel | str
    assumption_notes: str = ""


@dataclass(frozen=True)
class OpportunityDecisionRecord:
    artifact_run_id: str
    canonical_match_id: str
    model_name: str
    model_family: str
    feature_version: str
    split_manifest_id: str
    source_commit_sha: str
    as_of_date: str
    selected_side: Literal["positive", "negative"]
    model_probability: float
    market_probability: float | None
    edge: float | None
    expected_value_per_contract: float | None
    confidence: float
    available_liquidity_dollars: float | None
    market_probability_source: str
    liquidity_source: str
    provenance_label: BacktestProvenanceLabel | str
    threshold_snapshot: dict[str, Any]
    accepted: bool
    rejection_reason_codes: tuple[str, ...] = field(default_factory=tuple)
    realized_outcome: int | None = None
    realized_pnl: float | None = None


@dataclass(frozen=True)
class OpportunityDecisionBatch:
    run_id: str
    artifact_run_id: str
    feature_version: str
    split_manifest_id: str
    source_commit_sha: str
    provenance_label: BacktestProvenanceLabel
    assumption_notes: str
    thresholds: DecisionThresholds
    accepted_records: list[OpportunityDecisionRecord]
    rejected_records: list[OpportunityDecisionRecord]

    @property
    def records(self) -> list[OpportunityDecisionRecord]:
        return self.accepted_records + self.rejected_records
