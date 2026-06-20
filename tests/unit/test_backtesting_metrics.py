from __future__ import annotations

from dataclasses import replace

import pytest

from tennisprediction.backtesting.metrics import estimate_backtest_uncertainty, summarize_backtest
from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    DecisionThresholds,
    OpportunityDecisionBatch,
    OpportunityDecisionRecord,
)


def test_summarize_backtest_computes_chronological_equity_curve_and_drawdown() -> None:
    batch = _decision_batch()

    summary = summarize_backtest(batch)
    uncertainty = estimate_backtest_uncertainty(batch)

    assert summary.sample_size == 3
    assert summary.accepted_count == 3
    assert summary.rejected_count == 1
    assert summary.win_rate == pytest.approx(2 / 3)
    assert summary.average_edge == pytest.approx(0.1666666667)
    assert summary.gross_profit == pytest.approx(0.7)
    assert summary.net_profit == pytest.approx(0.5)
    assert summary.total_staked == pytest.approx(0.6)
    assert summary.roi == pytest.approx(0.5 / 0.6)
    assert summary.max_drawdown == pytest.approx(0.2)
    assert [point.canonical_match_id for point in summary.equity_curve] == [
        "match:001",
        "match:002",
        "match:003",
    ]
    assert [point.cumulative_profit for point in summary.equity_curve] == pytest.approx(
        [-0.2, 0.1, 0.5]
    )
    assert [point.drawdown for point in summary.equity_curve] == pytest.approx(
        [0.2, 0.0, 0.0]
    )
    assert uncertainty.sample_size == 3
    assert uncertainty.net_profit_lower <= uncertainty.net_profit_upper
    assert uncertainty.roi_lower <= uncertainty.roi_upper


def _decision_batch() -> OpportunityDecisionBatch:
    thresholds = DecisionThresholds(
        min_edge=0.05,
        min_confidence=0.6,
        min_liquidity=100.0,
        assumption_notes="fixture",
    )
    accepted_records = [
        _accepted_record("match:003", "20240103", 0.1, 0.4, 0.4),
        _accepted_record("match:001", "20240101", 0.2, -0.2, -0.2),
        _accepted_record("match:002", "20240102", 0.3, 0.3, 0.3),
    ]
    rejected_records = [
        replace(
            accepted_records[0],
            accepted=False,
            rejection_reason_codes=("below_min_edge",),
            realized_outcome=None,
            realized_pnl=None,
        )
    ]
    return OpportunityDecisionBatch(
        run_id="backtest-run",
        artifact_run_id="artifact-run",
        feature_version="03-01-test",
        split_manifest_id="split-001",
        source_commit_sha="deadbeefcafebabe",
        provenance_label=BacktestProvenanceLabel.actual_kalshi_historical,
        assumption_notes="fixture",
        thresholds=thresholds,
        accepted_records=accepted_records,
        rejected_records=rejected_records,
    )


def _accepted_record(
    canonical_match_id: str,
    as_of_date: str,
    market_probability: float,
    edge: float,
    realized_pnl: float,
) -> OpportunityDecisionRecord:
    return OpportunityDecisionRecord(
        artifact_run_id="artifact-run",
        canonical_match_id=canonical_match_id,
        model_name="logistic_regression_baseline",
        model_family="logistic_regression",
        feature_version="03-01-test",
        split_manifest_id="split-001",
        source_commit_sha="deadbeefcafebabe",
        as_of_date=as_of_date,
        selected_side="positive",
        model_probability=market_probability + edge,
        market_probability=market_probability,
        edge=edge,
        expected_value_per_contract=edge,
        confidence=market_probability + edge,
        available_liquidity_dollars=250.0,
        market_probability_source="normalized_positive_side",
        liquidity_source="normalized_available_liquidity_dollars",
        provenance_label=BacktestProvenanceLabel.actual_kalshi_historical,
        threshold_snapshot={
            "min_edge": 0.05,
            "min_confidence": 0.6,
            "min_liquidity": 100.0,
        },
        accepted=True,
        rejection_reason_codes=(),
        realized_outcome=1 if realized_pnl > 0 else 0,
        realized_pnl=realized_pnl,
    )
