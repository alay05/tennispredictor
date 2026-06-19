from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict

type FeatureValue = str | int | float | bool | None


@dataclass(frozen=True)
class ModelingRow:
    feature_version: str
    canonical_match_id: str
    player_a_id: str
    player_b_id: str
    as_of_date: str
    target: int
    lineage_source_repo: str
    lineage_source_commit_sha: str
    lineage_source_file_path: str
    lineage_source_row_number: int
    lineage_source_snapshot_root: str
    feature_values: dict[str, FeatureValue]


@dataclass(frozen=True)
class FrozenModelingDataset:
    feature_version: str
    label_definition: str
    rows: list[ModelingRow]
    feature_columns: list[str]


@dataclass(frozen=True)
class FrozenSplitWindow:
    canonical_match_ids: list[str]
    row_count: int
    first_as_of_date: str
    last_as_of_date: str
    membership_sha256: str


class FrozenSplitManifest(BaseModel):
    split_id: str
    feature_version: str
    label_definition: str
    source_repo: str
    source_commit_sha: str
    source_snapshot_root: str
    train_end_date: str
    validation_end_date: str
    test_end_date: str
    train: FrozenSplitWindow
    validation: FrozenSplitWindow
    test: FrozenSplitWindow

    model_config = ConfigDict(frozen=True)


@dataclass(frozen=True)
class RawModelFitResult:
    model_name: str
    model_family: str
    feature_columns: list[str]
    split_manifest_path: str
    train_row_count: int
    validation_row_count: int
    test_row_count: int
    validation_probabilities: list[float]
    test_probabilities: list[float]
    model_params: dict[str, FeatureValue]
    trained_estimator: Any
    raw_model_artifact_path: str | None
    fit_metadata: dict[str, FeatureValue]


@dataclass(frozen=True)
class XGBoostTrainingConfig:
    n_estimators: int = 400
    learning_rate: float = 0.05
    max_depth: int = 6
    subsample: float = 0.8
    colsample_bytree: float = 0.8
    min_child_weight: int = 1
    reg_lambda: float = 1.0
    random_state: int = 42
    early_stopping_rounds: int = 25


@dataclass(frozen=True)
class CalibratedPredictionRow:
    model_name: str
    model_family: str
    canonical_match_id: str
    as_of_date: str
    surface: str
    tourney_level: str
    round_name: str
    best_of: int
    player_a_rank: int | None
    player_b_rank: int | None
    rank_diff: int | None
    target: int
    raw_probability: float
    calibrated_probability: float
    favored_side: str
    favored_probability: float


@dataclass(frozen=True)
class CalibratedModelResult:
    model_name: str
    model_family: str
    split_manifest_path: str
    calibration_method: str
    calibrator: Any
    validation_row_count: int
    test_row_count: int
    validation_membership_sha256: str
    test_membership_sha256: str
    calibrated_validation_probabilities: list[float]
    calibrated_test_probabilities: list[float]
    validation_predictions: list[CalibratedPredictionRow]
    test_predictions: list[CalibratedPredictionRow]


@dataclass(frozen=True)
class CalibrationBin:
    bin_index: int
    lower_bound: float
    upper_bound: float
    sample_count: int
    mean_predicted_probability: float | None
    empirical_positive_rate: float | None
    absolute_calibration_gap: float | None


@dataclass(frozen=True)
class CalibrationCurvePoint:
    bin_index: int
    mean_predicted_probability: float
    empirical_positive_rate: float


@dataclass(frozen=True)
class ProbabilityMetrics:
    model_family: str
    accuracy: float
    roc_auc: float
    log_loss: float
    brier_score: float
    expected_calibration_error: float
    calibration_bins: list[CalibrationBin]
    calibration_curve: list[CalibrationCurvePoint]
    calibration_curve_artifact: str


@dataclass(frozen=True)
class SegmentDiagnosticRow:
    segment_name: str
    segment_value: str
    sample_count: int
    win_rate: float
    accuracy: float
    mean_calibrated_probability: float
    mean_favored_probability: float


class ModelArtifactManifest(BaseModel):
    run_id: str
    model_name: str
    model_family: str
    source_repo: str
    source_commit_sha: str
    source_version_label: str | None
    feature_version: str
    split_manifest_id: str
    split_boundaries: dict[str, str]
    model_params: dict[str, FeatureValue]
    calibrator_metadata: dict[str, FeatureValue]
    metrics_provenance: dict[str, FeatureValue]
    dependency_versions: dict[str, str]
    feature_columns_file: str
    split_manifest_file: str
    raw_model_file: str
    raw_model_sha256: str
    preprocessor_file: str | None = None
    calibrator_file: str
    calibrator_sha256: str
    report_files: dict[str, str]

    model_config = ConfigDict(frozen=True)


@dataclass(frozen=True)
class LoadedModelArtifactBundle:
    artifact_dir: Path
    manifest: ModelArtifactManifest
    feature_columns: list[str]
    split_manifest: FrozenSplitManifest
    raw_estimator: Any
    calibrator: Any
