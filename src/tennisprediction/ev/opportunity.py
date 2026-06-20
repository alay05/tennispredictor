from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    DecisionThresholds,
    MarketProbabilitySource,
    NormalizedMarketInput,
    OpportunityDecisionBatch,
    OpportunityDecisionRecord,
    ReplayPredictionRow,
)
from tennisprediction.ev.pricing import SideEvaluation, evaluate_candidate_side


def evaluate_opportunities(
    replay_rows: Sequence[ReplayPredictionRow],
    market_inputs: Sequence[NormalizedMarketInput],
    thresholds: DecisionThresholds,
    *,
    run_id: str,
    provenance_label: BacktestProvenanceLabel = BacktestProvenanceLabel.synthetic_proxy,
) -> OpportunityDecisionBatch:
    market_lookup = {
        market_input.canonical_match_id: market_input
        for market_input in market_inputs
    }
    accepted_records: list[OpportunityDecisionRecord] = []
    rejected_records: list[OpportunityDecisionRecord] = []

    for replay_row in replay_rows:
        market_input = market_lookup[replay_row.canonical_match_id]
        batch_records = _evaluate_single_row(
            replay_row=replay_row,
            market_input=market_input,
            thresholds=thresholds,
        )
        accepted_records.extend(
            [record for record in batch_records if record.accepted]
        )
        rejected_records.extend(
            [record for record in batch_records if not record.accepted]
        )

    return OpportunityDecisionBatch(
        run_id=run_id,
        artifact_run_id=replay_rows[0].artifact_run_id if replay_rows else run_id,
        feature_version=replay_rows[0].feature_version if replay_rows else "",
        split_manifest_id=replay_rows[0].split_manifest_id if replay_rows else "",
        source_commit_sha=replay_rows[0].source_commit_sha if replay_rows else "",
        provenance_label=provenance_label,
        assumption_notes=thresholds.assumption_notes,
        thresholds=thresholds,
        accepted_records=accepted_records,
        rejected_records=rejected_records,
    )


def _evaluate_single_row(
    *,
    replay_row: ReplayPredictionRow,
    market_input: NormalizedMarketInput,
    thresholds: DecisionThresholds,
) -> list[OpportunityDecisionRecord]:
    provenance_label = market_input.provenance_label
    market_probability_positive = _coerce_market_probability(market_input.market_probability)
    positive_evaluation = evaluate_candidate_side(
        side="positive",
        model_probability=replay_row.calibrated_probability,
        market_probability=market_probability_positive,
        available_liquidity_dollars=market_input.available_liquidity_dollars,
        thresholds=thresholds,
        provenance_label=provenance_label,
    )
    negative_evaluation = evaluate_candidate_side(
        side="negative",
        model_probability=1.0 - replay_row.calibrated_probability,
        market_probability=(
            None
            if market_probability_positive is None
            else 1.0 - market_probability_positive
        ),
        available_liquidity_dollars=market_input.available_liquidity_dollars,
        thresholds=thresholds,
        provenance_label=provenance_label,
    )
    winner = (
        positive_evaluation
        if _is_better(positive_evaluation, negative_evaluation)
        else negative_evaluation
    )
    return [
        _build_decision_record(
            replay_row=replay_row,
            market_input=market_input,
            evaluation=winner,
            thresholds=thresholds,
        )
    ]


def _build_decision_record(
    *,
    replay_row: ReplayPredictionRow,
    market_input: NormalizedMarketInput,
    evaluation: SideEvaluation,
    thresholds: DecisionThresholds,
) -> OpportunityDecisionRecord:
    selected_market_probability = evaluation.market_probability
    selected_side = evaluation.side
    realized_outcome = None
    realized_pnl = None
    if evaluation.accepted and selected_market_probability is not None:
        outcome_win = (selected_side == "positive" and replay_row.target == 1) or (
            selected_side == "negative" and replay_row.target == 0
        )
        realized_outcome = 1 if outcome_win else 0
        per_contract_cost = selected_market_probability
        penalty = thresholds.fee_per_contract + thresholds.slippage_per_contract
        realized_pnl = (
            1.0 - per_contract_cost - penalty
            if outcome_win
            else -per_contract_cost - penalty
        )

    return OpportunityDecisionRecord(
        artifact_run_id=replay_row.artifact_run_id,
        canonical_match_id=replay_row.canonical_match_id,
        model_name=replay_row.model_name,
        model_family=replay_row.model_family,
        feature_version=replay_row.feature_version,
        split_manifest_id=replay_row.split_manifest_id,
        source_commit_sha=replay_row.source_commit_sha,
        as_of_date=replay_row.as_of_date,
        selected_side=selected_side,
        model_probability=evaluation.model_probability,
        market_probability=evaluation.market_probability,
        edge=evaluation.edge,
        expected_value_per_contract=evaluation.expected_value_per_contract,
        confidence=evaluation.confidence,
        available_liquidity_dollars=market_input.available_liquidity_dollars,
        market_probability_source=_coerce_market_probability_source(
            market_input.market_probability_source
        ),
        liquidity_source=market_input.liquidity_source,
        provenance_label=market_input.provenance_label,
        threshold_snapshot=market_input_threshold_snapshot(
            market_input,
            thresholds=thresholds,
            selected_side=evaluation.side,
        ),
        accepted=evaluation.accepted,
        rejection_reason_codes=evaluation.reason_codes,
        realized_outcome=realized_outcome,
        realized_pnl=realized_pnl,
    )


def market_input_threshold_snapshot(
    market_input: NormalizedMarketInput,
    *,
    thresholds: DecisionThresholds,
    selected_side: Literal["positive", "negative"],
) -> dict[str, object]:
    return {
        "market_probability_source": _coerce_market_probability_source(
            market_input.market_probability_source
        ),
        "liquidity_source": market_input.liquidity_source,
        "provenance_label": _serialize_provenance_label(market_input.provenance_label),
        "assumption_notes": market_input.assumption_notes,
        "selected_side": selected_side,
        "min_edge": thresholds.min_edge,
        "min_confidence": thresholds.min_confidence,
        "min_liquidity": thresholds.min_liquidity,
        "fee_per_contract": thresholds.fee_per_contract,
        "slippage_per_contract": thresholds.slippage_per_contract,
        "threshold_assumption_notes": thresholds.assumption_notes,
    }


def _is_better(left: SideEvaluation, right: SideEvaluation) -> bool:
    left_edge = left.edge if left.edge is not None else float("-inf")
    right_edge = right.edge if right.edge is not None else float("-inf")
    if left_edge != right_edge:
        return left_edge > right_edge
    return left.confidence >= right.confidence


def _coerce_market_probability(value: float | None) -> float | None:
    return value


def _coerce_market_probability_source(value: str | MarketProbabilitySource) -> str:
    if isinstance(value, MarketProbabilitySource):
        return value.value
    return value


def _coerce_provenance_label(
    value: BacktestProvenanceLabel | str,
) -> BacktestProvenanceLabel:
    if isinstance(value, BacktestProvenanceLabel):
        return value
    try:
        return BacktestProvenanceLabel(value)
    except ValueError as exc:
        raise ValueError("unsupported provenance label") from exc


def _serialize_provenance_label(value: BacktestProvenanceLabel | str) -> str:
    if isinstance(value, BacktestProvenanceLabel):
        return value.value
    return value
