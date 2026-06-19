from __future__ import annotations

from sklearn.calibration import calibration_curve
from sklearn.metrics import accuracy_score, brier_score_loss, log_loss, roc_auc_score

from tennisprediction.modeling.schemas import (
    CalibrationBin,
    CalibrationCurvePoint,
    ProbabilityMetrics,
)


def evaluate_probability_predictions(
    y_true: list[int],
    probabilities: list[float],
) -> ProbabilityMetrics:
    calibration_bins = _build_uniform_calibration_bins(y_true=y_true, probabilities=probabilities)
    calibration_curve_points = _build_calibration_curve_points(
        y_true=y_true,
        probabilities=probabilities,
        calibration_bins=calibration_bins,
    )
    ece = _expected_calibration_error(calibration_bins)

    return ProbabilityMetrics(
        model_family=str(getattr(probabilities, "model_family", "unknown")),
        accuracy=float(accuracy_score(y_true, _predicted_labels(probabilities))),
        roc_auc=float(roc_auc_score(y_true, probabilities)),
        log_loss=float(log_loss(y_true, probabilities)),
        brier_score=float(brier_score_loss(y_true, probabilities)),
        expected_calibration_error=ece,
        calibration_bins=calibration_bins,
        calibration_curve=calibration_curve_points,
        calibration_curve_artifact="uniform_10_bin_calibration_curve",
    )


def _predicted_labels(probabilities: list[float]) -> list[int]:
    return [1 if probability >= 0.5 else 0 for probability in probabilities]


def _build_uniform_calibration_bins(
    *,
    y_true: list[int],
    probabilities: list[float],
) -> list[CalibrationBin]:
    calibration_bins: list[CalibrationBin] = []

    for bin_index in range(10):
        lower_bound = bin_index / 10
        upper_bound = (bin_index + 1) / 10
        if bin_index == 9:
            bucket = [
                (target, probability)
                for target, probability in zip(y_true, probabilities, strict=True)
                if lower_bound <= probability <= upper_bound
            ]
        else:
            bucket = [
                (target, probability)
                for target, probability in zip(y_true, probabilities, strict=True)
                if lower_bound <= probability < upper_bound
            ]

        if bucket:
            sample_count = len(bucket)
            mean_predicted_probability = (
                sum(probability for _, probability in bucket) / sample_count
            )
            empirical_positive_rate = sum(target for target, _ in bucket) / sample_count
            absolute_calibration_gap = abs(empirical_positive_rate - mean_predicted_probability)
        else:
            sample_count = 0
            mean_predicted_probability = None
            empirical_positive_rate = None
            absolute_calibration_gap = None

        calibration_bins.append(
            CalibrationBin(
                bin_index=bin_index,
                lower_bound=float(lower_bound),
                upper_bound=float(upper_bound),
                sample_count=sample_count,
                mean_predicted_probability=mean_predicted_probability,
                empirical_positive_rate=empirical_positive_rate,
                absolute_calibration_gap=absolute_calibration_gap,
            )
        )

    return calibration_bins


def _build_calibration_curve_points(
    *,
    y_true: list[int],
    probabilities: list[float],
    calibration_bins: list[CalibrationBin],
) -> list[CalibrationCurvePoint]:
    prob_true, prob_pred = calibration_curve(
        y_true,
        probabilities,
        n_bins=10,
        strategy="uniform",
    )
    non_empty_bins = [
        calibration_bin
        for calibration_bin in calibration_bins
        if calibration_bin.sample_count > 0
    ]

    return [
        CalibrationCurvePoint(
            bin_index=calibration_bin.bin_index,
            mean_predicted_probability=float(predicted_probability),
            empirical_positive_rate=float(true_probability),
        )
        for calibration_bin, true_probability, predicted_probability in zip(
            non_empty_bins,
            prob_true,
            prob_pred,
            strict=True,
        )
    ]


def _expected_calibration_error(calibration_bins: list[CalibrationBin]) -> float:
    total_samples = sum(calibration_bin.sample_count for calibration_bin in calibration_bins)
    if total_samples == 0:
        return 0.0

    return float(
        sum(
            (calibration_bin.sample_count / total_samples)
            * (calibration_bin.absolute_calibration_gap or 0.0)
            for calibration_bin in calibration_bins
        )
    )
