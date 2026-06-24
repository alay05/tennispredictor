from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    DecisionThresholds,
    ExecutableMarketInput,
    ExecutableSideInput,
    OpportunityDecisionBatch,
    OpportunityDecisionRecord,
    ReplayPredictionRow,
)
from tennisprediction.kalshi.snapshots import KalshiOrderbookSnapshotRow
from tennisprediction.market_mapping.schemas import (
    MappingConfidenceTier,
    MarketMappingEvidenceRow,
    MarketMappingState,
)
from tennisprediction.monitoring.scan import run_kalshi_ev_scan


def test_run_kalshi_ev_scan_shadow_mode_scores_only_matched_markets_and_keeps_rejections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot_database_path = tmp_path / "kalshi_snapshots.duckdb"
    artifact_dir = tmp_path / "artifact-bundle"
    thresholds = DecisionThresholds(
        min_edge=0.02,
        min_confidence=0.25,
        min_liquidity=5.0,
        fee_per_contract=0.01,
        slippage_per_contract=0.02,
    )
    matched_row = _matched_mapping_row()
    unmatched_row = _unmatched_mapping_row()
    orderbook_row = _orderbook_row(ticker=matched_row.market_ticker)
    executable_market_input = _executable_market_input(
        canonical_match_id=matched_row.canonical_match_id or "match:001",
        market_ticker=matched_row.market_ticker,
    )
    replay_row = _replay_row(canonical_match_id=matched_row.canonical_match_id or "match:001")
    decision_batch = OpportunityDecisionBatch(
        run_id="scan-001",
        artifact_run_id=replay_row.artifact_run_id,
        feature_version=replay_row.feature_version,
        split_manifest_id=replay_row.split_manifest_id,
        source_commit_sha=replay_row.source_commit_sha,
        provenance_label=BacktestProvenanceLabel.collected_snapshot_replay,
        assumption_notes="fixture assumptions",
        thresholds=thresholds,
        accepted_records=[
            _decision_record(
                replay_row=replay_row,
                accepted=True,
                market_ticker=matched_row.market_ticker,
                expected_value_per_contract=0.12,
                edge=0.09,
                confidence=0.74,
            )
        ],
        rejected_records=[],
    )

    calls: dict[str, object] = {}

    def fake_collect_kalshi_snapshots(*args: object, **kwargs: object) -> Path:
        raise AssertionError("shadow mode must not collect fresh Kalshi snapshots")

    def fake_resolve_kalshi_market_mappings(
        *,
        database_path: Path,
    ) -> list[MarketMappingEvidenceRow]:
        calls["mapping_database_path"] = database_path
        return [matched_row, unmatched_row]

    def fake_load_latest_orderbook_snapshots(
        *,
        database_path: Path,
        tickers: tuple[str, ...],
    ) -> dict[str, KalshiOrderbookSnapshotRow]:
        calls["orderbook_database_path"] = database_path
        calls["orderbook_tickers"] = tickers
        return {matched_row.market_ticker: orderbook_row}

    def fake_predict_matches_for_canonical_ids(
        artifact_dir_arg: Path,
        database_path_arg: Path,
        *,
        canonical_match_ids: tuple[str, ...],
        expected_feature_version: str,
        expected_split_manifest_id: str,
    ) -> list[ReplayPredictionRow]:
        calls["prediction_args"] = {
            "artifact_dir": artifact_dir_arg,
            "database_path": database_path_arg,
            "canonical_match_ids": canonical_match_ids,
            "expected_feature_version": expected_feature_version,
            "expected_split_manifest_id": expected_split_manifest_id,
        }
        return [replay_row]

    def fake_derive_executable_market_input(
        *,
        orderbook_row: KalshiOrderbookSnapshotRow,
        mapping_row: MarketMappingEvidenceRow,
        evaluated_at_utc: datetime,
    ) -> ExecutableMarketInput:
        calls["derived_market_ticker"] = mapping_row.market_ticker
        calls["evaluated_at_utc"] = evaluated_at_utc
        assert orderbook_row.ticker == mapping_row.market_ticker
        return executable_market_input

    def fake_evaluate_opportunities(
        replay_rows: list[ReplayPredictionRow],
        market_inputs: list[ExecutableMarketInput],
        thresholds_arg: DecisionThresholds,
        *,
        run_id: str,
        provenance_label: BacktestProvenanceLabel,
    ) -> OpportunityDecisionBatch:
        calls["evaluate_run_id"] = run_id
        calls["evaluate_market_inputs"] = market_inputs
        assert replay_rows == [replay_row]
        assert market_inputs == [executable_market_input]
        assert thresholds_arg == thresholds
        assert provenance_label == BacktestProvenanceLabel.collected_snapshot_replay
        return decision_batch

    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.collect_kalshi_snapshots",
        fake_collect_kalshi_snapshots,
    )
    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.resolve_kalshi_market_mappings",
        fake_resolve_kalshi_market_mappings,
    )
    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.load_latest_orderbook_snapshots",
        fake_load_latest_orderbook_snapshots,
    )
    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.predict_matches_for_canonical_ids",
        fake_predict_matches_for_canonical_ids,
    )
    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.derive_executable_market_input",
        fake_derive_executable_market_input,
    )
    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.evaluate_opportunities",
        fake_evaluate_opportunities,
    )

    result = run_kalshi_ev_scan(
        artifact_dir=artifact_dir,
        database_path=snapshot_database_path,
        expected_feature_version="feature-v1",
        expected_split_manifest_id="split-001",
        thresholds=thresholds,
        run_id="scan-001",
        collect_fresh=False,
        evaluated_at_utc=datetime(2026, 6, 21, 12, 0, tzinfo=UTC),
    )

    assert result.snapshot_database_path == snapshot_database_path
    assert calls["mapping_database_path"] == snapshot_database_path
    assert calls["orderbook_database_path"] == snapshot_database_path
    assert calls["orderbook_tickers"] == (matched_row.market_ticker,)
    assert calls["prediction_args"] == {
        "artifact_dir": artifact_dir,
        "database_path": snapshot_database_path,
        "canonical_match_ids": ("match:001",),
        "expected_feature_version": "feature-v1",
        "expected_split_manifest_id": "split-001",
    }
    assert calls["derived_market_ticker"] == matched_row.market_ticker
    assert calls["evaluate_run_id"] == "scan-001"
    assert len(result.accepted_records) == 1
    assert len(result.rejected_records) == 1
    assert result.accepted_records[0]["market_ticker"] == matched_row.market_ticker
    assert result.accepted_records[0]["mapping_state"] == MarketMappingState.matched.value
    assert (
        result.accepted_records[0]["mapping_confidence"]
        == MappingConfidenceTier.exact_names.value
    )
    assert result.rejected_records[0]["market_ticker"] == unmatched_row.market_ticker
    assert result.rejected_records[0]["mapping_state"] == MarketMappingState.unmatched.value
    assert (
        result.rejected_records[0]["mapping_confidence"]
        == MappingConfidenceTier.exact_names.value
    )
    assert "timing_window_miss" in result.rejected_records[0]["rejection_reason_codes"]


def test_run_kalshi_ev_scan_collect_fresh_reuses_read_only_snapshot_job(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    persisted_database_path = tmp_path / "fresh_snapshots.duckdb"
    artifact_dir = tmp_path / "artifact-bundle"
    private_key = tmp_path / "kalshi.pem"
    private_key.write_text("fixture private key", encoding="utf-8")
    thresholds = DecisionThresholds(
        min_edge=0.01,
        min_confidence=0.1,
        min_liquidity=1.0,
    )
    matched_row = _matched_mapping_row()
    replay_row = _replay_row(canonical_match_id=matched_row.canonical_match_id or "match:001")
    decision_batch = OpportunityDecisionBatch(
        run_id="scan-live",
        artifact_run_id=replay_row.artifact_run_id,
        feature_version=replay_row.feature_version,
        split_manifest_id=replay_row.split_manifest_id,
        source_commit_sha=replay_row.source_commit_sha,
        provenance_label=BacktestProvenanceLabel.collected_snapshot_replay,
        assumption_notes="fixture assumptions",
        thresholds=thresholds,
        accepted_records=[],
        rejected_records=[],
    )

    calls: dict[str, object] = {}

    class FakeKalshiReadClient:
        def __init__(self, *, access_key: str, private_key: Path, base_url: str | None) -> None:
            calls["client_args"] = {
                "access_key": access_key,
                "private_key": private_key,
                "base_url": base_url,
            }

        def close(self) -> None:
            calls["client_closed"] = True

    def fake_collect_kalshi_snapshots(
        client: FakeKalshiReadClient,
        *,
        database_path: Path | None,
        page_limit: int,
        status: object,
    ) -> Path:
        calls["collect_snapshot_args"] = {
            "client_type": type(client).__name__,
            "database_path": database_path,
            "page_limit": page_limit,
            "status": status,
        }
        return persisted_database_path

    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.KalshiReadClient",
        FakeKalshiReadClient,
    )
    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.collect_kalshi_snapshots",
        fake_collect_kalshi_snapshots,
    )
    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.resolve_kalshi_market_mappings",
        lambda *, database_path: [matched_row],
    )
    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.load_latest_orderbook_snapshots",
        lambda *, database_path, tickers: {
            matched_row.market_ticker: _orderbook_row(ticker=matched_row.market_ticker)
        },
    )
    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.derive_executable_market_input",
        lambda *, orderbook_row, mapping_row, evaluated_at_utc: _executable_market_input(
            canonical_match_id=mapping_row.canonical_match_id or "match:001",
            market_ticker=mapping_row.market_ticker,
        ),
    )
    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.predict_matches_for_canonical_ids",
        lambda *args, **kwargs: [replay_row],
    )
    monkeypatch.setattr(
        "tennisprediction.monitoring.scan.evaluate_opportunities",
        lambda *args, **kwargs: decision_batch,
    )

    result = run_kalshi_ev_scan(
        artifact_dir=artifact_dir,
        database_path=tmp_path / "target.duckdb",
        expected_feature_version="feature-v1",
        expected_split_manifest_id="split-001",
        thresholds=thresholds,
        run_id="scan-live",
        collect_fresh=True,
        access_key="kalshi-access",
        private_key=private_key,
        base_url="https://demo-api.kalshi.co",
    )

    assert result.snapshot_database_path == persisted_database_path
    assert calls["client_args"] == {
        "access_key": "kalshi-access",
        "private_key": private_key,
        "base_url": "https://demo-api.kalshi.co",
    }
    assert calls["collect_snapshot_args"] == {
        "client_type": "FakeKalshiReadClient",
        "database_path": tmp_path / "target.duckdb",
        "page_limit": 100,
        "status": "open",
    }
    assert calls["client_closed"] is True


def _matched_mapping_row() -> MarketMappingEvidenceRow:
    return MarketMappingEvidenceRow(
        market_ticker="KXATP-001",
        event_ticker="ATP-LONDON",
        collected_at_utc=datetime(2026, 6, 21, 11, 55, tzinfo=UTC),
        raw_title="ATP London: Taylor Fritz vs Frances Tiafoe",
        raw_yes_sub_title="Taylor Fritz",
        raw_no_sub_title="Frances Tiafoe",
        normalized_yes_player_name="taylor fritz",
        normalized_no_player_name="frances tiafoe",
        alias_hit_player_ids=(),
        candidate_canonical_match_ids=("match:001",),
        mapping_state=MarketMappingState.matched,
        mapping_confidence=MappingConfidenceTier.exact_names,
        canonical_match_id="match:001",
        yes_canonical_player_id="player:a",
        no_canonical_player_id="player:b",
        yes_maps_to_player_a=True,
        no_maps_to_player_b=True,
        rejection_reason_codes=(),
    )


def _unmatched_mapping_row() -> MarketMappingEvidenceRow:
    return MarketMappingEvidenceRow(
        market_ticker="KXATP-404",
        event_ticker="ATP-LONDON",
        collected_at_utc=datetime(2026, 6, 21, 11, 55, tzinfo=UTC),
        raw_title="ATP London: Unknown vs Unknown",
        raw_yes_sub_title="Unknown One",
        raw_no_sub_title="Unknown Two",
        normalized_yes_player_name="unknown one",
        normalized_no_player_name="unknown two",
        alias_hit_player_ids=(),
        candidate_canonical_match_ids=(),
        mapping_state=MarketMappingState.unmatched,
        mapping_confidence=MappingConfidenceTier.exact_names,
        canonical_match_id=None,
        yes_canonical_player_id=None,
        no_canonical_player_id=None,
        yes_maps_to_player_a=None,
        no_maps_to_player_b=None,
        rejection_reason_codes=("timing_window_miss",),
    )


def _orderbook_row(*, ticker: str) -> KalshiOrderbookSnapshotRow:
    return KalshiOrderbookSnapshotRow(
        request_id="request-001",
        collected_at_utc=datetime(2026, 6, 21, 11, 58, tzinfo=UTC),
        request_method="GET",
        request_path="/trade-api/v2/markets/KXATP-001/orderbook",
        request_base_url="https://demo-api.kalshi.co",
        request_timestamp_ms=1718971080000,
        request_signed_payload="signed",
        request_query_params_json="[]",
        request_cursor=None,
        request_filter_params_json="{}",
        response_status_code=200,
        response_cursor=None,
        response_checksum="checksum",
        response_index=0,
        ticker=ticker,
        yes_levels_json='[{"price_dollars":"0.58","quantity_fp":"20"}]',
        no_levels_json='[{"price_dollars":"0.42","quantity_fp":"18"}]',
        yes_level_count=1,
        no_level_count=1,
        yes_best_price_dollars=None,
        yes_best_quantity_fp=None,
        no_best_price_dollars=None,
        no_best_quantity_fp=None,
    )


def _executable_market_input(
    *,
    canonical_match_id: str,
    market_ticker: str,
) -> ExecutableMarketInput:
    return ExecutableMarketInput(
        canonical_match_id=canonical_match_id,
        market_ticker=market_ticker,
        positive_side="yes",
        negative_side="no",
        yes_side=ExecutableSideInput(
            kalshi_side="yes",
            canonical_player_id="player:a",
            maps_to_player_a=True,
            entry_price=0.58,
            entry_price_source="reciprocal_no_bid_top_of_book",
            available_liquidity_dollars=11.6,
            liquidity_source="top_of_book_notional_from_no_bid_quantity",
            freshness_age_seconds=25.0,
            freshness_source="orderbook_collected_at_utc",
        ),
        no_side=ExecutableSideInput(
            kalshi_side="no",
            canonical_player_id="player:b",
            maps_to_player_a=False,
            entry_price=0.42,
            entry_price_source="reciprocal_yes_bid_top_of_book",
            available_liquidity_dollars=9.8,
            liquidity_source="top_of_book_notional_from_yes_bid_quantity",
            freshness_age_seconds=25.0,
            freshness_source="orderbook_collected_at_utc",
        ),
        provenance_label=BacktestProvenanceLabel.collected_snapshot_replay,
        assumption_notes="top-of-book executable pricing",
    )


def _replay_row(*, canonical_match_id: str) -> ReplayPredictionRow:
    return ReplayPredictionRow(
        artifact_run_id="artifact-run",
        model_name="logistic_regression_baseline",
        model_family="logistic_regression",
        canonical_match_id=canonical_match_id,
        player_a_id="player:a",
        player_b_id="player:b",
        as_of_date="20260621",
        surface="Grass",
        tourney_level="A",
        round_name="R16",
        best_of=3,
        player_a_rank=9,
        player_b_rank=14,
        rank_diff=-5,
        target=1,
        feature_version="feature-v1",
        split_manifest_id="split-001",
        source_commit_sha="deadbeefcafebabe",
        raw_probability=0.64,
        calibrated_probability=0.66,
        favored_side="A",
        favored_probability=0.66,
    )


def _decision_record(
    *,
    replay_row: ReplayPredictionRow,
    accepted: bool,
    market_ticker: str,
    expected_value_per_contract: float,
    edge: float,
    confidence: float,
) -> OpportunityDecisionRecord:
    return OpportunityDecisionRecord(
        artifact_run_id=replay_row.artifact_run_id,
        canonical_match_id=replay_row.canonical_match_id,
        model_name=replay_row.model_name,
        model_family=replay_row.model_family,
        feature_version=replay_row.feature_version,
        split_manifest_id=replay_row.split_manifest_id,
        source_commit_sha=replay_row.source_commit_sha,
        as_of_date=replay_row.as_of_date,
        selected_side="positive",
        model_probability=replay_row.calibrated_probability,
        market_probability=0.58,
        edge=edge,
        expected_value_per_contract=expected_value_per_contract,
        confidence=confidence,
        available_liquidity_dollars=11.6,
        market_probability_source="reciprocal_no_bid_top_of_book",
        liquidity_source="top_of_book_notional_from_no_bid_quantity",
        provenance_label=BacktestProvenanceLabel.collected_snapshot_replay,
        threshold_snapshot={
            "market_ticker": market_ticker,
            "selected_entry_price": 0.58,
        },
        accepted=accepted,
        selected_entry_price=0.58,
        entry_price_source="reciprocal_no_bid_top_of_book",
        freshness_age_seconds=25.0,
        freshness_source="orderbook_collected_at_utc",
        rejection_reason_codes=(),
    )
