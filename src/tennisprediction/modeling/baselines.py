from __future__ import annotations

from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from tennisprediction.modeling.schemas import (
    FeatureValue,
    FrozenModelingDataset,
    FrozenSplitManifest,
    RawModelFitResult,
)
from tennisprediction.modeling.splits import load_split_manifest


def fit_logistic_regression_baseline(
    dataset: FrozenModelingDataset,
    split_manifest: FrozenSplitManifest | str | Path,
) -> RawModelFitResult:
    manifest, manifest_path = _resolve_split_manifest(split_manifest)
    _validate_dataset_and_manifest(dataset=dataset, manifest=manifest)
    feature_groups = _infer_feature_groups(dataset)

    estimator = Pipeline(
        steps=[
            (
                "preprocessor",
                _build_preprocessor(feature_groups=feature_groups, scale_numeric=True),
            ),
            (
                "classifier",
                LogisticRegression(
                    max_iter=1000,
                    random_state=42,
                ),
            ),
        ]
    )
    return _fit_baseline(
        dataset=dataset,
        manifest=manifest,
        manifest_path=manifest_path,
        estimator=estimator,
        model_name="logistic_regression_baseline",
        model_family="logistic_regression",
        model_params={
            "max_iter": 1000,
            "random_state": 42,
        },
        fit_metadata={
            "numeric_imputer_strategy": "median",
            "categorical_imputer_strategy": "most_frequent",
            "categorical_encoder": "one_hot_ignore_unknown",
            "numeric_scaler": True,
        },
    )


def fit_random_forest_baseline(
    dataset: FrozenModelingDataset,
    split_manifest: FrozenSplitManifest | str | Path,
) -> RawModelFitResult:
    manifest, manifest_path = _resolve_split_manifest(split_manifest)
    _validate_dataset_and_manifest(dataset=dataset, manifest=manifest)
    feature_groups = _infer_feature_groups(dataset)

    estimator = Pipeline(
        steps=[
            (
                "preprocessor",
                _build_preprocessor(feature_groups=feature_groups, scale_numeric=False),
            ),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=400,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )
    return _fit_baseline(
        dataset=dataset,
        manifest=manifest,
        manifest_path=manifest_path,
        estimator=estimator,
        model_name="random_forest_baseline",
        model_family="random_forest",
        model_params={
            "n_estimators": 400,
            "random_state": 42,
            "n_jobs": -1,
        },
        fit_metadata={
            "numeric_imputer_strategy": "median",
            "categorical_imputer_strategy": "most_frequent",
            "categorical_encoder": "one_hot_ignore_unknown",
            "numeric_scaler": False,
        },
    )


def _fit_baseline(
    *,
    dataset: FrozenModelingDataset,
    manifest: FrozenSplitManifest,
    manifest_path: str,
    estimator: Pipeline,
    model_name: str,
    model_family: str,
    model_params: dict[str, FeatureValue],
    fit_metadata: dict[str, FeatureValue],
) -> RawModelFitResult:
    train_frame, train_target = _build_split_frame_and_target(
        dataset=dataset,
        canonical_match_ids=manifest.train.canonical_match_ids,
    )
    validation_frame, _ = _build_split_frame_and_target(
        dataset=dataset,
        canonical_match_ids=manifest.validation.canonical_match_ids,
    )
    test_frame, _ = _build_split_frame_and_target(
        dataset=dataset,
        canonical_match_ids=manifest.test.canonical_match_ids,
    )

    estimator.fit(train_frame, train_target)

    return RawModelFitResult(
        model_name=model_name,
        model_family=model_family,
        feature_columns=list(dataset.feature_columns),
        split_manifest_path=manifest_path,
        train_row_count=manifest.train.row_count,
        validation_row_count=manifest.validation.row_count,
        test_row_count=manifest.test.row_count,
        validation_probabilities=_predict_probabilities(estimator, validation_frame),
        test_probabilities=_predict_probabilities(estimator, test_frame),
        model_params=model_params,
        trained_estimator=estimator,
        raw_model_artifact_path=None,
        fit_metadata={
            **fit_metadata,
            "split_id": manifest.split_id,
            "feature_version": dataset.feature_version,
            "label_definition": dataset.label_definition,
            "train_membership_sha256": manifest.train.membership_sha256,
            "validation_membership_sha256": manifest.validation.membership_sha256,
            "test_membership_sha256": manifest.test.membership_sha256,
        },
    )


def _resolve_split_manifest(
    split_manifest: FrozenSplitManifest | str | Path,
) -> tuple[FrozenSplitManifest, str]:
    if isinstance(split_manifest, FrozenSplitManifest):
        return split_manifest, split_manifest.split_id

    manifest_path = Path(split_manifest)
    return load_split_manifest(manifest_path), str(manifest_path)


def _validate_dataset_and_manifest(
    *,
    dataset: FrozenModelingDataset,
    manifest: FrozenSplitManifest,
) -> None:
    if dataset.feature_version != manifest.feature_version:
        msg = "dataset feature_version must match split manifest feature_version"
        raise ValueError(msg)
    if dataset.label_definition != manifest.label_definition:
        msg = "dataset label_definition must match split manifest label_definition"
        raise ValueError(msg)

    known_match_ids = {row.canonical_match_id for row in dataset.rows}
    requested_match_ids = (
        manifest.train.canonical_match_ids
        + manifest.validation.canonical_match_ids
        + manifest.test.canonical_match_ids
    )
    unique_requested_match_ids = set(requested_match_ids)
    if len(unique_requested_match_ids) != len(requested_match_ids):
        msg = "split manifest memberships must be unique across train, validation, and test"
        raise ValueError(msg)

    missing_match_ids = [
        canonical_match_id
        for canonical_match_id in requested_match_ids
        if canonical_match_id not in known_match_ids
    ]
    if missing_match_ids:
        missing_display = ", ".join(missing_match_ids)
        msg = f"split manifest references unknown canonical_match_id values: {missing_display}"
        raise ValueError(msg)


def _infer_feature_groups(dataset: FrozenModelingDataset) -> dict[str, list[str]]:
    numeric_columns: list[str] = []
    categorical_columns: list[str] = []

    for feature_column in dataset.feature_columns:
        exemplar = _first_non_null_feature_value(dataset=dataset, feature_column=feature_column)
        if isinstance(exemplar, str | bool):
            categorical_columns.append(feature_column)
        else:
            numeric_columns.append(feature_column)

    return {
        "numeric": numeric_columns,
        "categorical": categorical_columns,
    }


def _first_non_null_feature_value(
    *,
    dataset: FrozenModelingDataset,
    feature_column: str,
) -> FeatureValue:
    for row in dataset.rows:
        value = row.feature_values[feature_column]
        if value is not None:
            return value
    return None


def _build_preprocessor(
    *,
    feature_groups: dict[str, list[str]],
    scale_numeric: bool,
) -> ColumnTransformer:
    numeric_steps: list[tuple[str, object]] = [
        ("imputer", SimpleImputer(strategy="median")),
    ]
    if scale_numeric:
        numeric_steps.append(("scaler", StandardScaler()))

    transformers: list[tuple[str, object, list[str]]] = []
    if feature_groups["numeric"]:
        transformers.append(
            (
                "numeric",
                Pipeline(steps=numeric_steps),
                feature_groups["numeric"],
            )
        )
    if feature_groups["categorical"]:
        transformers.append(
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                feature_groups["categorical"],
            )
        )

    return ColumnTransformer(transformers=transformers)


def _build_split_frame_and_target(
    *,
    dataset: FrozenModelingDataset,
    canonical_match_ids: list[str],
) -> tuple[pd.DataFrame, list[int]]:
    rows_by_match_id = {
        row.canonical_match_id: row
        for row in dataset.rows
    }
    selected_rows = [
        rows_by_match_id[canonical_match_id]
        for canonical_match_id in canonical_match_ids
    ]
    frame = pd.DataFrame.from_records(
        [
            {
                feature_column: row.feature_values[feature_column]
                for feature_column in dataset.feature_columns
            }
            for row in selected_rows
        ],
        columns=dataset.feature_columns,
    )
    target = [row.target for row in selected_rows]
    return frame, target


def _predict_probabilities(estimator: Pipeline, feature_frame: pd.DataFrame) -> list[float]:
    positive_class_probabilities = estimator.predict_proba(feature_frame)[:, 1]
    return [float(probability) for probability in positive_class_probabilities]
