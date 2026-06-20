from __future__ import annotations

import pytest

from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    DecisionThresholds,
    MarketProbabilitySource,
    NormalizedMarketInput,
    ReplayPredictionRow,
)
from tennisprediction.ev.opportunity import evaluate_opportunities


def test_evaluate_opportunities_chooses_higher_ev_side_and_keeps_threshold_snapshot() -> None:
    replay_row = _replay_row(calibrated_probability=0.35, target=1)
    market_input = NormalizedMarketInput(
        canonical_match_id=replay_row.canonical_match_id,
        market_probability=0.55,
        market_probability_source=MarketProbabilitySource.normalized_positive_side,
        available_liquidity_dollars=250.0,
        liquidity_source="normalized_available_liquidity_dollars",
        provenance_label=BacktestProvenanceLabel.actual_kalshi_historical,
        assumption_notes="fixture",
    )
    thresholds = DecisionThresholds(
        min_edge=0.05,
        min_confidence=0.6,
        min_liquidity=100.0,
        assumption_notes="fixture",
    )

    batch = evaluate_opportunities(
        [replay_row],
        [market_input],
        thresholds,
        run_id="decision-run",
        provenance_label=BacktestProvenanceLabel.actual_kalshi_historical,
    )

    assert batch.provenance_label is BacktestProvenanceLabel.actual_kalshi_historical
    assert len(batch.accepted_records) == 1
    assert len(batch.rejected_records) == 0

    record = batch.accepted_records[0]
    assert record.selected_side == "negative"
    assert record.confidence == pytest.approx(0.65)
    assert record.market_probability == pytest.approx(0.45)
    assert record.edge == pytest.approx(0.20)
    assert record.expected_value_per_contract == pytest.approx(0.20)
    assert record.accepted is True
    assert record.rejection_reason_codes == ()
    assert record.threshold_snapshot["market_probability_source"] == "normalized_positive_side"
    assert record.threshold_snapshot["liquidity_source"] == "normalized_available_liquidity_dollars"
    assert record.threshold_snapshot["selected_side"] == "negative"
    assert record.threshold_snapshot["min_edge"] == pytest.approx(0.05)


def test_evaluate_opportunities_preserves_rejection_reason_codes_for_invalid_inputs() -> None:
    replay_rows = [
        _replay_row(canonical_match_id="match:low-edge", calibrated_probability=0.54, target=1),
        _replay_row(canonical_match_id="match:missing-prob", calibrated_probability=0.62, target=0),
        _replay_row(canonical_match_id="match:bad-bounds", calibrated_probability=0.71, target=1),
        _replay_row(
            canonical_match_id="match:bad-provenance",
            calibrated_probability=0.66,
            target=0,
        ),
    ]
    market_inputs = [
        NormalizedMarketInput(
            canonical_match_id="match:low-edge",
            market_probability=0.53,
            market_probability_source=MarketProbabilitySource.normalized_positive_side,
            available_liquidity_dollars=200.0,
            liquidity_source="normalized_available_liquidity_dollars",
            provenance_label=BacktestProvenanceLabel.actual_kalshi_historical,
        ),
        NormalizedMarketInput(
            canonical_match_id="match:missing-prob",
            market_probability=None,
            market_probability_source=MarketProbabilitySource.normalized_positive_side,
            available_liquidity_dollars=200.0,
            liquidity_source="normalized_available_liquidity_dollars",
            provenance_label=BacktestProvenanceLabel.actual_kalshi_historical,
        ),
        NormalizedMarketInput(
            canonical_match_id="match:bad-bounds",
            market_probability=1.2,
            market_probability_source=MarketProbabilitySource.normalized_positive_side,
            available_liquidity_dollars=200.0,
            liquidity_source="normalized_available_liquidity_dollars",
            provenance_label=BacktestProvenanceLabel.actual_kalshi_historical,
        ),
        NormalizedMarketInput(
            canonical_match_id="match:bad-provenance",
            market_probability=0.51,
            market_probability_source=MarketProbabilitySource.normalized_positive_side,
            available_liquidity_dollars=200.0,
            liquidity_source="normalized_available_liquidity_dollars",
            provenance_label="unknown_provenance",
        ),
    ]
    thresholds = DecisionThresholds(
        min_edge=0.05,
        min_confidence=0.6,
        min_liquidity=100.0,
        assumption_notes="fixture",
    )

    batch = evaluate_opportunities(
        replay_rows,
        market_inputs,
        thresholds,
        run_id="decision-run",
        provenance_label=BacktestProvenanceLabel.synthetic_proxy,
    )

    assert len(batch.accepted_records) == 0
    assert len(batch.rejected_records) == 4
    reason_sets = {
        record.canonical_match_id: set(record.rejection_reason_codes)
        for record in batch.rejected_records
    }
    assert reason_sets["match:low-edge"] == {"below_min_edge", "below_min_confidence"}
    assert reason_sets["match:missing-prob"] == {"missing_market_probability"}
    assert reason_sets["match:bad-bounds"] == {"invalid_probability_bounds"}
    assert reason_sets["match:bad-provenance"] == {"unsupported_provenance"}
    assert batch.rejected_records[-1].threshold_snapshot["provenance_label"] == "unknown_provenance"


def _replay_row(
    *,
    canonical_match_id: str = "match:001",
    calibrated_probability: float,
    target: int,
) -> ReplayPredictionRow:
    return ReplayPredictionRow(
        artifact_run_id="logistic-replay-run",
        model_name="logistic_regression_baseline",
        model_family="logistic_regression",
        canonical_match_id=canonical_match_id,
        player_a_id="player:a",
        player_b_id="player:b",
        as_of_date="20240101",
        surface="Hard",
        tourney_level="A",
        round_name="R32",
        best_of=3,
        player_a_rank=10,
        player_b_rank=25,
        rank_diff=-15,
        target=target,
        feature_version="03-01-test",
        split_manifest_id="split-001",
        source_commit_sha="deadbeefcafebabe",
        raw_probability=calibrated_probability,
        calibrated_probability=calibrated_probability,
        favored_side="A" if calibrated_probability >= 0.5 else "B",
        favored_probability=max(calibrated_probability, 1.0 - calibrated_probability),
    )
