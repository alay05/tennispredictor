from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import pandas as pd

from tennisprediction.backtesting.schemas import ReplayPredictionRow, ReplayRunResult
from tennisprediction.config import Settings
from tennisprediction.modeling.datasets import materialize_modeling_dataset
from tennisprediction.modeling.registry import load_model_artifact_bundle


def replay_model_predictions(
    artifact_dir: str | Path,
    database_path: str | Path,
    *,
    expected_feature_version: str,
    expected_split_manifest_id: str,
) -> ReplayRunResult:
    bundle = load_model_artifact_bundle(
        artifact_dir,
        expected_feature_version=expected_feature_version,
        expected_split_manifest_id=expected_split_manifest_id,
    )
    dataset = materialize_modeling_dataset(
        database_path=database_path,
        feature_version=expected_feature_version,
    )

    row_lookup = {row.canonical_match_id: row for row in dataset.rows}
    ordered_rows = [
        row_lookup[canonical_match_id]
        for canonical_match_id in bundle.split_manifest.test.canonical_match_ids
    ]

    feature_frame = _build_feature_frame(
        ordered_rows=ordered_rows,
        feature_columns=bundle.feature_columns,
    )
    raw_probabilities = _positive_class_probabilities(
        bundle.raw_estimator.predict_proba(feature_frame)
    )
    calibrated_probabilities = _positive_class_probabilities(
        bundle.calibrator.predict_proba(feature_frame)
    )

    replay_rows = [
        ReplayPredictionRow(
            artifact_run_id=bundle.manifest.run_id,
            model_name=bundle.manifest.model_name,
            model_family=bundle.manifest.model_family,
            canonical_match_id=row.canonical_match_id,
            player_a_id=row.player_a_id,
            player_b_id=row.player_b_id,
            as_of_date=row.as_of_date,
            surface=str(row.feature_values["surface"]),
            tourney_level=str(row.feature_values["tourney_level"]),
            round_name=str(row.feature_values["round_name"]),
            best_of=_required_int(row.feature_values["best_of"]),
            player_a_rank=_optional_int(row.feature_values["player_a_rank"]),
            player_b_rank=_optional_int(row.feature_values["player_b_rank"]),
            rank_diff=_optional_int(row.feature_values["rank_diff"]),
            target=row.target,
            feature_version=row.feature_version,
            split_manifest_id=bundle.manifest.split_manifest_id,
            source_commit_sha=bundle.manifest.source_commit_sha,
            raw_probability=raw_probability,
            calibrated_probability=calibrated_probability,
            favored_side="A" if calibrated_probability >= 0.5 else "B",
            favored_probability=max(calibrated_probability, 1.0 - calibrated_probability),
        )
        for row, raw_probability, calibrated_probability in zip(
            ordered_rows,
            raw_probabilities,
            calibrated_probabilities,
            strict=True,
        )
    ]

    _validate_saved_predictions(bundle.manifest.run_id, replay_rows)

    return ReplayRunResult(
        artifact_run_id=bundle.manifest.run_id,
        artifact_dir=Path(bundle.artifact_dir),
        feature_version=bundle.manifest.feature_version,
        split_manifest_id=bundle.manifest.split_manifest_id,
        source_commit_sha=bundle.manifest.source_commit_sha,
        rows=replay_rows,
        parity_checked=_saved_predictions_exist(bundle.manifest.run_id),
    )


def _build_feature_frame(
    *,
    ordered_rows: list[Any],
    feature_columns: list[str],
) -> pd.DataFrame:
    records = [
        {feature_column: row.feature_values[feature_column] for feature_column in feature_columns}
        for row in ordered_rows
    ]
    return pd.DataFrame.from_records(records)


def _positive_class_probabilities(predictions: object) -> list[float]:
    prediction_rows = cast(Any, predictions)
    return [float(row[1]) for row in prediction_rows]


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    msg = "expected integer feature value"
    raise TypeError(msg)


def _required_int(value: object) -> int:
    optional_value = _optional_int(value)
    if optional_value is None:
        msg = "expected integer feature value"
        raise TypeError(msg)
    return optional_value


def _saved_predictions_exist(run_id: str) -> bool:
    settings = Settings()
    return (settings.reports_dir / "modeling" / run_id / "test_predictions.parquet").is_file()


def _validate_saved_predictions(run_id: str, replay_rows: list[ReplayPredictionRow]) -> None:
    settings = Settings()
    predictions_path = settings.reports_dir / "modeling" / run_id / "test_predictions.parquet"
    if not predictions_path.is_file():
        return

    saved_predictions = pd.read_parquet(predictions_path)
    if len(saved_predictions) != len(replay_rows):
        msg = "saved parity predictions do not match replay row count"
        raise ValueError(msg)

    replay_frame = pd.DataFrame.from_records([asdict(row) for row in replay_rows])
    shared_columns = [
        "canonical_match_id",
        "raw_probability",
        "calibrated_probability",
        "favored_side",
        "favored_probability",
    ]
    if not saved_predictions[shared_columns].equals(replay_frame[shared_columns]):
        msg = "saved parity predictions do not match regenerated replay rows"
        raise ValueError(msg)
