from __future__ import annotations

from dataclasses import dataclass

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
    train_end_date: str
    validation_end_date: str
    test_end_date: str
    train: FrozenSplitWindow
    validation: FrozenSplitWindow
    test: FrozenSplitWindow

    model_config = ConfigDict(frozen=True)
