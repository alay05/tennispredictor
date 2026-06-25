from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from rich.console import Console

import tennisprediction.config as config_module
from tennisprediction import operations
from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    DecisionThresholds,
    NormalizedMarketInput,
    OpportunityDecisionBatch,
    OpportunityDecisionRecord,
    ReplayPredictionRow,
)
from tennisprediction.config import Settings
from tennisprediction.ev.opportunity import evaluate_opportunities
from tennisprediction.logging import bind_audit_context, configure_logging
from tennisprediction.market_mapping.resolver import require_matched_mapping
from tennisprediction.market_mapping.schemas import (
    MappingConfidenceTier,
    MarketMappingEvidenceRow,
    MarketMappingState,
)
from tennisprediction.monitoring.alerts import render_operator_report


class _ListHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def test_configure_logging_emits_stable_context_to_console_and_repo_local_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    logger = configure_logging(settings)
    audit_logger = bind_audit_context(
        logger,
        run_id="run-001",
        command="scan-kalshi-ev",
        stage="bootstrap",
    )

    audit_logger.info(
        "configured operational logging",
        extra={
            "market_ticker": "KXATP-DJO-A",
            "mapping_state": "matched",
            "decision_state": "accepted",
        },
    )
    _flush_handlers(logger)

    file_handlers = [
        handler for handler in logger.handlers if isinstance(handler, logging.FileHandler)
    ]
    stream_handlers = [
        handler for handler in logger.handlers if isinstance(handler, logging.StreamHandler)
    ]

    assert file_handlers, "configure_logging() should fan out to a repo-local file handler"
    assert stream_handlers, "configure_logging() should retain console output"

    audit_log_path = settings.reports_dir / "audit" / "operations.log"
    assert audit_log_path.is_file()

    audit_log = audit_log_path.read_text(encoding="utf-8")
    assert "run-001" in audit_log
    assert "scan-kalshi-ev" in audit_log
    assert "bootstrap" in audit_log
    assert "KXATP-DJO-A" in audit_log
    assert "matched" in audit_log
    assert "accepted" in audit_log


def test_operations_wrappers_emit_start_and_finish_audit_events(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    logger = configure_logging(settings)
    collector = _attach_collector(logger)

    monkeypatch.setattr(
        operations,
        "SackmannSourceClient",
        lambda: _FakeSackmannClient(manifest={"snapshot": "raw"}),
    )
    monkeypatch.setattr(operations, "validate_snapshot", lambda manifest: {"validated": manifest})
    monkeypatch.setattr(operations, "normalize_snapshot", lambda snapshot: {"normalized": snapshot})
    monkeypatch.setattr(
        operations,
        "persist_canonical_snapshot",
        lambda snapshot, database_path: Path(database_path),
    )

    monkeypatch.setattr(operations, "_load_canonical_matches", lambda _: ["match"])
    monkeypatch.setattr(operations, "_load_canonical_rankings", lambda _: ["ranking"])
    monkeypatch.setattr(operations, "_load_canonical_match_stats", lambda _: ["stats"])
    monkeypatch.setattr(
        operations,
        "build_feature_snapshots",
        lambda **kwargs: {"feature_version": kwargs["feature_version"]},
    )
    monkeypatch.setattr(
        operations,
        "persist_feature_build",
        lambda feature_build, database_path: Path(database_path).with_name("features.duckdb"),
    )

    monkeypatch.setattr(operations, "materialize_modeling_dataset", lambda **_: {"rows": 2})
    monkeypatch.setattr(
        operations,
        "freeze_chronological_splits",
        lambda *args, **kwargs: {"split": "001"},
    )
    monkeypatch.setattr(operations, "_fit_model", lambda **_: {"fit": "ok"})
    monkeypatch.setattr(
        operations,
        "calibrate_model_probabilities",
        lambda *args, **kwargs: _fake_calibration_result(),
    )
    monkeypatch.setattr(
        operations,
        "evaluate_probability_predictions",
        lambda *args, **kwargs: _FakeMetrics(),
    )
    monkeypatch.setattr(
        operations,
        "write_model_artifact_bundle",
        lambda run_id, *args, **kwargs: settings.models_dir / run_id,
    )

    monkeypatch.setattr(
        operations,
        "load_model_artifact_bundle",
        lambda *args, **kwargs: _FakeBundleManifestContainer(run_id="artifact-001"),
    )
    monkeypatch.setattr(
        operations,
        "replay_model_predictions",
        lambda *args, **kwargs: _fake_replay_result(),
    )
    monkeypatch.setattr(
        operations,
        "summarize_backtest",
        lambda batch: {"accepted": len(batch.accepted_records)},
    )
    monkeypatch.setattr(operations, "estimate_backtest_uncertainty", lambda batch: {"bands": []})
    monkeypatch.setattr(
        operations,
        "evaluate_opportunities",
        lambda replay_rows, market_inputs, thresholds, **kwargs: _fake_decision_batch(
            run_id=kwargs["run_id"],
            artifact_run_id=replay_rows[0].artifact_run_id,
        ),
    )
    monkeypatch.setattr(
        operations,
        "write_backtest_reports",
        lambda run_id, *args, **kwargs: settings.reports_dir / "backtesting" / run_id,
    )

    monkeypatch.setattr(
        operations,
        "KalshiReadClient",
        _FakeKalshiReadClient,
    )
    monkeypatch.setattr(
        operations,
        "collect_kalshi_snapshot_job",
        lambda client, **kwargs: Path(kwargs["database_path"]),
    )

    monkeypatch.setattr(
        operations,
        "run_kalshi_ev_scan",
        lambda **kwargs: _FakeScanRunResult(
            run_id=kwargs["run_id"],
            snapshot_database_path=settings.duckdb_path,
            accepted_records=[_accepted_alert_row()],
            rejected_records=[_rejected_alert_row()],
        ),
    )
    monkeypatch.setattr(
        operations,
        "write_live_monitor_reports",
        (
            lambda *, run_id, accepted_rows, rejected_rows, settings: (
                settings.reports_dir / "monitoring" / run_id
            )
        ),
    )
    monkeypatch.setattr(operations, "render_live_monitor_console", lambda **kwargs: None)
    monkeypatch.setattr(
        operations.pd,
        "read_parquet",
        lambda path: pd.DataFrame(
            [_accepted_alert_row()] if "accepted" in str(path) else [_rejected_alert_row()]
        ),
    )

    operations.ingest_snapshot(
        source_commit_sha="0123456789abcdef0123456789abcdef01234567",
        settings=settings,
    )
    operations.build_features(feature_version="feature-v1", settings=settings)
    operations.train_artifact_bundle(
        run_id="train-001",
        feature_version="feature-v1",
        train_end_date="2024-01-01",
        validation_end_date="2024-06-01",
        test_end_date="2024-12-01",
        settings=settings,
    )
    operations.evaluate_artifact(
        artifact_dir=settings.models_dir / "artifact-001",
        expected_feature_version="feature-v1",
        expected_split_manifest_id="split-001",
        settings=settings,
    )
    operations.run_backtest(
        artifact_dir=settings.models_dir / "artifact-001",
        expected_feature_version="feature-v1",
        expected_split_manifest_id="split-001",
        run_id="backtest-001",
        settings=settings,
    )
    operations.collect_kalshi_snapshots(
        access_key="access-key",
        private_key=tmp_path / "kalshi.pem",
        settings=settings,
    )
    operations.scan_kalshi_ev(
        artifact_dir=settings.models_dir / "artifact-001",
        expected_feature_version="feature-v1",
        expected_split_manifest_id="split-001",
        run_id="scan-001",
        settings=settings,
    )
    report_dir = settings.reports_dir / "monitoring" / "scan-001"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "accepted_opportunities.parquet").write_text("fixture", encoding="utf-8")
    (report_dir / "rejected_opportunities.parquet").write_text("fixture", encoding="utf-8")
    operations.report_monitoring_run(
        run_id="scan-001",
        settings=settings,
    )

    start_commands = {
        record.command
        for record in collector.records
        if getattr(record, "stage", None) == "start"
    }
    finish_commands = {
        record.command
        for record in collector.records
        if getattr(record, "stage", None) == "finish"
    }
    expected_commands = {
        "ingest-snapshot",
        "build-features",
        "train-artifact-bundle",
        "evaluate-artifact",
        "run-backtest",
        "collect-kalshi-snapshots",
        "scan-kalshi-ev",
        "review-monitoring-report",
    }

    assert start_commands == expected_commands
    assert finish_commands == expected_commands
    assert all(getattr(record, "run_id", "") for record in collector.records)


def test_monitoring_decision_seams_emit_reason_coded_audit_summaries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    logger = configure_logging(settings)
    collector = _attach_collector(logger)

    mapping_row = _mapping_row(
        mapping_state=MarketMappingState.ambiguous,
        mapping_confidence=MappingConfidenceTier.manual_review_required,
        rejection_reason_codes=("multiple_candidate_matches",),
    )

    unscorable = require_matched_mapping(mapping_row)
    assert unscorable is not None

    thresholds = DecisionThresholds(
        min_edge=0.05,
        min_confidence=0.35,
        min_liquidity=5.0,
        assumption_notes="unit-test",
    )
    decision_batch = evaluate_opportunities(
        [_replay_row()],
        [
            NormalizedMarketInput(
                canonical_match_id="match-001",
                market_probability=0.42,
                market_probability_source="manual_fixture",
                available_liquidity_dollars=30.0,
                liquidity_source="fixture",
                provenance_label=BacktestProvenanceLabel.synthetic_proxy,
                assumption_notes="fixture",
            )
        ],
        thresholds,
        run_id="scan-001",
    )
    assert decision_batch.accepted_records

    console = Console(record=True, width=160)
    render_operator_report(
        accepted_rows=[_accepted_alert_row()],
        rejected_rows=[_rejected_alert_row()],
        console=console,
    )

    assert any(
        getattr(record, "mapping_state", None) == "ambiguous"
        for record in collector.records
    )
    assert any(
        getattr(record, "decision_state", None) == "accepted"
        for record in collector.records
    )
    assert any(
        getattr(record, "rejection_reason", None) == "multiple_candidate_matches"
        for record in collector.records
    )


def test_logging_redacts_kalshi_sensitive_values_from_records_and_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path, monkeypatch)
    logger = configure_logging(settings)
    collector = _attach_collector(logger)
    audit_logger = bind_audit_context(
        logger,
        run_id="run-002",
        command="collect-kalshi-snapshots",
        stage="request",
    )

    private_key_path = tmp_path / "kalshi-private-key.pem"
    private_key_path.write_text("-----BEGIN PRIVATE KEY-----\nsecret-material\n", encoding="utf-8")

    audit_logger.info(
        "issuing signed kalshi request",
        extra={
            "access_key": "kalshi-access-key",
            "authorization": "Bearer super-secret-token",
            "private_key": private_key_path.read_text(encoding="utf-8"),
            "private_key_path": str(private_key_path),
        },
    )
    _flush_handlers(logger)

    assert collector.records, "expected log records from the redaction test"
    redacted_record = collector.records[-1]
    assert getattr(redacted_record, "access_key", None) == "[REDACTED]"
    assert getattr(redacted_record, "authorization", None) == "[REDACTED]"
    assert getattr(redacted_record, "private_key", None) == "[REDACTED]"
    assert getattr(redacted_record, "private_key_path", None) == "[REDACTED]"

    audit_log = (settings.reports_dir / "audit" / "operations.log").read_text(encoding="utf-8")
    assert "kalshi-access-key" not in audit_log
    assert "super-secret-token" not in audit_log
    assert "secret-material" not in audit_log
    assert str(private_key_path) not in audit_log
    assert "[REDACTED]" in audit_log


def _settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    return Settings(
        data_dir=Path("data"),
        models_dir=Path("models"),
        reports_dir=Path("reports"),
        duckdb_path=Path("data/testing.duckdb"),
        alert_channels=("terminal", "file"),
    )


def _attach_collector(logger: logging.Logger) -> _ListHandler:
    handler = _ListHandler()
    logger.addHandler(handler)
    return handler


def _flush_handlers(logger: logging.Logger) -> None:
    for handler in logger.handlers:
        if hasattr(handler, "flush"):
            handler.flush()


@dataclass(frozen=True)
class _FakeMetrics:
    accuracy: float = 0.6
    roc_auc: float = 0.7
    log_loss: float = 0.5
    brier_score: float = 0.2
    expected_calibration_error: float = 0.03


@dataclass(frozen=True)
class _FakeBundleManifest:
    run_id: str
    feature_version: str = "feature-v1"
    split_manifest_id: str = "split-001"


@dataclass(frozen=True)
class _FakeBundleManifestContainer:
    run_id: str

    @property
    def manifest(self) -> _FakeBundleManifest:
        return _FakeBundleManifest(run_id=self.run_id)


@dataclass(frozen=True)
class _FakeCalibrationResult:
    test_predictions: list[ReplayPredictionRow]


@dataclass(frozen=True)
class _FakeScanRunResult:
    run_id: str
    snapshot_database_path: Path
    accepted_records: list[dict[str, object]]
    rejected_records: list[dict[str, object]]


class _FakeSackmannClient:
    def __init__(self, manifest: dict[str, object]) -> None:
        self._manifest = manifest

    def load_snapshot(self, **_: object) -> dict[str, object]:
        return self._manifest


class _FakeKalshiReadClient:
    def __init__(self, *, access_key: str, private_key: Path, base_url: str | None = None) -> None:
        self.access_key = access_key
        self.private_key = private_key
        self.base_url = base_url

    def close(self) -> None:
        return None


def _fake_replay_result() -> Any:
    @dataclass(frozen=True)
    class _ReplayResult:
        rows: list[ReplayPredictionRow]
        parity_checked: bool = True

    return _ReplayResult(rows=[_replay_row()])


def _fake_calibration_result() -> _FakeCalibrationResult:
    return _FakeCalibrationResult(test_predictions=[_replay_row()])


def _fake_decision_batch(*, run_id: str, artifact_run_id: str) -> OpportunityDecisionBatch:
    thresholds = DecisionThresholds(
        min_edge=0.05,
        min_confidence=0.35,
        min_liquidity=5.0,
        assumption_notes="fixture",
    )
    record = OpportunityDecisionRecord(
        artifact_run_id=artifact_run_id,
        canonical_match_id="match-001",
        model_name="logistic-regression",
        model_family="logistic_regression",
        feature_version="feature-v1",
        split_manifest_id="split-001",
        source_commit_sha="0123456789abcdef0123456789abcdef01234567",
        as_of_date="2024-07-01",
        selected_side="positive",
        model_probability=0.66,
        market_probability=0.42,
        edge=0.24,
        expected_value_per_contract=0.18,
        confidence=0.66,
        available_liquidity_dollars=25.0,
        market_probability_source="manual_fixture",
        liquidity_source="fixture",
        provenance_label=BacktestProvenanceLabel.synthetic_proxy,
        threshold_snapshot={"selected_side": "positive"},
        accepted=True,
        rejection_reason_codes=(),
    )
    return OpportunityDecisionBatch(
        run_id=run_id,
        artifact_run_id=artifact_run_id,
        feature_version="feature-v1",
        split_manifest_id="split-001",
        source_commit_sha="0123456789abcdef0123456789abcdef01234567",
        provenance_label=BacktestProvenanceLabel.synthetic_proxy,
        assumption_notes="fixture",
        thresholds=thresholds,
        accepted_records=[record],
        rejected_records=[],
    )


def _replay_row() -> ReplayPredictionRow:
    return ReplayPredictionRow(
        artifact_run_id="artifact-001",
        model_name="logistic-regression",
        model_family="logistic_regression",
        canonical_match_id="match-001",
        player_a_id="player-a",
        player_b_id="player-b",
        as_of_date="2024-07-01",
        surface="Hard",
        tourney_level="ATP-500",
        round_name="F",
        best_of=3,
        player_a_rank=1,
        player_b_rank=2,
        rank_diff=-1,
        target=1,
        feature_version="feature-v1",
        split_manifest_id="split-001",
        source_commit_sha="0123456789abcdef0123456789abcdef01234567",
        raw_probability=0.63,
        calibrated_probability=0.66,
        favored_side="A",
        favored_probability=0.66,
    )


def _mapping_row(
    *,
    mapping_state: MarketMappingState,
    mapping_confidence: MappingConfidenceTier,
    rejection_reason_codes: tuple[str, ...],
) -> MarketMappingEvidenceRow:
    return MarketMappingEvidenceRow(
        market_ticker="KXATP-001",
        event_ticker="ATP-FINAL",
        collected_at_utc=datetime.now(UTC),
        raw_title="Novak Djokovic vs Carlos Alcaraz",
        raw_yes_sub_title="Novak Djokovic",
        raw_no_sub_title="Carlos Alcaraz",
        normalized_yes_player_name="novak djokovic",
        normalized_no_player_name="carlos alcaraz",
        alias_hit_player_ids=(),
        candidate_canonical_match_ids=("match-001",),
        mapping_state=mapping_state,
        mapping_confidence=mapping_confidence,
        canonical_match_id="match-001",
        yes_canonical_player_id="player-a",
        no_canonical_player_id="player-b",
        yes_maps_to_player_a=True,
        no_maps_to_player_b=True,
        rejection_reason_codes=rejection_reason_codes,
    )


def _accepted_alert_row() -> dict[str, object]:
    return {
        "canonical_match_id": "match-001",
        "matchup": "Novak Djokovic vs Carlos Alcaraz",
        "market_ticker": "KXATP-001",
        "model_probability": 0.66,
        "market_probability": 0.42,
        "edge": 0.24,
        "expected_value_per_contract": 0.18,
        "available_liquidity_dollars": 25.0,
        "confidence": 0.66,
        "freshness_age_seconds": 90.0,
        "mapping_state": "matched",
        "mapping_confidence": "exact_names",
    }


def _rejected_alert_row() -> dict[str, object]:
    return {
        "canonical_match_id": None,
        "matchup": "Unknown Match",
        "market_ticker": "KXATP-404",
        "mapping_state": "ambiguous",
        "mapping_confidence": "manual_review_required",
        "rejection_reason_codes": ["multiple_candidate_matches"],
    }
