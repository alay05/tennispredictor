from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
import json
from pathlib import Path

import joblib
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
from tests.unit.modeling_fixtures import build_synthetic_modeling_fixture


@pytest.mark.parametrize(
    ("raw_fit_builder", "expected_family", "expected_raw_model_file"),
    [
        (fit_logistic_regression_baseline, "logistic_regression", "raw_model.joblib"),
        (fit_random_forest_baseline, "random_forest", "raw_model.joblib"),
        (fit_xgboost_candidate, "xgboost", "raw_model.ubj"),
    ],
)
def test_write_model_artifact_bundle_persists_immutable_reports_and_provenance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_fit_builder: Callable[..., RawModelFitResult],
    expected_family: str,
    expected_raw_model_file: str,
) -> None:
    dataset, manifest_path, manifest, settings = _build_dataset_manifest_and_settings(
        tmp_path,
        monkeypatch,
    )
    raw_fit_result = _with_source_version_label(raw_fit_builder(dataset, manifest_path))
    calibrated_result = calibrate_model_probabilities(
        raw_fit_result,
        dataset,
        manifest_path,
        method="sigmoid",
    )
    metrics = evaluate_probability_predictions(
        _targets_for_ids(dataset, manifest.test.canonical_match_ids),
        calibrated_result.calibrated_test_probabilities,
    )
    run_id = f"{expected_family}-artifact-run"

    artifact_dir = write_model_artifact_bundle(
        run_id,
        raw_fit_result,
        calibrated_result,
        metrics,
        manifest,
        settings,
    )

    assert artifact_dir == settings.models_dir / "runs" / run_id
    assert (artifact_dir / "manifest.json").is_file()
    assert (artifact_dir / "feature_columns.json").is_file()
    assert (artifact_dir / "split_manifest.json").is_file()
    assert (artifact_dir / expected_raw_model_file).is_file()
    assert (artifact_dir / "calibrator.joblib").is_file()

    report_dir = settings.reports_dir / "modeling" / run_id
    assert (report_dir / "metrics.json").is_file()
    assert (report_dir / "calibration_curve.csv").is_file()
    assert (report_dir / "calibration_bins.csv").is_file()
    assert (report_dir / "segment_diagnostics.csv").is_file()
    assert (report_dir / "test_predictions.parquet").is_file()

    manifest_payload = _read_json(artifact_dir / "manifest.json")
    assert manifest_payload["run_id"] == run_id
    assert manifest_payload["model_family"] == expected_family
    assert manifest_payload["source_commit_sha"] == dataset.rows[0].lineage_source_commit_sha
    assert manifest_payload["source_version_label"] == "sackmann-atp-2024"
    assert manifest_payload["feature_version"] == dataset.feature_version
    assert manifest_payload["split_manifest_id"] == manifest.split_id
    assert manifest_payload["split_boundaries"] == {
        "train_end_date": manifest.train_end_date,
        "validation_end_date": manifest.validation_end_date,
        "test_end_date": manifest.test_end_date,
    }
    assert manifest_payload["model_params"] == raw_fit_result.model_params
    assert manifest_payload["calibrator_metadata"]["method"] == "sigmoid"
    assert manifest_payload["metrics_provenance"]["calibration_curve_artifact"] == (
        "uniform_10_bin_calibration_curve"
    )
    assert set(manifest_payload["report_files"]) == {
        "metrics",
        "calibration_curve",
        "calibration_bins",
        "segment_diagnostics",
        "test_predictions",
    }

    with pytest.raises(FileExistsError):
        write_model_artifact_bundle(
            run_id,
            raw_fit_result,
            calibrated_result,
            metrics,
            manifest,
            settings,
        )


@pytest.mark.parametrize(
    ("raw_fit_builder", "run_id"),
    [
        (fit_logistic_regression_baseline, "logistic-guard-run"),
        (fit_random_forest_baseline, "random-forest-guard-run"),
        (fit_xgboost_candidate, "xgboost-guard-run"),
    ],
)
def test_load_model_artifact_bundle_rejects_untrusted_paths_missing_files_and_manifest_mismatches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_fit_builder: Callable[..., RawModelFitResult],
    run_id: str,
) -> None:
    dataset, manifest_path, manifest, settings = _build_dataset_manifest_and_settings(
        tmp_path,
        monkeypatch,
    )
    raw_fit_result = _with_source_version_label(raw_fit_builder(dataset, manifest_path))
    calibrated_result = calibrate_model_probabilities(
        raw_fit_result,
        dataset,
        manifest_path,
        method="sigmoid",
    )
    metrics = evaluate_probability_predictions(
        _targets_for_ids(dataset, manifest.test.canonical_match_ids),
        calibrated_result.calibrated_test_probabilities,
    )
    artifact_dir = write_model_artifact_bundle(
        run_id,
        raw_fit_result,
        calibrated_result,
        metrics,
        manifest,
        settings,
    )

    load_spy = {"count": 0}
    original_joblib_load = joblib.load

    def _counting_joblib_load(path: object) -> object:
        load_spy["count"] += 1
        return original_joblib_load(path)

    monkeypatch.setattr("tennisprediction.modeling.registry.joblib.load", _counting_joblib_load)

    outside_path = tmp_path.parent / "outside-run"
    with pytest.raises(ValueError, match="repository"):
        load_model_artifact_bundle(
            outside_path,
            expected_feature_version=dataset.feature_version,
            expected_split_manifest_id=manifest.split_id,
        )
    assert load_spy["count"] == 0

    with pytest.raises(ValueError, match="feature_version"):
        load_model_artifact_bundle(
            artifact_dir,
            expected_feature_version="wrong-feature-version",
            expected_split_manifest_id=manifest.split_id,
        )
    assert load_spy["count"] == 0

    with pytest.raises(ValueError, match="split manifest"):
        load_model_artifact_bundle(
            artifact_dir,
            expected_feature_version=dataset.feature_version,
            expected_split_manifest_id="wrong-split-id",
        )
    assert load_spy["count"] == 0

    calibrator_path = artifact_dir / "calibrator.joblib"
    calibrator_path.unlink()
    with pytest.raises(FileNotFoundError):
        load_model_artifact_bundle(
            artifact_dir,
            expected_feature_version=dataset.feature_version,
            expected_split_manifest_id=manifest.split_id,
        )
    assert load_spy["count"] == 0


def _build_dataset_manifest_and_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[FrozenModelingDataset, Path, FrozenSplitManifest, Settings]:
    fixture = build_synthetic_modeling_fixture(tmp_path)
    dataset = materialize_modeling_dataset(
        database_path=fixture.database_path,
        feature_version=fixture.feature_version,
    )
    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    settings = Settings(
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        reports_dir=tmp_path / "reports",
        duckdb_path=tmp_path / "data" / "testing.duckdb",
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
    return dataset, manifest_path, manifest, settings


def _targets_for_ids(dataset: FrozenModelingDataset, canonical_match_ids: list[str]) -> list[int]:
    row_lookup = {row.canonical_match_id: row for row in dataset.rows}
    return [row_lookup[canonical_match_id].target for canonical_match_id in canonical_match_ids]


def _with_source_version_label(raw_fit_result: RawModelFitResult) -> RawModelFitResult:
    return replace(
        raw_fit_result,
        fit_metadata={
            **raw_fit_result.fit_metadata,
            "source_version_label": "sackmann-atp-2024",
        },
    )


def _read_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))
