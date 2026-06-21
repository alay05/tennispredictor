from __future__ import annotations

import pytest

from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    DecisionThresholds,
    ExecutableMarketInput,
    ExecutableSideInput,
    ReplayPredictionRow,
)
from tennisprediction.ev.opportunity import evaluate_opportunities


def test_evaluate_opportunities_uses_explicit_no_entry_price_and_preserves_pricing_evidence() -> None:
    replay_row = _replay_row(calibrated_probability=0.61, target=0)
    thresholds = DecisionThresholds(
        min_edge=0.05,
        min_confidence=0.35,
        min_liquidity=5.0,
        fee_per_contract=0.02,
        slippage_per_contract=0.01,
        assumption_notes="fixture assumptions",
    )
    market_input = ExecutableMarketInput(
        canonical_match_id=replay_row.canonical_match_id,
        market_ticker="KXATP-001",
        positive_side="yes",
        negative_side="no",
        yes_side=ExecutableSideInput(
            kalshi_side="yes",
            canonical_player_id="player:a",
            maps_to_player_a=True,
            entry_price=0.64,
            entry_price_source="reciprocal_no_bid_top_of_book",
            available_liquidity_dollars=12.5,
            liquidity_source="top_of_book_notional_from_no_bid_quantity",
            freshness_age_seconds=30.0,
            freshness_source="orderbook_collected_at_utc",
        ),
        no_side=ExecutableSideInput(
            kalshi_side="no",
            canonical_player_id="player:b",
            maps_to_player_a=False,
            entry_price=0.28,
            entry_price_source="reciprocal_yes_bid_top_of_book",
            available_liquidity_dollars=8.4,
            liquidity_source="top_of_book_notional_from_yes_bid_quantity",
            freshness_age_seconds=30.0,
            freshness_source="orderbook_collected_at_utc",
        ),
        provenance_label=BacktestProvenanceLabel.collected_snapshot_replay,
        assumption_notes="top-of-book executable pricing",
    )

    batch = evaluate_opportunities(
        [replay_row],
        [market_input],
        thresholds,
        run_id="live-scan-pricing",
        provenance_label=BacktestProvenanceLabel.collected_snapshot_replay,
    )

    assert len(batch.accepted_records) == 1
    assert len(batch.rejected_records) == 0
    record = batch.accepted_records[0]
    assert record.selected_side == "negative"
    assert record.market_probability == pytest.approx(0.28)
    assert record.selected_entry_price == pytest.approx(0.28)
    assert record.entry_price_source == "reciprocal_yes_bid_top_of_book"
    assert record.edge == pytest.approx(0.11)
    assert record.expected_value_per_contract == pytest.approx(0.08)
    assert record.available_liquidity_dollars == pytest.approx(8.4)
    assert (
        record.liquidity_source == "top_of_book_notional_from_yes_bid_quantity"
    )
    assert record.freshness_age_seconds == pytest.approx(30.0)
    assert record.freshness_source == "orderbook_collected_at_utc"
    assert record.rejection_reason_codes == ()
    assert record.threshold_snapshot["selected_entry_price"] == pytest.approx(0.28)
    assert record.threshold_snapshot["entry_price_source"] == "reciprocal_yes_bid_top_of_book"
    assert record.threshold_snapshot["liquidity_source"] == "top_of_book_notional_from_yes_bid_quantity"
    assert record.threshold_snapshot["freshness_age_seconds"] == pytest.approx(30.0)
    assert record.threshold_snapshot["freshness_source"] == "orderbook_collected_at_utc"
    assert record.threshold_snapshot["fee_per_contract"] == pytest.approx(0.02)
    assert record.threshold_snapshot["slippage_per_contract"] == pytest.approx(0.01)


def test_evaluate_opportunities_keeps_stale_side_rejections_with_pricing_evidence() -> None:
    replay_row = _replay_row(calibrated_probability=0.75, target=1)
    thresholds = DecisionThresholds(
        min_edge=0.05,
        min_confidence=0.6,
        min_liquidity=5.0,
        fee_per_contract=0.01,
        slippage_per_contract=0.02,
    )
    market_input = ExecutableMarketInput(
        canonical_match_id=replay_row.canonical_match_id,
        market_ticker="KXATP-002",
        positive_side="yes",
        negative_side="no",
        yes_side=ExecutableSideInput(
            kalshi_side="yes",
            canonical_player_id="player:a",
            maps_to_player_a=True,
            entry_price=0.40,
            entry_price_source="reciprocal_no_bid_top_of_book",
            available_liquidity_dollars=9.2,
            liquidity_source="top_of_book_notional_from_no_bid_quantity",
            freshness_age_seconds=180.0,
            freshness_source="orderbook_collected_at_utc",
            rejection_reason_codes=("stale_orderbook",),
        ),
        no_side=ExecutableSideInput(
            kalshi_side="no",
            canonical_player_id="player:b",
            maps_to_player_a=False,
            entry_price=0.70,
            entry_price_source="reciprocal_yes_bid_top_of_book",
            available_liquidity_dollars=8.0,
            liquidity_source="top_of_book_notional_from_yes_bid_quantity",
            freshness_age_seconds=30.0,
            freshness_source="orderbook_collected_at_utc",
        ),
        provenance_label=BacktestProvenanceLabel.collected_snapshot_replay,
        assumption_notes="top-of-book executable pricing",
    )

    batch = evaluate_opportunities(
        [replay_row],
        [market_input],
        thresholds,
        run_id="live-scan-pricing",
        provenance_label=BacktestProvenanceLabel.collected_snapshot_replay,
    )

    assert len(batch.accepted_records) == 0
    assert len(batch.rejected_records) == 1
    record = batch.rejected_records[0]
    assert record.selected_side == "positive"
    assert record.selected_entry_price == pytest.approx(0.40)
    assert record.entry_price_source == "reciprocal_no_bid_top_of_book"
    assert record.available_liquidity_dollars == pytest.approx(9.2)
    assert record.freshness_age_seconds == pytest.approx(180.0)
    assert record.freshness_source == "orderbook_collected_at_utc"
    assert "stale_orderbook" in record.rejection_reason_codes
    assert record.threshold_snapshot["selected_entry_price"] == pytest.approx(0.40)
    assert record.threshold_snapshot["entry_price_source"] == "reciprocal_no_bid_top_of_book"
    assert record.threshold_snapshot["freshness_age_seconds"] == pytest.approx(180.0)


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
