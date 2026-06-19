from __future__ import annotations

import json
import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from shutil import copy2
from typing import Any, cast

import joblib  # type: ignore[import-untyped]
from sklearn.pipeline import Pipeline
from xgboost import XGBClassifier

from tennisprediction.config import Settings
from tennisprediction.ingestion.manifests import sha256_file
from tennisprediction.modeling.reports import write_model_reports
from tennisprediction.modeling.schemas import (
    CalibratedModelResult,
    FeatureValue,
    FrozenSplitManifest,
    LoadedModelArtifactBundle,
    ModelArtifactManifest,
    ProbabilityMetrics,
    RawModelFitResult,
)
from tennisprediction.modeling.splits import load_split_manifest


def write_model_artifact_bundle(
    run_id: str,
    raw_fit_result: RawModelFitResult,
    calibrated_result: CalibratedModelResult,
    metrics_result: ProbabilityMetrics,
    split_manifest: FrozenSplitManifest,
    settings: Settings,
) -> Path:
    artifact_dir = settings.models_dir / "runs" / run_id
    artifact_dir.mkdir(parents=True, exist_ok=False)
    report_dir = write_model_reports(run_id, calibrated_result, metrics_result, settings)

    feature_columns_path = artifact_dir / "feature_columns.json"
    feature_columns_path.write_text(
        json.dumps(raw_fit_result.feature_columns, indent=2),
        encoding="utf-8",
    )

    split_manifest_path = artifact_dir / "split_manifest.json"
    split_manifest_path.write_text(
        split_manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )

    raw_model_file, preprocessor_file = _persist_raw_estimator(
        artifact_dir=artifact_dir,
        raw_fit_result=raw_fit_result,
    )
    calibrator_path = artifact_dir / "calibrator.joblib"
    joblib.dump(calibrated_result.calibrator, calibrator_path)

    manifest = ModelArtifactManifest(
        run_id=run_id,
        model_name=raw_fit_result.model_name,
        model_family=raw_fit_result.model_family,
        source_repo=split_manifest.source_repo,
        source_commit_sha=split_manifest.source_commit_sha,
        source_version_label=_optional_str(raw_fit_result.fit_metadata.get("source_version_label")),
        feature_version=split_manifest.feature_version,
        split_manifest_id=split_manifest.split_id,
        split_boundaries={
            "train_end_date": split_manifest.train_end_date,
            "validation_end_date": split_manifest.validation_end_date,
            "test_end_date": split_manifest.test_end_date,
        },
        model_params=raw_fit_result.model_params,
        calibrator_metadata=_calibrator_metadata(calibrated_result),
        metrics_provenance=_metrics_provenance(metrics_result),
        dependency_versions=_dependency_versions(raw_fit_result.model_family),
        feature_columns_file=feature_columns_path.name,
        split_manifest_file=split_manifest_path.name,
        raw_model_file=raw_model_file.name,
        raw_model_sha256=sha256_file(raw_model_file),
        preprocessor_file=preprocessor_file.name if preprocessor_file is not None else None,
        calibrator_file=calibrator_path.name,
        calibrator_sha256=sha256_file(calibrator_path),
        report_files={
            "metrics": str(_repo_relative(report_dir / "metrics.json")),
            "calibration_curve": str(_repo_relative(report_dir / "calibration_curve.csv")),
            "calibration_bins": str(_repo_relative(report_dir / "calibration_bins.csv")),
            "segment_diagnostics": str(_repo_relative(report_dir / "segment_diagnostics.csv")),
            "test_predictions": str(_repo_relative(report_dir / "test_predictions.parquet")),
        },
    )
    (artifact_dir / "manifest.json").write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return artifact_dir


def load_model_artifact_bundle(
    path: str | Path,
    *,
    expected_feature_version: str,
    expected_split_manifest_id: str,
) -> LoadedModelArtifactBundle:
    artifact_dir = Settings._resolve_repo_path(Path(path))
    if not artifact_dir.exists():
        raise FileNotFoundError(artifact_dir)
    if not artifact_dir.is_dir():
        msg = "artifact bundle path must be a directory"
        raise ValueError(msg)

    manifest_path = artifact_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = ModelArtifactManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    _validate_manifest(
        manifest,
        expected_feature_version=expected_feature_version,
        expected_split_manifest_id=expected_split_manifest_id,
    )

    feature_columns_path = artifact_dir / manifest.feature_columns_file
    split_manifest_path = artifact_dir / manifest.split_manifest_file
    raw_model_path = artifact_dir / manifest.raw_model_file
    calibrator_path = artifact_dir / manifest.calibrator_file
    preprocessor_path = (
        artifact_dir / manifest.preprocessor_file
        if manifest.preprocessor_file is not None
        else None
    )
    required_paths = [
        feature_columns_path,
        split_manifest_path,
        raw_model_path,
        calibrator_path,
    ]
    if preprocessor_path is not None:
        required_paths.append(preprocessor_path)
    required_paths.extend(
        Settings._resolve_repo_path(Path(relative_path))
        for relative_path in manifest.report_files.values()
    )
    for required_path in required_paths:
        if not required_path.is_file():
            raise FileNotFoundError(required_path)

    if sha256_file(raw_model_path) != manifest.raw_model_sha256:
        msg = "raw model checksum mismatch"
        raise ValueError(msg)
    if sha256_file(calibrator_path) != manifest.calibrator_sha256:
        msg = "calibrator checksum mismatch"
        raise ValueError(msg)

    feature_columns = cast(
        list[str],
        json.loads(feature_columns_path.read_text(encoding="utf-8")),
    )
    split_manifest = load_split_manifest(split_manifest_path)
    calibrator = joblib.load(calibrator_path)
    raw_estimator = _load_raw_estimator(
        raw_model_path=raw_model_path,
        preprocessor_path=preprocessor_path,
        model_family=manifest.model_family,
    )

    return LoadedModelArtifactBundle(
        artifact_dir=artifact_dir,
        manifest=manifest,
        feature_columns=feature_columns,
        split_manifest=split_manifest,
        raw_estimator=raw_estimator,
        calibrator=calibrator,
    )


def _persist_raw_estimator(
    *,
    artifact_dir: Path,
    raw_fit_result: RawModelFitResult,
) -> tuple[Path, Path | None]:
    if raw_fit_result.raw_model_artifact_path is not None:
        source_path = Path(raw_fit_result.raw_model_artifact_path)
        destination_path = artifact_dir / source_path.name
        copy2(source_path, destination_path)
        return destination_path, None

    if raw_fit_result.model_family == "xgboost":
        trained_pipeline = _require_pipeline(raw_fit_result.trained_estimator)
        preprocessor_path = artifact_dir / "preprocessor.joblib"
        joblib.dump(trained_pipeline.named_steps["preprocessor"], preprocessor_path)

        raw_model_path = artifact_dir / "raw_model.ubj"
        classifier = trained_pipeline.named_steps["classifier"]
        if not isinstance(classifier, XGBClassifier):
            msg = "xgboost raw estimator must expose an XGBClassifier classifier step"
            raise TypeError(msg)
        classifier.save_model(raw_model_path)
        return raw_model_path, preprocessor_path

    raw_model_path = artifact_dir / "raw_model.joblib"
    joblib.dump(raw_fit_result.trained_estimator, raw_model_path)
    return raw_model_path, None


def _load_raw_estimator(
    *,
    raw_model_path: Path,
    preprocessor_path: Path | None,
    model_family: str,
) -> Any:
    if model_family == "xgboost":
        if preprocessor_path is None:
            msg = "xgboost artifacts require a preprocessor sidecar"
            raise ValueError(msg)
        preprocessor = joblib.load(preprocessor_path)
        classifier = XGBClassifier()
        classifier.load_model(raw_model_path)
        return Pipeline(
            steps=[
                ("preprocessor", preprocessor),
                ("classifier", classifier),
            ]
        )

    return joblib.load(raw_model_path)


def _validate_manifest(
    manifest: ModelArtifactManifest,
    *,
    expected_feature_version: str,
    expected_split_manifest_id: str,
) -> None:
    if manifest.feature_version != expected_feature_version:
        msg = "manifest feature_version does not match expected feature_version"
        raise ValueError(msg)
    if manifest.split_manifest_id != expected_split_manifest_id:
        msg = "manifest split manifest id does not match expected split manifest id"
        raise ValueError(msg)
    if len(manifest.source_commit_sha) < 7:
        msg = "manifest source_commit_sha must be a pinned source commit SHA"
        raise ValueError(msg)

    current_versions = _dependency_versions(manifest.model_family)
    if manifest.dependency_versions != current_versions:
        msg = "saved dependency metadata does not match the current runtime"
        raise ValueError(msg)


def _calibrator_metadata(calibrated_result: CalibratedModelResult) -> dict[str, FeatureValue]:
    return {
        "method": calibrated_result.calibration_method,
        "validation_row_count": calibrated_result.validation_row_count,
        "test_row_count": calibrated_result.test_row_count,
        "validation_membership_sha256": calibrated_result.validation_membership_sha256,
        "test_membership_sha256": calibrated_result.test_membership_sha256,
        "fit_row_count": _optional_int(
            getattr(calibrated_result.calibrator, "fit_row_count", None)
        ),
    }


def _metrics_provenance(metrics_result: ProbabilityMetrics) -> dict[str, FeatureValue]:
    return {
        "model_family": metrics_result.model_family,
        "calibration_curve_artifact": metrics_result.calibration_curve_artifact,
        "calibration_bin_count": len(metrics_result.calibration_bins),
        "calibration_curve_point_count": len(metrics_result.calibration_curve),
    }


def _dependency_versions(model_family: str) -> dict[str, str]:
    dependency_names = ["joblib", "pandas", "scikit-learn"]
    if model_family == "xgboost":
        dependency_names.append("xgboost")

    versions = {"python": sys.version.split()[0]}
    for dependency_name in dependency_names:
        try:
            versions[dependency_name] = version(dependency_name)
        except PackageNotFoundError as exc:
            msg = f"missing required dependency: {dependency_name}"
            raise ValueError(msg) from exc
    return versions


def _repo_relative(path: Path) -> Path:
    return path.relative_to(Settings().repo_root)


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str | float):
        return int(value)

    msg = "expected an int-compatible value"
    raise TypeError(msg)


def _require_pipeline(estimator: object) -> Pipeline:
    if not isinstance(estimator, Pipeline):
        msg = "trained estimator must be a Pipeline"
        raise TypeError(msg)
    return estimator
