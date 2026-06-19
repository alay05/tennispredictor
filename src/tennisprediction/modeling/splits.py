from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import cast

from tennisprediction.config import Settings
from tennisprediction.modeling.schemas import (
    FrozenModelingDataset,
    FrozenSplitManifest,
    FrozenSplitWindow,
    ModelingRow,
)


@dataclass(frozen=True)
class SplitBoundaryConfig:
    train_end_date: str
    validation_end_date: str
    test_end_date: str


def freeze_chronological_splits(
    dataset: FrozenModelingDataset,
    boundary_config: SplitBoundaryConfig,
    settings: Settings,
) -> FrozenSplitManifest:
    _validate_boundary_order(boundary_config)

    train_rows = [row for row in dataset.rows if row.as_of_date <= boundary_config.train_end_date]
    validation_rows = [
        row
        for row in dataset.rows
        if boundary_config.train_end_date < row.as_of_date <= boundary_config.validation_end_date
    ]
    test_rows = [
        row
        for row in dataset.rows
        if boundary_config.validation_end_date < row.as_of_date <= boundary_config.test_end_date
    ]

    train_window = _build_window(
        rows=train_rows,
        expected_end_date=boundary_config.train_end_date,
        window_name="train",
    )
    validation_window = _build_window(
        rows=validation_rows,
        expected_end_date=boundary_config.validation_end_date,
        window_name="validation",
    )
    test_window = _build_window(
        rows=test_rows,
        expected_end_date=boundary_config.test_end_date,
        window_name="test",
    )

    if train_window.row_count + validation_window.row_count + test_window.row_count != len(
        dataset.rows
    ):
        msg = "split windows must partition the full ordered dataset"
        raise ValueError(msg)

    split_id = (
        f"{dataset.feature_version}-"
        f"{boundary_config.train_end_date}-"
        f"{boundary_config.validation_end_date}-"
        f"{boundary_config.test_end_date}"
    )
    manifest = FrozenSplitManifest(
        split_id=split_id,
        feature_version=dataset.feature_version,
        label_definition=dataset.label_definition,
        source_repo=_common_source_value(dataset=dataset, field_name="lineage_source_repo"),
        source_commit_sha=_common_source_value(
            dataset=dataset,
            field_name="lineage_source_commit_sha",
        ),
        source_snapshot_root=_common_source_value(
            dataset=dataset,
            field_name="lineage_source_snapshot_root",
        ),
        train_end_date=boundary_config.train_end_date,
        validation_end_date=boundary_config.validation_end_date,
        test_end_date=boundary_config.test_end_date,
        train=train_window,
        validation=validation_window,
        test=test_window,
    )

    split_dir = settings.models_dir / "splits"
    split_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = split_dir / f"{split_id}.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest


def load_split_manifest(path: str | Path) -> FrozenSplitManifest:
    manifest_path = Path(path)
    return FrozenSplitManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))


def _build_window(
    *,
    rows: list[ModelingRow],
    expected_end_date: str,
    window_name: str,
) -> FrozenSplitWindow:
    if not rows:
        msg = f"{window_name} window is empty"
        raise ValueError(msg)

    last_row = rows[-1]
    if last_row.as_of_date != expected_end_date:
        msg = f"{window_name} window is empty at boundary {expected_end_date}"
        raise ValueError(msg)

    canonical_match_ids = [row.canonical_match_id for row in rows]
    return FrozenSplitWindow(
        canonical_match_ids=canonical_match_ids,
        row_count=len(rows),
        first_as_of_date=rows[0].as_of_date,
        last_as_of_date=last_row.as_of_date,
        membership_sha256=_membership_sha256(canonical_match_ids),
    )


def _membership_sha256(canonical_match_ids: list[str]) -> str:
    digest = sha256()
    for canonical_match_id in canonical_match_ids:
        digest.update(canonical_match_id.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _validate_boundary_order(boundary_config: SplitBoundaryConfig) -> None:
    if not (
        boundary_config.train_end_date
        < boundary_config.validation_end_date
        < boundary_config.test_end_date
    ):
        msg = "split boundary dates must be strictly increasing"
        raise ValueError(msg)


def _common_source_value(
    *,
    dataset: FrozenModelingDataset,
    field_name: str,
) -> str:
    values = {getattr(row, field_name) for row in dataset.rows}
    if len(values) != 1:
        msg = f"dataset rows must share one {field_name} value"
        raise ValueError(msg)
    return cast(str, next(iter(values)))
