from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

import tennisprediction.config as config_module
from tennisprediction.config import Settings
from tennisprediction.modeling.datasets import materialize_modeling_dataset
from tennisprediction.modeling.schemas import (
    FrozenModelingDataset,
    FrozenSplitManifest,
    FrozenSplitWindow,
)
from tennisprediction.modeling.splits import SplitBoundaryConfig, freeze_chronological_splits
from tennisprediction.modeling.xgboost_model import (
    XGBoostTrainingConfig,
    fit_xgboost_candidate,
)
from tests.unit.modeling_fixtures import build_synthetic_modeling_fixture, membership_sha256


def test_fit_xgboost_candidate_uses_train_membership_only_and_reserves_tail_eval_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset, manifest_path, manifest = _build_dataset_and_manifest(tmp_path, monkeypatch)
    custom_train_ids = manifest.train.canonical_match_ids[:10] + manifest.train.canonical_match_ids[-4:]
    custom_manifest = manifest.model_copy(
        update={
            "train": _window_for_ids(dataset=dataset, canonical_match_ids=custom_train_ids),
        }
    )
    custom_manifest_path = manifest_path.with_name("custom-xgboost-split.json")
    custom_manifest_path.write_text(custom_manifest.model_dump_json(indent=2), encoding="utf-8")

    result = fit_xgboost_candidate(
        dataset,
        custom_manifest_path,
        XGBoostTrainingConfig(),
    )

    expected_eval_ids = custom_train_ids[-3:]
    expected_fit_ids = custom_train_ids[:-3]

    assert result.model_name == "xgboost_candidate"
    assert result.model_family == "xgboost"
    assert result.feature_columns == dataset.feature_columns
    assert result.split_manifest_path == str(custom_manifest_path)
    assert result.train_row_count == len(custom_train_ids)
    assert result.validation_row_count == custom_manifest.validation.row_count
    assert result.test_row_count == custom_manifest.test.row_count
    assert result.model_params == {
        "n_estimators": 400,
        "learning_rate": 0.05,
        "max_depth": 6,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 1,
        "reg_lambda": 1.0,
        "random_state": 42,
        "early_stopping_rounds": 25,
    }
    assert result.trained_estimator is not None
    assert result.raw_model_artifact_path is None
    assert result.fit_metadata["fit_row_count"] == len(expected_fit_ids)
    assert result.fit_metadata["eval_row_count"] == len(expected_eval_ids)
    assert result.fit_metadata["fit_membership_sha256"] == membership_sha256(expected_fit_ids)
    assert result.fit_metadata["eval_membership_sha256"] == membership_sha256(expected_eval_ids)
    assert result.fit_metadata["best_iteration"] is not None
    assert result.fit_metadata["best_score"] is not None

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
