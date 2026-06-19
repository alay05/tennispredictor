from __future__ import annotations

from importlib.metadata import version
from pathlib import Path

import pandas as pd
import pytest

import tennisprediction.config as config_module
from tennisprediction.config import Settings
from tennisprediction.modeling.baselines import (
    fit_logistic_regression_baseline,
    fit_random_forest_baseline,
)
from tennisprediction.modeling.datasets import materialize_modeling_dataset
from tennisprediction.modeling.schemas import (
    FrozenModelingDataset,
    FrozenSplitManifest,
    FrozenSplitWindow,
)
from tennisprediction.modeling.splits import (
    SplitBoundaryConfig,
    freeze_chronological_splits,
)
from tests.unit.modeling_fixtures import (
    build_synthetic_modeling_fixture,
    membership_sha256,
)


def test_ml_dependency_group_imports_approved_runtime() -> None:
    assert version("joblib").startswith("1.5.")
    assert version("pandas").startswith("3.0.")
    assert version("scikit-learn").startswith("1.9.")
    assert version("xgboost").startswith("3.2.")
    assert pd.__name__ == "pandas"


def test_fit_logistic_regression_baseline_uses_train_membership_and_manifest_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, manifest_path, manifest = _build_dataset_and_manifest(tmp_path, monkeypatch)
    custom_train_ids = manifest.train.canonical_match_ids[::2]
    custom_manifest = manifest.model_copy(
        update={
            "train": _window_for_ids(dataset=dataset, canonical_match_ids=custom_train_ids),
        }
    )
    custom_manifest_path = manifest_path.with_name("custom-logistic-split.json")
    custom_manifest_path.write_text(custom_manifest.model_dump_json(indent=2), encoding="utf-8")

    result = fit_logistic_regression_baseline(dataset, custom_manifest_path)

    assert result.model_name == "logistic_regression_baseline"
    assert result.model_family == "logistic_regression"
    assert result.feature_columns == dataset.feature_columns
    assert result.split_manifest_path == str(custom_manifest_path)
    assert result.train_row_count == len(custom_train_ids)
    assert result.validation_row_count == custom_manifest.validation.row_count
    assert result.test_row_count == custom_manifest.test.row_count
    assert result.model_params["max_iter"] == 1000
    assert result.model_params["random_state"] == 42
    assert result.trained_estimator is not None
    assert result.raw_model_artifact_path is None

    _assert_probabilities_follow_manifest_order(
        dataset=dataset,
        canonical_match_ids=custom_manifest.validation.canonical_match_ids,
        feature_columns=result.feature_columns,
        trained_estimator=result.trained_estimator,
        probabilities=result.validation_probabilities,
    )
    _assert_probabilities_follow_manifest_order(
        dataset=dataset,
        canonical_match_ids=custom_manifest.test.canonical_match_ids,
        feature_columns=result.feature_columns,
        trained_estimator=result.trained_estimator,
        probabilities=result.test_probabilities,
    )


def test_fit_random_forest_baseline_preserves_feature_contract_and_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, manifest_path, manifest = _build_dataset_and_manifest(tmp_path, monkeypatch)
    custom_train_ids = manifest.train.canonical_match_ids[::2]
    custom_manifest = manifest.model_copy(
        update={
            "train": _window_for_ids(dataset=dataset, canonical_match_ids=custom_train_ids),
        }
    )
    custom_manifest_path = manifest_path.with_name("custom-random-forest-split.json")
    custom_manifest_path.write_text(custom_manifest.model_dump_json(indent=2), encoding="utf-8")

    result = fit_random_forest_baseline(dataset, custom_manifest_path)

    assert result.model_name == "random_forest_baseline"
    assert result.model_family == "random_forest"
    assert result.feature_columns == dataset.feature_columns
    assert result.split_manifest_path == str(custom_manifest_path)
    assert result.train_row_count == len(custom_train_ids)
    assert result.validation_row_count == custom_manifest.validation.row_count
    assert result.test_row_count == custom_manifest.test.row_count
    assert result.model_params["n_estimators"] == 400
    assert result.model_params["random_state"] == 42
    assert result.model_params["n_jobs"] == -1
    assert result.trained_estimator is not None
    assert result.raw_model_artifact_path is None

    _assert_probabilities_follow_manifest_order(
        dataset=dataset,
        canonical_match_ids=custom_manifest.validation.canonical_match_ids,
        feature_columns=result.feature_columns,
        trained_estimator=result.trained_estimator,
        probabilities=result.validation_probabilities,
    )
    _assert_probabilities_follow_manifest_order(
        dataset=dataset,
        canonical_match_ids=custom_manifest.test.canonical_match_ids,
        feature_columns=result.feature_columns,
        trained_estimator=result.trained_estimator,
        probabilities=result.test_probabilities,
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


def _window_for_ids(
    *,
    dataset: FrozenModelingDataset,
    canonical_match_ids: list[str],
) -> FrozenSplitWindow:
    row_lookup = {row.canonical_match_id: row for row in dataset.rows}
    rows = [row_lookup[canonical_match_id] for canonical_match_id in canonical_match_ids]
    return FrozenSplitWindow(
        canonical_match_ids=canonical_match_ids,
        row_count=len(canonical_match_ids),
        first_as_of_date=rows[0].as_of_date,
        last_as_of_date=rows[-1].as_of_date,
        membership_sha256=membership_sha256(canonical_match_ids),
    )


def _assert_probabilities_follow_manifest_order(
    *,
    dataset: FrozenModelingDataset,
    canonical_match_ids: list[str],
    feature_columns: list[str],
    trained_estimator: object,
    probabilities: list[float],
) -> None:
    feature_frame = _feature_frame(
        dataset=dataset,
        canonical_match_ids=canonical_match_ids,
        feature_columns=feature_columns,
    )
    expected_probabilities = trained_estimator.predict_proba(feature_frame)[:, 1].tolist()
    assert probabilities == pytest.approx(expected_probabilities)


def _feature_frame(
    *,
    dataset: FrozenModelingDataset,
    canonical_match_ids: list[str],
    feature_columns: list[str],
) -> pd.DataFrame:
    row_lookup = {row.canonical_match_id: row for row in dataset.rows}
    return pd.DataFrame.from_records(
        [
            {
                feature_column: row_lookup[canonical_match_id].feature_values[feature_column]
                for feature_column in feature_columns
            }
            for canonical_match_id in canonical_match_ids
        ],
        columns=feature_columns,
    )
