from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import tennisprediction.config as config_module
from tennisprediction.backtesting.metrics import estimate_backtest_uncertainty, summarize_backtest
from tennisprediction.backtesting.provenance import guard_profitability_claims
from tennisprediction.backtesting.reports import write_backtest_reports
from tennisprediction.backtesting.schemas import BacktestProvenanceLabel
from tests.unit.test_backtesting_metrics import _decision_batch


def test_guard_profitability_claims_requires_actual_history_and_persists_report_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch = _decision_batch()
    synthetic_batch = batch.__class__(
        run_id="backtest-run",
        artifact_run_id=batch.artifact_run_id,
        feature_version=batch.feature_version,
        split_manifest_id=batch.split_manifest_id,
        source_commit_sha=batch.source_commit_sha,
        provenance_label=BacktestProvenanceLabel.synthetic_proxy,
        assumption_notes=batch.assumption_notes,
        thresholds=batch.thresholds,
        accepted_records=batch.accepted_records,
        rejected_records=batch.rejected_records,
    )
    summary = summarize_backtest(synthetic_batch)
    uncertainty = estimate_backtest_uncertainty(synthetic_batch)

    claim_guard = guard_profitability_claims(
        summary,
        uncertainty,
        provenance_label=BacktestProvenanceLabel.synthetic_proxy,
        assumption_notes=synthetic_batch.assumption_notes,
    )
    assert claim_guard.allowed is False
    assert "synthetic_proxy" in claim_guard.banner

    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    settings = config_module.Settings(
        data_dir=Path("data"),
        models_dir=Path("models"),
        reports_dir=Path("reports"),
        duckdb_path=Path("data/testing.duckdb"),
    )

    report_dir = write_backtest_reports(
        "backtest-run",
        synthetic_batch,
        summary,
        uncertainty,
        settings,
    )

    assert report_dir.is_dir()
    assert (report_dir / "summary.json").is_file()
    assert (report_dir / "uncertainty.json").is_file()
    assert (report_dir / "provenance.json").is_file()
    assert (report_dir / "equity_curve.csv").is_file()
    assert (report_dir / "decision_reason_counts.csv").is_file()
    assert (report_dir / "accepted_opportunities.parquet").is_file()
    assert (report_dir / "rejected_opportunities.parquet").is_file()

    summary_payload = pd.read_json(report_dir / "summary.json", typ="series")
    assert summary_payload["claim_allowed"] is False
    assert summary_payload["provenance_label"] == "synthetic_proxy"

    provenance_payload = pd.read_json(report_dir / "provenance.json", typ="series")
    assert provenance_payload["claim_allowed"] is False
    assert provenance_payload["provenance_label"] == "synthetic_proxy"

    accepted = pd.read_parquet(report_dir / "accepted_opportunities.parquet")
    rejected = pd.read_parquet(report_dir / "rejected_opportunities.parquet")
    assert len(accepted) == len(synthetic_batch.accepted_records)
    assert len(rejected) == len(synthetic_batch.rejected_records)
    assert set(rejected["rejection_reason_codes"].iloc[0]) == {"below_min_edge"}
