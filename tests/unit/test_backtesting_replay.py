from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import tennisprediction.config as config_module
from tennisprediction.backtesting.replay import replay_model_predictions
from tennisprediction.config import Settings
from tennisprediction.modeling.baselines import fit_logistic_regression_baseline
from tennisprediction.modeling.calibration import calibrate_model_probabilities
from tennisprediction.modeling.datasets import materialize_modeling_dataset
from tennisprediction.modeling.metrics import evaluate_probability_predictions
from tennisprediction.modeling.registry import write_model_artifact_bundle
from tennisprediction.modeling.splits import SplitBoundaryConfig, freeze_chronological_splits
from tests.unit.modeling_fixtures import build_synthetic_modeling_fixture


def test_replay_model_predictions_loads_trusted_bundle_and_regenerates_frozen_test_window(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture, manifest, artifact_dir, settings = _build_phase03_bundle(tmp_path, monkeypatch)

    result = replay_model_predictions(
        artifact_dir,
        fixture.database_path,
        expected_feature_version=fixture.feature_version,
        expected_split_manifest_id=manifest.split_id,
    )

    assert result.artifact_run_id == "logistic-replay-run"
    assert result.feature_version == fixture.feature_version
    assert result.split_manifest_id == manifest.split_id
    assert result.parity_checked is True
    assert len(result.rows) == manifest.test.row_count
    assert [row.canonical_match_id for row in result.rows] == manifest.test.canonical_match_ids

    saved_predictions = pd.read_parquet(
        settings.reports_dir / "modeling" / result.artifact_run_id / "test_predictions.parquet"
    )
    assert saved_predictions["canonical_match_id"].tolist() == [
        row.canonical_match_id for row in result.rows
    ]
    assert saved_predictions["calibrated_probability"].tolist() == pytest.approx(
        [row.calibrated_probability for row in result.rows]
    )
    assert all(row.artifact_run_id == result.artifact_run_id for row in result.rows)
    assert all(row.feature_version == fixture.feature_version for row in result.rows)
    assert all(row.split_manifest_id == manifest.split_id for row in result.rows)
    assert all(row.source_commit_sha == manifest.source_commit_sha for row in result.rows)


def test_replay_model_predictions_rejects_expected_metadata_mismatches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture, manifest, artifact_dir, _settings = _build_phase03_bundle(tmp_path, monkeypatch)

    with pytest.raises(ValueError):
        replay_model_predictions(
            artifact_dir,
            fixture.database_path,
            expected_feature_version="wrong-feature-version",
            expected_split_manifest_id=manifest.split_id,
        )


def _build_phase03_bundle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[object, object, Path, Settings]:
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
    raw_fit_result = fit_logistic_regression_baseline(dataset, manifest_path)
    calibrated_result = calibrate_model_probabilities(
        raw_fit_result,
        dataset,
        manifest_path,
    )
    row_lookup = {row.canonical_match_id: row for row in dataset.rows}
    test_targets = [
        row_lookup[canonical_match_id].target
        for canonical_match_id in manifest.test.canonical_match_ids
    ]
    metrics = evaluate_probability_predictions(
        test_targets,
        calibrated_result.calibrated_test_probabilities,
    )
    artifact_dir = write_model_artifact_bundle(
        "logistic-replay-run",
        raw_fit_result,
        calibrated_result,
        metrics,
        manifest,
        settings,
    )
    return fixture, manifest, artifact_dir, settings
