from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from tennisprediction.config import Settings
from tennisprediction.modeling.metrics import build_segment_diagnostics
from tennisprediction.modeling.schemas import CalibratedModelResult, ProbabilityMetrics


def write_model_reports(
    run_id: str,
    calibrated_result: CalibratedModelResult,
    metrics_result: ProbabilityMetrics,
    settings: Settings,
) -> Path:
    report_dir = settings.reports_dir / "modeling" / run_id
    report_dir.mkdir(parents=True, exist_ok=False)

    metrics_payload = {
        "model_family": metrics_result.model_family,
        "accuracy": metrics_result.accuracy,
        "roc_auc": metrics_result.roc_auc,
        "log_loss": metrics_result.log_loss,
        "brier_score": metrics_result.brier_score,
        "expected_calibration_error": metrics_result.expected_calibration_error,
        "calibration_curve_artifact": metrics_result.calibration_curve_artifact,
    }
    (report_dir / "metrics.json").write_text(
        json.dumps(metrics_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    _write_csv(
        report_dir / "calibration_curve.csv",
        [asdict(row) for row in metrics_result.calibration_curve],
    )
    _write_csv(
        report_dir / "calibration_bins.csv",
        [asdict(row) for row in metrics_result.calibration_bins],
    )
    _write_csv(
        report_dir / "segment_diagnostics.csv",
        [asdict(row) for row in build_segment_diagnostics(calibrated_result.test_predictions)],
    )
    _write_parquet(
        report_dir / "test_predictions.parquet",
        [asdict(row) for row in calibrated_result.test_predictions],
    )

    return report_dir


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame.from_records(rows).to_csv(path, index=False)


def _write_parquet(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame.from_records(rows).to_parquet(path, index=False)
