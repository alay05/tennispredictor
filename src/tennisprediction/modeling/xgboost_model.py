from __future__ import annotations

from math import ceil
from pathlib import Path

from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from tennisprediction.modeling.baselines import (
    _build_preprocessor,
    _build_split_frame_and_target,
    _infer_feature_groups,
    _predict_probabilities,
    _resolve_split_manifest,
    _validate_dataset_and_manifest,
)
from tennisprediction.modeling.schemas import (
    FeatureValue,
    FrozenModelingDataset,
    FrozenSplitManifest,
    RawModelFitResult,
    XGBoostTrainingConfig,
)


def fit_xgboost_candidate(
    dataset: FrozenModelingDataset,
    split_manifest: FrozenSplitManifest | str | Path,
    config: XGBoostTrainingConfig | None = None,
) -> RawModelFitResult:
    resolved_config = config or XGBoostTrainingConfig()
    manifest, manifest_path = _resolve_split_manifest(split_manifest)
    _validate_dataset_and_manifest(dataset=dataset, manifest=manifest)
    feature_groups = _infer_feature_groups(dataset)
    fit_ids, eval_ids = _split_train_memberships_for_early_stopping(
        manifest.train.canonical_match_ids
    )

    fit_frame, fit_target = _build_split_frame_and_target(
        dataset=dataset,
        canonical_match_ids=fit_ids,
    )
    eval_frame, eval_target = _build_split_frame_and_target(
        dataset=dataset,
        canonical_match_ids=eval_ids,
    )
    validation_frame, _ = _build_split_frame_and_target(
        dataset=dataset,
        canonical_match_ids=manifest.validation.canonical_match_ids,
    )
    test_frame, _ = _build_split_frame_and_target(
        dataset=dataset,
        canonical_match_ids=manifest.test.canonical_match_ids,
    )

    preprocessor = _build_preprocessor(feature_groups=feature_groups, scale_numeric=False)
    transformed_fit_frame = preprocessor.fit_transform(fit_frame, fit_target)
    transformed_eval_frame = preprocessor.transform(eval_frame)

    estimator = XGBClassifier(
        n_estimators=resolved_config.n_estimators,
        learning_rate=resolved_config.learning_rate,
        max_depth=resolved_config.max_depth,
        subsample=resolved_config.subsample,
        colsample_bytree=resolved_config.colsample_bytree,
        min_child_weight=resolved_config.min_child_weight,
        reg_lambda=resolved_config.reg_lambda,
        random_state=resolved_config.random_state,
        early_stopping_rounds=resolved_config.early_stopping_rounds,
        eval_metric="logloss",
    )
    estimator.fit(
        transformed_fit_frame,
        fit_target,
        eval_set=[(transformed_eval_frame, eval_target)],
        verbose=False,
    )
    trained_estimator = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", estimator),
        ]
    )

    return RawModelFitResult(
        model_name="xgboost_candidate",
        model_family="xgboost",
        feature_columns=list(dataset.feature_columns),
        split_manifest_path=manifest_path,
        train_row_count=manifest.train.row_count,
        validation_row_count=manifest.validation.row_count,
        test_row_count=manifest.test.row_count,
        validation_probabilities=_predict_probabilities(trained_estimator, validation_frame),
        test_probabilities=_predict_probabilities(trained_estimator, test_frame),
        model_params=_build_model_params(resolved_config),
        trained_estimator=trained_estimator,
        raw_model_artifact_path=None,
        fit_metadata={
            "numeric_imputer_strategy": "median",
            "categorical_imputer_strategy": "most_frequent",
            "categorical_encoder": "one_hot_ignore_unknown",
            "numeric_scaler": False,
            "split_id": manifest.split_id,
            "feature_version": dataset.feature_version,
            "label_definition": dataset.label_definition,
            "train_membership_sha256": manifest.train.membership_sha256,
            "validation_membership_sha256": manifest.validation.membership_sha256,
            "test_membership_sha256": manifest.test.membership_sha256,
            "fit_row_count": len(fit_ids),
            "eval_row_count": len(eval_ids),
            "fit_membership_sha256": _membership_sha256(fit_ids),
            "eval_membership_sha256": _membership_sha256(eval_ids),
            "best_iteration": _as_int(getattr(estimator, "best_iteration", None)),
            "best_score": _as_float(getattr(estimator, "best_score", None)),
        },
    )


def _build_model_params(config: XGBoostTrainingConfig) -> dict[str, FeatureValue]:
    return {
        "n_estimators": config.n_estimators,
        "learning_rate": config.learning_rate,
        "max_depth": config.max_depth,
        "subsample": config.subsample,
        "colsample_bytree": config.colsample_bytree,
        "min_child_weight": config.min_child_weight,
        "reg_lambda": config.reg_lambda,
        "random_state": config.random_state,
        "early_stopping_rounds": config.early_stopping_rounds,
    }


def _split_train_memberships_for_early_stopping(
    canonical_match_ids: list[str],
) -> tuple[list[str], list[str]]:
    if len(canonical_match_ids) < 3:
        msg = "xgboost candidate requires at least three train rows for fit/eval splitting"
        raise ValueError(msg)

    eval_count = max(1, ceil(len(canonical_match_ids) * 0.15))
    if eval_count >= len(canonical_match_ids):
        eval_count = len(canonical_match_ids) - 1

    fit_ids = canonical_match_ids[:-eval_count]
    eval_ids = canonical_match_ids[-eval_count:]
    return fit_ids, eval_ids


def _membership_sha256(canonical_match_ids: list[str]) -> str:
    from hashlib import sha256

    digest = sha256()
    for canonical_match_id in canonical_match_ids:
        digest.update(canonical_match_id.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _as_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str | float):
        return int(value)

    msg = "best_iteration must be convertible to int"
    raise TypeError(msg)


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, float):
        return value
    if isinstance(value, int | str):
        return float(value)

    msg = "best_score must be convertible to float"
    raise TypeError(msg)
