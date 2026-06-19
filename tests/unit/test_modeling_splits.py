from __future__ import annotations

from pathlib import Path

import pytest

import tennisprediction.config as config_module
from tennisprediction.config import Settings
from tennisprediction.modeling.datasets import materialize_modeling_dataset
from tennisprediction.modeling.splits import (
    SplitBoundaryConfig,
    freeze_chronological_splits,
    load_split_manifest,
)
from tests.unit.modeling_fixtures import build_synthetic_modeling_fixture, membership_sha256


def test_freeze_chronological_splits_persists_memberships_counts_and_hashes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    expected_train = fixture.ordered_match_ids[:14]
    expected_validation = fixture.ordered_match_ids[14:17]
    expected_test = fixture.ordered_match_ids[17:]

    assert manifest.train_end_date == fixture.resolved_train_end_date
    assert manifest.validation_end_date == fixture.resolved_validation_end_date
    assert manifest.test_end_date == fixture.resolved_test_end_date
    assert manifest.train.canonical_match_ids == expected_train
    assert manifest.validation.canonical_match_ids == expected_validation
    assert manifest.test.canonical_match_ids == expected_test
    assert manifest.train.row_count == 14
    assert manifest.validation.row_count == 3
    assert manifest.test.row_count == 3
    assert manifest.train.first_as_of_date == "20240101"
    assert manifest.train.last_as_of_date == fixture.resolved_train_end_date
    assert manifest.validation.first_as_of_date == "20240115"
    assert manifest.validation.last_as_of_date == fixture.resolved_validation_end_date
    assert manifest.test.first_as_of_date == "20240118"
    assert manifest.test.last_as_of_date == fixture.resolved_test_end_date
    assert manifest.train.membership_sha256 == membership_sha256(expected_train)
    assert manifest.validation.membership_sha256 == membership_sha256(expected_validation)
    assert manifest.test.membership_sha256 == membership_sha256(expected_test)

    manifest_path = settings.models_dir / "splits" / f"{manifest.split_id}.json"
    assert manifest_path.exists()
    assert load_split_manifest(manifest_path) == manifest


def test_freeze_chronological_splits_rejects_empty_or_non_increasing_windows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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

    with pytest.raises(ValueError, match="strictly increasing"):
        freeze_chronological_splits(
            dataset,
            SplitBoundaryConfig(
                train_end_date="20240115",
                validation_end_date="20240115",
                test_end_date="20240120",
            ),
            settings,
        )

    with pytest.raises(ValueError, match="empty"):
        freeze_chronological_splits(
            dataset,
            SplitBoundaryConfig(
                train_end_date="20240114",
                validation_end_date="20240117",
                test_end_date="20240125",
            ),
            settings,
        )
