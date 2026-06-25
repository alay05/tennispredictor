from __future__ import annotations

import json
import logging
from contextlib import AbstractContextManager
from pathlib import Path
from uuid import uuid4

import duckdb
import pandas as pd

from tennisprediction.backtesting.metrics import (
    estimate_backtest_uncertainty,
    summarize_backtest,
)
from tennisprediction.backtesting.replay import replay_model_predictions
from tennisprediction.backtesting.reports import write_backtest_reports
from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    DecisionThresholds,
    NormalizedMarketInput,
)
from tennisprediction.config import Settings, get_settings
from tennisprediction.domain.models import (
    CanonicalMatch,
    CanonicalMatchStat,
    CanonicalRanking,
    SourceLineage,
)
from tennisprediction.domain.normalization import normalize_snapshot
from tennisprediction.ev.opportunity import evaluate_opportunities
from tennisprediction.features.persistence import persist_feature_build
from tennisprediction.features.runner import build_feature_snapshots
from tennisprediction.ingestion.sackmann_fetcher import SackmannSourceClient
from tennisprediction.ingestion.validation import validate_snapshot
from tennisprediction.kalshi.client import AllowedMarketStatus, KalshiReadClient
from tennisprediction.kalshi.jobs import (
    collect_kalshi_snapshots as collect_kalshi_snapshot_job,
)
from tennisprediction.logging import audit_context, bind_audit_context
from tennisprediction.modeling.baselines import (
    fit_logistic_regression_baseline,
    fit_random_forest_baseline,
)
from tennisprediction.modeling.calibration import calibrate_model_probabilities
from tennisprediction.modeling.datasets import materialize_modeling_dataset
from tennisprediction.modeling.metrics import evaluate_probability_predictions
from tennisprediction.modeling.registry import (
    load_model_artifact_bundle,
    write_model_artifact_bundle,
)
from tennisprediction.modeling.schemas import (
    FrozenModelingDataset,
    FrozenSplitManifest,
    RawModelFitResult,
)
from tennisprediction.modeling.splits import SplitBoundaryConfig, freeze_chronological_splits
from tennisprediction.modeling.xgboost_model import fit_xgboost_candidate
from tennisprediction.monitoring.reports import (
    render_live_monitor_console,
    write_live_monitor_reports,
)
from tennisprediction.monitoring.scan import run_kalshi_ev_scan
from tennisprediction.storage.duckdb import persist_canonical_snapshot

_SACKMANN_ATTRIBUTION = "Jeff Sackmann tennis_atp"
_SACKMANN_LICENSE_NAME = "CC BY-NC-SA 4.0"
_SACKMANN_LICENSE_TEXT = "Attribution required"
_OPERATIONS_LOGGER = logging.getLogger("tennisprediction.operations")


def _command_scope(
    command: str,
    *,
    run_id: str | None = None,
    artifact_run_id: str | None = None,
) -> tuple[logging.LoggerAdapter[logging.Logger], str, AbstractContextManager[None]]:
    effective_run_id = run_id or f"{command}-{uuid4().hex[:12]}"
    context = {
        "run_id": effective_run_id,
        "command": command,
        "artifact_run_id": artifact_run_id or effective_run_id,
    }
    return (
        bind_audit_context(_OPERATIONS_LOGGER, **context),
        effective_run_id,
        audit_context(**context),
    )


def _log_command_event(
    logger: logging.LoggerAdapter[logging.Logger],
    *,
    stage: str,
    message: str,
    **extra: object,
) -> None:
    logger.info(
        message,
        extra={
            "stage": stage,
            **extra,
        },
    )


def ingest_snapshot(
    *,
    source_commit_sha: str,
    database_path: str | Path | None = None,
    settings: Settings | None = None,
) -> Path:
    resolved_settings = settings or get_settings()
    logger, _, context = _command_scope("ingest-snapshot")
    with context:
        _log_command_event(
            logger,
            stage="start",
            message="Starting ingest snapshot command",
            decision_state="command_started",
        )
        manifest = SackmannSourceClient().load_snapshot(
            commit_sha=source_commit_sha,
            attribution_text=_SACKMANN_ATTRIBUTION,
            license_name=_SACKMANN_LICENSE_NAME,
            license_text=_SACKMANN_LICENSE_TEXT,
        )
        validated_snapshot = validate_snapshot(manifest)
        canonical_snapshot = normalize_snapshot(validated_snapshot)
        output_path = persist_canonical_snapshot(
            canonical_snapshot,
            database_path=_database_path(database_path, settings=resolved_settings),
        )
        _log_command_event(
            logger,
            stage="finish",
            message="Finished ingest snapshot command",
            decision_state="command_finished",
            output_path=str(output_path),
        )
        return output_path


def build_features(
    *,
    feature_version: str,
    database_path: str | Path | None = None,
    settings: Settings | None = None,
) -> Path:
    resolved_settings = settings or get_settings()
    resolved_database_path = _database_path(database_path, settings=resolved_settings)
    logger, _, context = _command_scope("build-features")
    with context:
        _log_command_event(
            logger,
            stage="start",
            message="Starting build features command",
            decision_state="command_started",
        )
        feature_build = build_feature_snapshots(
            matches=_load_canonical_matches(resolved_database_path),
            rankings=_load_canonical_rankings(resolved_database_path),
            match_stats=_load_canonical_match_stats(resolved_database_path),
            feature_version=feature_version,
        )
        output_path = persist_feature_build(
            feature_build,
            database_path=resolved_database_path,
        )
        _log_command_event(
            logger,
            stage="finish",
            message="Finished build features command",
            decision_state="command_finished",
            output_path=str(output_path),
        )
        return output_path


def train_artifact_bundle(
    *,
    run_id: str,
    feature_version: str,
    train_end_date: str,
    validation_end_date: str,
    test_end_date: str,
    database_path: str | Path | None = None,
    model_family: str | None = None,
    calibration_method: str | None = None,
    settings: Settings | None = None,
) -> Path:
    resolved_settings = settings or get_settings()
    logger, _, context = _command_scope(
        "train-artifact-bundle",
        run_id=run_id,
        artifact_run_id=run_id,
    )
    with context:
        _log_command_event(
            logger,
            stage="start",
            message="Starting train artifact bundle command",
            decision_state="command_started",
        )
        dataset = materialize_modeling_dataset(
            database_path=_database_path(database_path, settings=resolved_settings),
            feature_version=feature_version,
        )
        split_manifest = freeze_chronological_splits(
            dataset,
            SplitBoundaryConfig(
                train_end_date=train_end_date,
                validation_end_date=validation_end_date,
                test_end_date=test_end_date,
            ),
            resolved_settings,
        )
        resolved_model_family = model_family or resolved_settings.default_model_family
        raw_fit_result = _fit_model(
            dataset=dataset,
            split_manifest=split_manifest,
            model_family=resolved_model_family,
        )
        calibrated_result = calibrate_model_probabilities(
            raw_fit_result,
            dataset,
            split_manifest,
            method=calibration_method or resolved_settings.default_calibration_method,
        )
        metrics_result = evaluate_probability_predictions(
            [row.target for row in calibrated_result.test_predictions],
            [row.calibrated_probability for row in calibrated_result.test_predictions],
        )
        output_path = write_model_artifact_bundle(
            run_id,
            raw_fit_result,
            calibrated_result,
            metrics_result,
            split_manifest,
            resolved_settings,
        )
        _log_command_event(
            logger,
            stage="finish",
            message="Finished train artifact bundle command",
            decision_state="command_finished",
            output_path=str(output_path),
        )
        return output_path


def evaluate_artifact(
    *,
    artifact_dir: str | Path,
    expected_feature_version: str,
    expected_split_manifest_id: str,
    database_path: str | Path | None = None,
    settings: Settings | None = None,
) -> Path:
    resolved_settings = settings or get_settings()
    bundle = load_model_artifact_bundle(
        artifact_dir,
        expected_feature_version=expected_feature_version,
        expected_split_manifest_id=expected_split_manifest_id,
    )
    logger, _, context = _command_scope(
        "evaluate-artifact",
        run_id=bundle.manifest.run_id,
        artifact_run_id=bundle.manifest.run_id,
    )
    with context:
        _log_command_event(
            logger,
            stage="start",
            message="Starting evaluate artifact command",
            decision_state="command_started",
        )
        replay_result = replay_model_predictions(
            artifact_dir,
            _database_path(database_path, settings=resolved_settings),
            expected_feature_version=expected_feature_version,
            expected_split_manifest_id=expected_split_manifest_id,
        )
        metrics_result = evaluate_probability_predictions(
            [row.target for row in replay_result.rows],
            [row.calibrated_probability for row in replay_result.rows],
        )
        evaluation_path = (
            resolved_settings.reports_dir / "modeling" / bundle.manifest.run_id / "evaluation.json"
        )
        evaluation_path.parent.mkdir(parents=True, exist_ok=True)
        evaluation_path.write_text(
            json.dumps(
                {
                    "artifact_run_id": bundle.manifest.run_id,
                    "feature_version": bundle.manifest.feature_version,
                    "split_manifest_id": bundle.manifest.split_manifest_id,
                    "parity_checked": replay_result.parity_checked,
                    "sample_size": len(replay_result.rows),
                    "metrics": {
                        "accuracy": metrics_result.accuracy,
                        "roc_auc": metrics_result.roc_auc,
                        "log_loss": metrics_result.log_loss,
                        "brier_score": metrics_result.brier_score,
                        "expected_calibration_error": metrics_result.expected_calibration_error,
                    },
                },
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        _log_command_event(
            logger,
            stage="finish",
            message="Finished evaluate artifact command",
            decision_state="command_finished",
            output_path=str(evaluation_path),
        )
        return evaluation_path


def run_backtest(
    *,
    artifact_dir: str | Path,
    expected_feature_version: str,
    expected_split_manifest_id: str,
    run_id: str,
    database_path: str | Path | None = None,
    min_edge: float | None = None,
    min_confidence: float | None = None,
    min_liquidity: float | None = None,
    fee_per_contract: float = 0.0,
    slippage_per_contract: float = 0.0,
    settings: Settings | None = None,
) -> Path:
    resolved_settings = settings or get_settings()
    logger, _, context = _command_scope(
        "run-backtest",
        run_id=run_id,
        artifact_run_id=run_id,
    )
    with context:
        _log_command_event(
            logger,
            stage="start",
            message="Starting backtest command",
            decision_state="command_started",
        )
        replay_result = replay_model_predictions(
            artifact_dir,
            _database_path(database_path, settings=resolved_settings),
            expected_feature_version=expected_feature_version,
            expected_split_manifest_id=expected_split_manifest_id,
        )
        thresholds = DecisionThresholds(
            min_edge=min_edge if min_edge is not None else resolved_settings.default_min_edge,
            min_confidence=(
                min_confidence
                if min_confidence is not None
                else resolved_settings.default_min_confidence
            ),
            min_liquidity=(
                min_liquidity
                if min_liquidity is not None
                else resolved_settings.default_min_liquidity
            ),
            fee_per_contract=fee_per_contract,
            slippage_per_contract=slippage_per_contract,
            assumption_notes="synthetic even-money proxy backtest",
        )
        market_inputs = [
            NormalizedMarketInput(
                canonical_match_id=row.canonical_match_id,
                market_probability=0.5,
                market_probability_source="synthetic_even_money_proxy",
                available_liquidity_dollars=max(thresholds.min_liquidity, 100.0),
                liquidity_source="synthetic_backtest_fixture",
                provenance_label=BacktestProvenanceLabel.synthetic_proxy,
                assumption_notes="operator CLI synthetic proxy backtest",
            )
            for row in replay_result.rows
        ]
        decision_batch = evaluate_opportunities(
            replay_result.rows,
            market_inputs,
            thresholds,
            run_id=run_id,
            provenance_label=BacktestProvenanceLabel.synthetic_proxy,
        )
        summary = summarize_backtest(decision_batch)
        uncertainty = estimate_backtest_uncertainty(decision_batch)
        output_path = write_backtest_reports(
            run_id,
            decision_batch,
            summary,
            uncertainty,
            resolved_settings,
        )
        _log_command_event(
            logger,
            stage="finish",
            message="Finished backtest command",
            decision_state="command_finished",
            output_path=str(output_path),
        )
        return output_path


def collect_kalshi_snapshots(
    *,
    access_key: str,
    private_key: Path,
    database_path: str | Path | None = None,
    base_url: str | None = None,
    page_limit: int = 100,
    status: AllowedMarketStatus | None = None,
    settings: Settings | None = None,
) -> Path:
    resolved_settings = settings or get_settings()
    logger, _, context = _command_scope("collect-kalshi-snapshots")
    with context:
        _log_command_event(
            logger,
            stage="start",
            message="Starting Kalshi snapshot collection command",
            decision_state="command_started",
        )
        client = KalshiReadClient(
            access_key=access_key,
            private_key=private_key,
            base_url=base_url,
        )
        try:
            output_path = collect_kalshi_snapshot_job(
                client,
                database_path=_database_path(database_path, settings=resolved_settings),
                page_limit=page_limit,
                status=status,
            )
        finally:
            client.close()
        _log_command_event(
            logger,
            stage="finish",
            message="Finished Kalshi snapshot collection command",
            decision_state="command_finished",
            output_path=str(output_path),
        )
        return output_path


def scan_kalshi_ev(
    *,
    artifact_dir: str | Path,
    expected_feature_version: str,
    expected_split_manifest_id: str,
    database_path: str | Path | None = None,
    collect_fresh: bool = False,
    access_key: str | None = None,
    private_key: Path | None = None,
    base_url: str | None = None,
    run_id: str | None = None,
    min_edge: float | None = None,
    min_confidence: float | None = None,
    min_liquidity: float | None = None,
    fee_per_contract: float = 0.0,
    slippage_per_contract: float = 0.0,
    settings: Settings | None = None,
) -> Path:
    resolved_settings = settings or get_settings()
    effective_run_id = run_id or resolved_settings.default_monitoring_run_id
    logger, _, context = _command_scope(
        "scan-kalshi-ev",
        run_id=effective_run_id,
        artifact_run_id=effective_run_id,
    )
    with context:
        _log_command_event(
            logger,
            stage="start",
            message="Starting Kalshi EV scan command",
            decision_state="command_started",
        )
        thresholds = DecisionThresholds(
            min_edge=min_edge if min_edge is not None else resolved_settings.default_min_edge,
            min_confidence=(
                min_confidence
                if min_confidence is not None
                else resolved_settings.default_min_confidence
            ),
            min_liquidity=(
                min_liquidity
                if min_liquidity is not None
                else resolved_settings.default_min_liquidity
            ),
            fee_per_contract=fee_per_contract,
            slippage_per_contract=slippage_per_contract,
            assumption_notes="read-only live monitor thresholds",
        )
        result = run_kalshi_ev_scan(
            artifact_dir=artifact_dir,
            database_path=_database_path(database_path, settings=resolved_settings),
            expected_feature_version=expected_feature_version,
            expected_split_manifest_id=expected_split_manifest_id,
            thresholds=thresholds,
            run_id=effective_run_id,
            collect_fresh=collect_fresh,
            access_key=access_key,
            private_key=private_key,
            base_url=base_url,
        )
        report_dir = write_live_monitor_reports(
            run_id=result.run_id,
            accepted_rows=result.accepted_records,
            rejected_rows=result.rejected_records,
            settings=resolved_settings,
        )
        if "terminal" in resolved_settings.alert_channels:
            render_live_monitor_console(
                accepted_rows=result.accepted_records,
                rejected_rows=result.rejected_records,
            )
        _log_command_event(
            logger,
            stage="finish",
            message="Finished Kalshi EV scan command",
            decision_state="command_finished",
            output_path=str(report_dir),
        )
        return report_dir


def report_monitoring_run(
    *,
    run_id: str,
    settings: Settings | None = None,
) -> Path:
    resolved_settings = settings or get_settings()
    logger, _, context = _command_scope(
        "review-monitoring-report",
        run_id=run_id,
        artifact_run_id=run_id,
    )
    report_dir = resolved_settings.reports_dir / "monitoring" / run_id
    accepted_path = report_dir / "accepted_opportunities.parquet"
    rejected_path = report_dir / "rejected_opportunities.parquet"
    with context:
        _log_command_event(
            logger,
            stage="start",
            message="Starting monitoring report review command",
            decision_state="command_started",
        )
        if not accepted_path.is_file():
            raise FileNotFoundError(accepted_path)
        if not rejected_path.is_file():
            raise FileNotFoundError(rejected_path)

        accepted_rows = pd.read_parquet(accepted_path).to_dict(orient="records")
        rejected_rows = pd.read_parquet(rejected_path).to_dict(orient="records")
        if "terminal" in resolved_settings.alert_channels:
            render_live_monitor_console(
                accepted_rows=accepted_rows,
                rejected_rows=rejected_rows,
            )
        _log_command_event(
            logger,
            stage="finish",
            message="Finished monitoring report review command",
            decision_state="command_finished",
            output_path=str(report_dir),
        )
        return report_dir


def _database_path(database_path: str | Path | None, *, settings: Settings) -> Path:
    if database_path is None:
        return settings.duckdb_path
    return Settings._resolve_repo_path(Path(database_path))


def _fit_model(
    *,
    dataset: FrozenModelingDataset,
    split_manifest: FrozenSplitManifest,
    model_family: str,
) -> RawModelFitResult:
    if model_family == "logistic_regression":
        return fit_logistic_regression_baseline(dataset, split_manifest)
    if model_family == "random_forest":
        return fit_random_forest_baseline(dataset, split_manifest)
    if model_family == "xgboost":
        return fit_xgboost_candidate(dataset, split_manifest)
    raise ValueError(f"unsupported model_family: {model_family}")


def _build_lineage(
    source_repo: str,
    source_commit_sha: str,
    source_file_path: str,
    source_row_number: int,
    source_snapshot_root: str,
) -> SourceLineage:
    return SourceLineage(
        source_repo=source_repo,
        source_commit_sha=source_commit_sha,
        source_file_path=source_file_path,
        source_row_number=source_row_number,
        source_snapshot_root=source_snapshot_root,
    )


def _load_canonical_matches(database_path: Path) -> list[CanonicalMatch]:
    connection = duckdb.connect(str(database_path))
    try:
        rows = connection.execute(
            """
            select
                canonical_match_id,
                canonical_tournament_id,
                winner_canonical_player_id,
                loser_canonical_player_id,
                source_tourney_id,
                surface,
                tourney_name,
                tourney_level,
                tourney_date,
                round_name,
                best_of,
                score,
                lineage_source_repo,
                lineage_source_commit_sha,
                lineage_source_file_path,
                lineage_source_row_number,
                lineage_source_snapshot_root
            from canonical_matches
            order by
                tourney_date,
                lineage_source_file_path,
                lineage_source_row_number,
                canonical_match_id
            """
        ).fetchall()
    finally:
        connection.close()

    return [
        CanonicalMatch(
            canonical_match_id=canonical_match_id,
            canonical_tournament_id=canonical_tournament_id,
            winner_canonical_player_id=winner_canonical_player_id,
            loser_canonical_player_id=loser_canonical_player_id,
            source_tourney_id=source_tourney_id,
            surface=surface,
            tourney_name=tourney_name,
            tourney_level=tourney_level,
            tourney_date=tourney_date,
            round_name=round_name,
            best_of=best_of,
            score=score,
            lineage=_build_lineage(
                lineage_source_repo,
                lineage_source_commit_sha,
                lineage_source_file_path,
                lineage_source_row_number,
                lineage_source_snapshot_root,
            ),
        )
        for (
            canonical_match_id,
            canonical_tournament_id,
            winner_canonical_player_id,
            loser_canonical_player_id,
            source_tourney_id,
            surface,
            tourney_name,
            tourney_level,
            tourney_date,
            round_name,
            best_of,
            score,
            lineage_source_repo,
            lineage_source_commit_sha,
            lineage_source_file_path,
            lineage_source_row_number,
            lineage_source_snapshot_root,
        ) in rows
    ]


def _load_canonical_rankings(database_path: Path) -> list[CanonicalRanking]:
    connection = duckdb.connect(str(database_path))
    try:
        rows = connection.execute(
            """
            select
                canonical_ranking_id,
                canonical_player_id,
                ranking_date,
                rank,
                points,
                lineage_source_repo,
                lineage_source_commit_sha,
                lineage_source_file_path,
                lineage_source_row_number,
                lineage_source_snapshot_root
            from canonical_rankings
            order by
                ranking_date,
                canonical_player_id,
                lineage_source_file_path,
                lineage_source_row_number
            """
        ).fetchall()
    finally:
        connection.close()

    return [
        CanonicalRanking(
            canonical_ranking_id=canonical_ranking_id,
            canonical_player_id=canonical_player_id,
            ranking_date=ranking_date,
            rank=rank,
            points=points,
            lineage=_build_lineage(
                lineage_source_repo,
                lineage_source_commit_sha,
                lineage_source_file_path,
                lineage_source_row_number,
                lineage_source_snapshot_root,
            ),
        )
        for (
            canonical_ranking_id,
            canonical_player_id,
            ranking_date,
            rank,
            points,
            lineage_source_repo,
            lineage_source_commit_sha,
            lineage_source_file_path,
            lineage_source_row_number,
            lineage_source_snapshot_root,
        ) in rows
    ]


def _load_canonical_match_stats(database_path: Path) -> list[CanonicalMatchStat]:
    connection = duckdb.connect(str(database_path))
    try:
        rows = connection.execute(
            """
            select
                canonical_match_stat_id,
                source_match_id,
                first_won_player1,
                first_won_player2,
                ace_player1,
                ace_player2,
                serve_points_player1,
                serve_points_player2,
                lineage_source_repo,
                lineage_source_commit_sha,
                lineage_source_file_path,
                lineage_source_row_number,
                lineage_source_snapshot_root
            from canonical_match_stats
            order by
                source_match_id,
                lineage_source_file_path,
                lineage_source_row_number
            """
        ).fetchall()
    finally:
        connection.close()

    return [
        CanonicalMatchStat(
            canonical_match_stat_id=canonical_match_stat_id,
            source_match_id=source_match_id,
            first_won_player1=first_won_player1,
            first_won_player2=first_won_player2,
            ace_player1=ace_player1,
            ace_player2=ace_player2,
            serve_points_player1=serve_points_player1,
            serve_points_player2=serve_points_player2,
            lineage=_build_lineage(
                lineage_source_repo,
                lineage_source_commit_sha,
                lineage_source_file_path,
                lineage_source_row_number,
                lineage_source_snapshot_root,
            ),
        )
        for (
            canonical_match_stat_id,
            source_match_id,
            first_won_player1,
            first_won_player2,
            ace_player1,
            ace_player2,
            serve_points_player1,
            serve_points_player2,
            lineage_source_repo,
            lineage_source_commit_sha,
            lineage_source_file_path,
            lineage_source_row_number,
            lineage_source_snapshot_root,
        ) in rows
    ]
