from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

import pandas as pd
import pytest

import tennisprediction.config as config_module
from tennisprediction.config import Settings
from tennisprediction.modeling.baselines import (
    fit_logistic_regression_baseline,
    fit_random_forest_baseline,
)
from tennisprediction.modeling.calibration import calibrate_model_probabilities
from tennisprediction.modeling.datasets import materialize_modeling_dataset
from tennisprediction.modeling.metrics import (
    build_segment_diagnostics,
    evaluate_probability_predictions,
)
from tennisprediction.modeling.reports import write_model_reports
from tennisprediction.modeling.schemas import (
    CalibratedPredictionRow,
    FrozenModelingDataset,
    FrozenSplitManifest,
    RawModelFitResult,
    SegmentDiagnosticRow,
)
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
def test_evaluate_probability_predictions_returns_scalar_metrics_bins_curve_and_ece(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_fit_builder: Callable[..., RawModelFitResult],
    expected_family: str,
) -> None:
    dataset, manifest_path, manifest = _build_dataset_and_manifest(tmp_path, monkeypatch)
    raw_fit_result = raw_fit_builder(dataset, manifest_path)
    calibrated_result = calibrate_model_probabilities(
        raw_fit_result,
        dataset,
        manifest_path,
        method="sigmoid",
    )
    y_true = _targets_for_ids(dataset, manifest.test.canonical_match_ids)

    metrics = evaluate_probability_predictions(
        y_true,
        calibrated_result.calibrated_test_probabilities,
    )

    assert metrics.model_family == expected_family
    assert 0.0 <= metrics.accuracy <= 1.0
    assert 0.0 <= metrics.roc_auc <= 1.0
    assert metrics.log_loss >= 0.0
    assert 0.0 <= metrics.brier_score <= 1.0
    assert metrics.expected_calibration_error >= 0.0
    assert len(metrics.calibration_bins) == 10
    assert [calibration_bin.bin_index for calibration_bin in metrics.calibration_bins] == list(
        range(10)
    )
    assert sum(calibration_bin.sample_count for calibration_bin in metrics.calibration_bins) == len(
        y_true
    )
    assert metrics.calibration_bins[0].lower_bound == pytest.approx(0.0)
    assert metrics.calibration_bins[-1].upper_bound == pytest.approx(1.0)
    assert metrics.calibration_curve_artifact == "uniform_10_bin_calibration_curve"
    assert len(metrics.calibration_curve) >= 1
    assert {curve_point.bin_index for curve_point in metrics.calibration_curve} <= set(range(10))
    for curve_point in metrics.calibration_curve:
        assert 0.0 <= curve_point.mean_predicted_probability <= 1.0
        assert 0.0 <= curve_point.empirical_positive_rate <= 1.0


def test_build_segment_diagnostics_groups_calibrated_predictions_into_required_segments() -> None:
    prediction_rows = [
        _prediction_row(
            canonical_match_id="match:surface:hard",
            as_of_date="20240103",
            surface="Hard",
            tourney_level="A",
            player_a_rank=8,
            player_b_rank=35,
            target=1,
            calibrated_probability=0.55,
        ),
        _prediction_row(
            canonical_match_id="match:surface:clay",
            as_of_date="20240210",
            surface="Clay",
            tourney_level="M",
            player_a_rank=19,
            player_b_rank=44,
            target=0,
            calibrated_probability=0.64,
        ),
        _prediction_row(
            canonical_match_id="match:surface:grass",
            as_of_date="20240318",
            surface="Grass",
            tourney_level="G",
            player_a_rank=32,
            player_b_rank=61,
            target=1,
            calibrated_probability=0.74,
        ),
        _prediction_row(
            canonical_match_id="match:ranking:51-100",
            as_of_date="20240426",
            surface="Hard",
            tourney_level="A",
            player_a_rank=78,
            player_b_rank=103,
            target=1,
            calibrated_probability=0.82,
        ),
        _prediction_row(
            canonical_match_id="match:ranking:101+",
            as_of_date="20240529",
            surface="Clay",
            tourney_level="M",
            player_a_rank=122,
            player_b_rank=145,
            target=0,
            calibrated_probability=0.91,
        ),
        _prediction_row(
            canonical_match_id="match:ranking:unranked",
            as_of_date="20240611",
            surface="Grass",
            tourney_level="A",
            player_a_rank=None,
            player_b_rank=None,
            target=1,
            calibrated_probability=0.58,
            favored_side="B",
            favored_probability=0.58,
        ),
    ]

    diagnostics = build_segment_diagnostics(prediction_rows)

    assert all(isinstance(row, SegmentDiagnosticRow) for row in diagnostics)
    assert _segment_values(diagnostics, "surface") == {"Hard", "Clay", "Grass"}
    assert _segment_values(diagnostics, "tourney_level") == {"A", "M", "G"}
    assert _segment_values(diagnostics, "time_period") == {"2024"}
    assert _segment_values(diagnostics, "ranking_band") == {
        "1-10",
        "11-25",
        "26-50",
        "51-100",
        "101+",
        "unranked",
    }
    assert _segment_values(diagnostics, "confidence_bucket") == {
        "[0.50,0.60)",
        "[0.60,0.70)",
        "[0.70,0.80)",
        "[0.80,0.90)",
        "[0.90,1.00]",
    }

    ranking_band_row = _find_segment_row(diagnostics, "ranking_band", "1-10")
    assert ranking_band_row.sample_count == 1
    assert ranking_band_row.win_rate == pytest.approx(1.0)
    assert ranking_band_row.mean_calibrated_probability == pytest.approx(0.55)

    confidence_row = _find_segment_row(diagnostics, "confidence_bucket", "[0.90,1.00]")
    assert confidence_row.sample_count == 1
    assert confidence_row.mean_favored_probability == pytest.approx(0.91)
    assert confidence_row.accuracy == pytest.approx(0.0)


@pytest.mark.parametrize(
    ("raw_fit_builder", "expected_family"),
    [
        (fit_logistic_regression_baseline, "logistic_regression"),
        (fit_random_forest_baseline, "random_forest"),
        (fit_xgboost_candidate, "xgboost"),
    ],
)
def test_write_model_reports_persists_curve_bins_segments_and_prediction_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    raw_fit_builder: Callable[..., RawModelFitResult],
    expected_family: str,
) -> None:
    dataset, manifest_path, manifest = _build_dataset_and_manifest(tmp_path, monkeypatch)
    raw_fit_result = raw_fit_builder(dataset, manifest_path)
    calibrated_result = calibrate_model_probabilities(
        raw_fit_result,
        dataset,
        manifest_path,
        method="sigmoid",
    )
    metrics = evaluate_probability_predictions(
        _targets_for_ids(dataset, manifest.test.canonical_match_ids),
        calibrated_result.calibrated_test_probabilities,
    )
    run_id = f"{expected_family}-report-run"
    settings = Settings(
        data_dir=tmp_path / "data",
        models_dir=tmp_path / "models",
        reports_dir=tmp_path / "reports",
        duckdb_path=tmp_path / "data" / "testing.duckdb",
    )

    report_dir = write_model_reports(run_id, calibrated_result, metrics, settings)

    calibration_curve_path = report_dir / "calibration_curve.csv"
    calibration_bins_path = report_dir / "calibration_bins.csv"
    segment_diagnostics_path = report_dir / "segment_diagnostics.csv"
    predictions_path = report_dir / "test_predictions.parquet"
    metrics_path = report_dir / "metrics.json"

    assert calibration_curve_path.is_file()
    assert calibration_bins_path.is_file()
    assert segment_diagnostics_path.is_file()
    assert predictions_path.is_file()
    assert metrics_path.is_file()

    calibration_curve = pd.read_csv(calibration_curve_path)
    assert list(calibration_curve.columns) == [
        "bin_index",
        "mean_predicted_probability",
        "empirical_positive_rate",
    ]
    assert len(calibration_curve) == len(metrics.calibration_curve)

    calibration_bins = pd.read_csv(calibration_bins_path)
    assert len(calibration_bins) == 10
    assert set(calibration_bins.columns) >= {
        "bin_index",
        "lower_bound",
        "upper_bound",
        "sample_count",
        "mean_predicted_probability",
        "empirical_positive_rate",
        "absolute_calibration_gap",
    }

    segment_diagnostics = pd.read_csv(segment_diagnostics_path)
    assert set(segment_diagnostics["segment_name"]) == {
        "surface",
        "tourney_level",
        "time_period",
        "ranking_band",
        "confidence_bucket",
    }

    predictions = pd.read_parquet(predictions_path)
    assert len(predictions) == len(calibrated_result.test_predictions)
    assert set(predictions.columns) >= {
        "model_name",
        "model_family",
        "canonical_match_id",
        "as_of_date",
        "surface",
        "tourney_level",
        "round_name",
        "best_of",
        "player_a_rank",
        "player_b_rank",
        "rank_diff",
        "target",
        "raw_probability",
        "calibrated_probability",
        "favored_side",
        "favored_probability",
    }
    assert set(predictions["model_family"]) == {expected_family}


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


def _targets_for_ids(dataset: FrozenModelingDataset, canonical_match_ids: list[str]) -> list[int]:
    row_lookup = {row.canonical_match_id: row for row in dataset.rows}
    return [row_lookup[canonical_match_id].target for canonical_match_id in canonical_match_ids]


def _prediction_row(
    *,
    canonical_match_id: str,
    as_of_date: str,
    surface: str,
    tourney_level: str,
    player_a_rank: int | None,
    player_b_rank: int | None,
    target: int,
    calibrated_probability: float,
    favored_side: str = "A",
    favored_probability: float | None = None,
) -> CalibratedPredictionRow:
    raw_probability = (
        calibrated_probability if favored_side == "A" else 1.0 - calibrated_probability
    )
    resolved_favored_probability = (
        favored_probability
        if favored_probability is not None
        else max(calibrated_probability, 1.0 - calibrated_probability)
    )
    return CalibratedPredictionRow(
        model_name="segment-diagnostic-model",
        model_family="logistic_regression",
        canonical_match_id=canonical_match_id,
        as_of_date=as_of_date,
        surface=surface,
        tourney_level=tourney_level,
        round_name="R32",
        best_of=3,
        player_a_rank=player_a_rank,
        player_b_rank=player_b_rank,
        rank_diff=None,
        target=target,
        raw_probability=raw_probability,
        calibrated_probability=calibrated_probability,
        favored_side=favored_side,
        favored_probability=resolved_favored_probability,
    )


def _segment_values(
    diagnostics: Iterable[SegmentDiagnosticRow],
    segment_name: str,
) -> set[str]:
    return {row.segment_value for row in diagnostics if row.segment_name == segment_name}


def _find_segment_row(
    diagnostics: Iterable[SegmentDiagnosticRow],
    segment_name: str,
    segment_value: str,
) -> SegmentDiagnosticRow:
    for row in diagnostics:
        if row.segment_name == segment_name and row.segment_value == segment_value:
            return row
    raise AssertionError(f"missing segment row for {segment_name}={segment_value}")
