from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest
from sklearn.frozen import FrozenEstimator

import tennisprediction.config as config_module
from tennisprediction.config import Settings
from tennisprediction.modeling.baselines import (
    fit_logistic_regression_baseline,
    fit_random_forest_baseline,
)
from tennisprediction.modeling.calibration import calibrate_model_probabilities
from tennisprediction.modeling.datasets import materialize_modeling_dataset
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
def test_calibrate_model_probabilities_uses_validation_rows_only_and_returns_typed_predictions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_fit_builder: Callable[..., RawModelFitResult],
    expected_family: str,
) -> None:
    dataset, manifest_path, manifest = _build_dataset_and_manifest(tmp_path, monkeypatch)
    raw_fit_result = raw_fit_builder(dataset, manifest_path)
    recording_instances: list[RecordingCalibratedClassifierCV] = []

    class RecordingCalibrator(RecordingCalibratedClassifierCV):
        def __init__(self, *args: object, **kwargs: object) -> None:
            super().__init__(*args, **kwargs)
            recording_instances.append(self)

    monkeypatch.setattr(
        "tennisprediction.modeling.calibration.CalibratedClassifierCV",
        RecordingCalibrator,
    )

    result = calibrate_model_probabilities(
        raw_fit_result,
        dataset,
        manifest_path,
        method="sigmoid",
    )

    calibrator = recording_instances[-1]
    assert isinstance(calibrator.estimator, FrozenEstimator)
    assert calibrator.method == "sigmoid"
    assert calibrator.fit_row_count == manifest.validation.row_count
    assert calibrator.predict_row_counts == [manifest.validation.row_count, manifest.test.row_count]

    assert result.model_name == raw_fit_result.model_name
    assert result.model_family == expected_family
    assert result.calibration_method == "sigmoid"
    assert result.calibrator is not None
    assert result.validation_row_count == manifest.validation.row_count
    assert result.test_row_count == manifest.test.row_count
    assert result.validation_membership_sha256 == manifest.validation.membership_sha256
    assert result.test_membership_sha256 == manifest.test.membership_sha256
    assert len(result.calibrated_validation_probabilities) == manifest.validation.row_count
    assert len(result.calibrated_test_probabilities) == manifest.test.row_count
    assert [
        row.canonical_match_id for row in result.validation_predictions
    ] == manifest.validation.canonical_match_ids
    assert [row.canonical_match_id for row in result.test_predictions] == manifest.test.canonical_match_ids

    row_lookup = {row.canonical_match_id: row for row in dataset.rows}
    for prediction_row in result.validation_predictions + result.test_predictions:
        source_row = row_lookup[prediction_row.canonical_match_id]
        assert prediction_row.as_of_date == source_row.as_of_date
        assert prediction_row.surface == source_row.feature_values["surface"]
        assert prediction_row.tourney_level == source_row.feature_values["tourney_level"]
        assert prediction_row.player_a_rank == source_row.feature_values["player_a_rank"]
        assert prediction_row.player_b_rank == source_row.feature_values["player_b_rank"]
        assert prediction_row.rank_diff == source_row.feature_values["rank_diff"]
        assert prediction_row.raw_probability in raw_fit_result.validation_probabilities + raw_fit_result.test_probabilities
        assert 0.0 <= prediction_row.calibrated_probability <= 1.0
        assert prediction_row.favored_side in {"A", "B"}
        assert prediction_row.favored_probability == pytest.approx(
            max(
                prediction_row.calibrated_probability,
                1.0 - prediction_row.calibrated_probability,
            )
        )


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


class RecordingCalibratedClassifierCV:
    def __init__(
        self,
        estimator: object = None,
        *,
        method: str = "sigmoid",
        **_: object,
    ) -> None:
        from sklearn.calibration import CalibratedClassifierCV as RealCalibratedClassifierCV

        self.estimator = estimator
        self.method = method
        self.fit_row_count = 0
        self.predict_row_counts: list[int] = []
        self._inner = RealCalibratedClassifierCV(estimator=estimator, method=method)

    def fit(self, X: object, y: object) -> RecordingCalibratedClassifierCV:
        self.fit_row_count = len(y)
        self._inner.fit(X, y)
        return self

    def predict_proba(self, X: object) -> object:
        self.predict_row_counts.append(len(X))
        return self._inner.predict_proba(X)

