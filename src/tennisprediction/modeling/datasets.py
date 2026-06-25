from __future__ import annotations

from pathlib import Path
from typing import cast

import duckdb

from tennisprediction.modeling.schemas import FeatureValue, FrozenModelingDataset, ModelingRow

LABEL_DEFINITION = "player_a_id == winner_canonical_player_id"
_NON_FEATURE_COLUMNS = {
    "feature_version",
    "canonical_match_id",
    "player_a_id",
    "player_b_id",
    "as_of_date",
    "player_a_side",
    "player_b_side",
    "target",
    "lineage_source_repo",
    "lineage_source_commit_sha",
    "lineage_source_file_path",
    "lineage_source_row_number",
    "lineage_source_snapshot_root",
}


def materialize_modeling_dataset(
    *,
    database_path: str | Path,
    feature_version: str,
) -> FrozenModelingDataset:
    connection = duckdb.connect(str(database_path))
    try:
        feature_columns = _feature_columns(connection)
        query = """
            select
                d.*,
                case
                    when d.player_a_id = m.winner_canonical_player_id then 1
                    else 0
                end as target
            from feature_differential_rows as d
            join canonical_matches as m using (canonical_match_id)
            where d.feature_version = ?
            order by
                d.as_of_date,
                d.lineage_source_file_path,
                d.lineage_source_row_number,
                d.canonical_match_id
        """
        cursor = connection.execute(query, [feature_version])
        column_names = [description[0] for description in cursor.description]
        rows = [
            _build_modeling_row(
                raw_row=dict(zip(column_names, values, strict=True)),
                feature_columns=feature_columns,
            )
            for values in cursor.fetchall()
        ]
    finally:
        connection.close()

    if not rows:
        msg = f"no persisted differential rows found for feature_version={feature_version}"
        raise ValueError(msg)

    return FrozenModelingDataset(
        feature_version=feature_version,
        label_definition=LABEL_DEFINITION,
        rows=rows,
        feature_columns=feature_columns,
    )


def _feature_columns(connection: duckdb.DuckDBPyConnection) -> list[str]:
    table_info = connection.execute("pragma table_info('feature_differential_rows')").fetchall()
    return [row[1] for row in table_info if row[1] not in _NON_FEATURE_COLUMNS]


def _build_modeling_row(
    *,
    raw_row: dict[str, object],
    feature_columns: list[str],
) -> ModelingRow:
    return ModelingRow(
        feature_version=_value_as_str(raw_row, "feature_version"),
        canonical_match_id=_value_as_str(raw_row, "canonical_match_id"),
        player_a_id=_value_as_str(raw_row, "player_a_id"),
        player_b_id=_value_as_str(raw_row, "player_b_id"),
        as_of_date=_value_as_str(raw_row, "as_of_date"),
        target=_value_as_int(raw_row, "target"),
        lineage_source_repo=_value_as_str(raw_row, "lineage_source_repo"),
        lineage_source_commit_sha=_value_as_str(raw_row, "lineage_source_commit_sha"),
        lineage_source_file_path=_value_as_str(raw_row, "lineage_source_file_path"),
        lineage_source_row_number=_value_as_int(raw_row, "lineage_source_row_number"),
        lineage_source_snapshot_root=_value_as_str(raw_row, "lineage_source_snapshot_root"),
        feature_values={
            column_name: cast(FeatureValue, raw_row[column_name]) for column_name in feature_columns
        },
    )


def _value_as_str(raw_row: dict[str, object], column_name: str) -> str:
    value = raw_row[column_name]
    if not isinstance(value, str):
        msg = f"{column_name} must be a string"
        raise TypeError(msg)
    return value


def _value_as_int(raw_row: dict[str, object], column_name: str) -> int:
    value = raw_row[column_name]
    if not isinstance(value, int):
        msg = f"{column_name} must be an integer"
        raise TypeError(msg)
    return value
