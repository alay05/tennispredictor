from __future__ import annotations

from collections.abc import Mapping, Sized
from pathlib import Path
from typing import cast

import numpy as np
from sklearn.calibration import _SigmoidCalibration
from sklearn.frozen import FrozenEstimator
from sklearn.isotonic import IsotonicRegression

from tennisprediction.modeling.baselines import (
    _build_split_frame_and_target,
    _resolve_split_manifest,
    _validate_dataset_and_manifest,
)
from tennisprediction.modeling.schemas import (
    CalibratedModelResult,
    CalibratedPredictionRow,
    FrozenModelingDataset,
    FrozenSplitManifest,
    RawModelFitResult,
)


def calibrate_model_probabilities(
    raw_fit_result: RawModelFitResult,
    dataset: FrozenModelingDataset,
    split_manifest: FrozenSplitManifest | str | Path,
    method: str = "sigmoid",
) -> CalibratedModelResult:
    manifest, manifest_path = _resolve_split_manifest(split_manifest)
    _validate_dataset_and_manifest(dataset=dataset, manifest=manifest)

    validation_frame, validation_target = _build_split_frame_and_target(
        dataset=dataset,
        canonical_match_ids=manifest.validation.canonical_match_ids,
    )
    test_frame, test_target = _build_split_frame_and_target(
        dataset=dataset,
        canonical_match_ids=manifest.test.canonical_match_ids,
    )

    calibrator = ValidationOnlyCalibrator(
        estimator=raw_fit_result.trained_estimator,
        method=method,
    )
    calibrator.fit(validation_frame, validation_target)

    calibrated_validation_probabilities = ProbabilityList(
        _positive_class_probabilities(calibrator.predict_proba(validation_frame)),
        model_family=raw_fit_result.model_family,
    )
    calibrated_test_probabilities = ProbabilityList(
        _positive_class_probabilities(calibrator.predict_proba(test_frame)),
        model_family=raw_fit_result.model_family,
    )

    return CalibratedModelResult(
        model_name=raw_fit_result.model_name,
        model_family=raw_fit_result.model_family,
        split_manifest_path=manifest_path,
        calibration_method=method,
        calibrator=calibrator,
        validation_row_count=manifest.validation.row_count,
        test_row_count=manifest.test.row_count,
        validation_membership_sha256=manifest.validation.membership_sha256,
        test_membership_sha256=manifest.test.membership_sha256,
        calibrated_validation_probabilities=calibrated_validation_probabilities,
        calibrated_test_probabilities=calibrated_test_probabilities,
        validation_predictions=_build_prediction_rows(
            dataset=dataset,
            canonical_match_ids=manifest.validation.canonical_match_ids,
            targets=validation_target,
            raw_probabilities=raw_fit_result.validation_probabilities,
            calibrated_probabilities=calibrated_validation_probabilities,
            raw_fit_result=raw_fit_result,
        ),
        test_predictions=_build_prediction_rows(
            dataset=dataset,
            canonical_match_ids=manifest.test.canonical_match_ids,
            targets=test_target,
            raw_probabilities=raw_fit_result.test_probabilities,
            calibrated_probabilities=calibrated_test_probabilities,
            raw_fit_result=raw_fit_result,
        ),
    )


class ProbabilityList(list[float]):
    def __init__(self, values: list[float], *, model_family: str) -> None:
        super().__init__(values)
        self.model_family = model_family


class ValidationOnlyCalibrator:
    def __init__(self, *, estimator: object, method: str) -> None:
        self.frozen_estimator = FrozenEstimator(estimator)
        self.method = method
        self.fit_row_count = 0
        self.predict_row_counts: list[int] = []
        self._calibrator_model: _SigmoidCalibration | IsotonicRegression | None = None

    def fit(self, X: object, y: list[int]) -> ValidationOnlyCalibrator:
        raw_scores = _raw_scores(self.frozen_estimator, X)
        if self.method == "sigmoid":
            calibrator_model = _SigmoidCalibration()
        elif self.method == "isotonic":
            calibrator_model = IsotonicRegression(out_of_bounds="clip")
        else:
            msg = f"unsupported calibration method: {self.method}"
            raise ValueError(msg)

        calibrator_model.fit(raw_scores, y)
        self.fit_row_count = len(y)
        self._calibrator_model = calibrator_model
        return self

    def predict_proba(self, X: object) -> np.ndarray:
        if self._calibrator_model is None:
            msg = "calibrator must be fitted before prediction"
            raise ValueError(msg)

        self.predict_row_counts.append(_row_count(X))
        calibrated_probabilities = np.clip(
            np.asarray(self._calibrator_model.predict(_raw_scores(self.frozen_estimator, X))),
            0.0,
            1.0,
        )
        return np.column_stack((1.0 - calibrated_probabilities, calibrated_probabilities))


def _positive_class_probabilities(predictions: object) -> list[float]:
    prediction_array = cast(np.ndarray, predictions)
    return [float(probability) for probability in prediction_array[:, 1]]


def _raw_scores(estimator: FrozenEstimator, X: object) -> np.ndarray:
    if hasattr(estimator, "decision_function"):
        return np.asarray(estimator.decision_function(X), dtype=float)
    probabilities = np.asarray(estimator.predict_proba(X), dtype=float)
    return probabilities[:, 1]


def _build_prediction_rows(
    *,
    dataset: FrozenModelingDataset,
    canonical_match_ids: list[str],
    targets: list[int],
    raw_probabilities: list[float],
    calibrated_probabilities: list[float],
    raw_fit_result: RawModelFitResult,
) -> list[CalibratedPredictionRow]:
    row_lookup = {row.canonical_match_id: row for row in dataset.rows}
    prediction_rows: list[CalibratedPredictionRow] = []

    for canonical_match_id, target, raw_probability, calibrated_probability in zip(
        canonical_match_ids,
        targets,
        raw_probabilities,
        calibrated_probabilities,
        strict=True,
    ):
        row = row_lookup[canonical_match_id]
        favored_side = "A" if calibrated_probability >= 0.5 else "B"
        favored_probability = max(calibrated_probability, 1.0 - calibrated_probability)
        prediction_rows.append(
            CalibratedPredictionRow(
                model_name=raw_fit_result.model_name,
                model_family=raw_fit_result.model_family,
                canonical_match_id=canonical_match_id,
                as_of_date=row.as_of_date,
                surface=_required_str_feature(row.feature_values, "surface"),
                tourney_level=_required_str_feature(row.feature_values, "tourney_level"),
                round_name=_required_str_feature(row.feature_values, "round_name"),
                best_of=_required_int_feature(row.feature_values, "best_of"),
                player_a_rank=_optional_int_feature(row.feature_values, "player_a_rank"),
                player_b_rank=_optional_int_feature(row.feature_values, "player_b_rank"),
                rank_diff=_optional_int_feature(row.feature_values, "rank_diff"),
                target=target,
                raw_probability=float(raw_probability),
                calibrated_probability=float(calibrated_probability),
                favored_side=favored_side,
                favored_probability=float(favored_probability),
            )
        )

    return prediction_rows


def _required_int_feature(feature_values: Mapping[str, object], feature_name: str) -> int:
    value = feature_values[feature_name]
    if not isinstance(value, int):
        msg = f"{feature_name} must be an integer feature"
        raise TypeError(msg)
    return value


def _optional_int_feature(feature_values: Mapping[str, object], feature_name: str) -> int | None:
    value = feature_values[feature_name]
    if value is None:
        return None
    if not isinstance(value, int):
        msg = f"{feature_name} must be an integer feature"
        raise TypeError(msg)
    return value


def _required_str_feature(feature_values: Mapping[str, object], feature_name: str) -> str:
    value = feature_values[feature_name]
    if not isinstance(value, str):
        msg = f"{feature_name} must be a string feature"
        raise TypeError(msg)
    return value


def _row_count(value: object) -> int:
    sized_value = cast(Sized, value)
    return len(sized_value)
