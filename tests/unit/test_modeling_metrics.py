from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

import tennisprediction.config as config_module
from tennisprediction.config import Settings
from tennisprediction.modeling.baselines import (
    fit_logistic_regression_baseline,
    fit_random_forest_baseline,
)
from tennisprediction.modeling.calibration import calibrate_model_probabilities
from tennisprediction.modeling.datasets import materialize_modeling_dataset
from tennisprediction.modeling.metrics import evaluate_probability_predictions
from tennisprediction.modeling.schemas import FrozenModelingDataset, FrozenSplitManifest, RawModelFitResult
from tennisprediction.modeling.splits import SplitBoundaryConfig, freeze_chronological_splits
from tennisprediction.modeling.xgboost_model import fit_xgboost_candidate
from tests.unit.modeling_fixtures import build_synthetic_modeling_fixture


@pytest.mark.parametrize(
    ("raw_fit_builder", "expected_family"),
    [
        (fit_logistic_regression_baseline, "logistic_regression"),
        (fit_random_forest_baseline, "random_forest"),
        (fit_xgboost_candidate, "xgboost"),
    ],
)
def test_evaluate_probability_predictions_returns_scalar_metrics_bins_curve_and_ece(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_fit_builder: Callable[..., RawModelFitResult],
    expected_family: str,
) -> None:
    dataset, manifest_path, manifest = _build_dataset_and_manifest(tmp_path, monkeypatch)
    raw_fit_result = raw_fit_builder(dataset, manifest_path)
    calibrated_result = calibrate_model_probabilities(
        raw_fit_result,
        dataset,
        manifest_path,
        method="sigmoid",
    )
    y_true = _targets_for_ids(dataset, manifest.test.canonical_match_ids)

    metrics = evaluate_probability_predictions(
        y_true,
        calibrated_result.calibrated_test_probabilities,
    )

    assert metrics.model_family == expected_family
    assert 0.0 <= metrics.accuracy <= 1.0
    assert 0.0 <= metrics.roc_auc <= 1.0
    assert metrics.log_loss >= 0.0
    assert 0.0 <= metrics.brier_score <= 1.0
    assert metrics.expected_calibration_error >= 0.0
    assert len(metrics.calibration_bins) == 10
    assert [calibration_bin.bin_index for calibration_bin in metrics.calibration_bins] == list(range(10))
    assert sum(calibration_bin.sample_count for calibration_bin in metrics.calibration_bins) == len(y_true)
    assert metrics.calibration_bins[0].lower_bound == pytest.approx(0.0)
    assert metrics.calibration_bins[-1].upper_bound == pytest.approx(1.0)
    assert metrics.calibration_curve_artifact == "uniform_10_bin_calibration_curve"
    assert len(metrics.calibration_curve) >= 1
    assert {
        curve_point.bin_index for curve_point in metrics.calibration_curve
    } <= set(range(10))
    for curve_point in metrics.calibration_curve:
        assert 0.0 <= curve_point.mean_predicted_probability <= 1.0
        assert 0.0 <= curve_point.empirical_positive_rate <= 1.0


def _build_dataset_and_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[FrozenModelingDataset, Path, FrozenSplitManifest]:
    fixture = build_synthetic_modeling_fixture(tmp_path)
    dataset = materialize_modeling_dataset(
        database_path=fixture.database_path,
        feature_version=fixture.feature_version,
    )
    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    settings = Settings(
        data_dir=Path("data"),
        models_dir=Path("models"),
        reports_dir=Path("reports"),
        duckdb_path=Path("data/testing.duckdb"),
    )
    manifest = freeze_chronological_splits(
        dataset,
        SplitBoundaryConfig(
            train_end_date=fixture.resolved_train_end_date,
            validation_end_date=fixture.resolved_validation_end_date,
            test_end_date=fixture.resolved_test_end_date,
        ),
        settings,
    )
    manifest_path = settings.models_dir / "splits" / f"{manifest.split_id}.json"
    return dataset, manifest_path, manifest


def _targets_for_ids(dataset: FrozenModelingDataset, canonical_match_ids: list[str]) -> list[int]:
    row_lookup = {row.canonical_match_id: row for row in dataset.rows}
    return [row_lookup[canonical_match_id].target for canonical_match_id in canonical_match_ids]
