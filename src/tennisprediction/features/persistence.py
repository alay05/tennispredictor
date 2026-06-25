from __future__ import annotations

from pathlib import Path
from typing import Any

import duckdb

from tennisprediction.features.schemas import FeatureBuildResult, PlayerFeatureSnapshot
from tennisprediction.storage.duckdb import _flatten, _replace_table

_SNAPSHOT_BASE_COLUMNS = {
    "feature_version",
    "canonical_match_id",
    "player_a_id",
    "player_b_id",
    "as_of_date",
    "surface",
    "tourney_level",
    "round_name",
    "best_of",
    "side",
    "lineage_source_repo",
    "lineage_source_commit_sha",
    "lineage_source_file_path",
    "lineage_source_row_number",
    "lineage_source_snapshot_root",
}


def _canonical_pair_key(player_one_id: str, player_two_id: str) -> str:
    if player_one_id <= player_two_id:
        return f"{player_one_id}::{player_two_id}"
    return f"{player_two_id}::{player_one_id}"


def _duckdb_type(*, column_name: str, value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "double"
    if value is None:
        if column_name.endswith(("_missing", "_low_sample")):
            return "boolean"
        if (
            "count" in column_name
            or "points" in column_name
            or "rank" in column_name
            or "days" in column_name
            or "exposure" in column_name
            or "row_number" in column_name
            or column_name in {"best_of", "ranking_change"}
        ):
            return "integer"
        if "rate" in column_name or "elo" in column_name or column_name.endswith("_diff"):
            return "double"
    return "varchar"


def _ddl_for_rows(
    *,
    table_name: str,
    rows: list[dict[str, Any]],
) -> str:
    if not rows:
        msg = f"{table_name} cannot be created from an empty feature build"
        raise ValueError(msg)

    columns = [
        f"{column_name} {_duckdb_type(column_name=column_name, value=value)}"
        for column_name, value in rows[0].items()
    ]
    column_block = ",\n                    ".join(columns)
    return f"""
                create table {table_name} (
                    {column_block}
                )
            """


def _snapshot_lookup(
    player_snapshots: list[PlayerFeatureSnapshot],
) -> dict[tuple[str, str], PlayerFeatureSnapshot]:
    return {(snapshot.canonical_match_id, snapshot.side): snapshot for snapshot in player_snapshots}


def _audit_snapshot_lookup(
    player_snapshots: list[PlayerFeatureSnapshot],
) -> dict[tuple[str, str], PlayerFeatureSnapshot]:
    return {
        (snapshot.canonical_match_id, snapshot.canonical_player_id): snapshot
        for snapshot in player_snapshots
    }


def _prefixed_snapshot_columns(
    *,
    prefix: str,
    snapshot: PlayerFeatureSnapshot,
) -> dict[str, Any]:
    flattened_snapshot = _flatten(snapshot)
    return {
        f"{prefix}_{column_name}": value
        for column_name, value in flattened_snapshot.items()
        if column_name not in _SNAPSHOT_BASE_COLUMNS
    }


def _build_differential_rows(feature_build: FeatureBuildResult) -> list[dict[str, Any]]:
    snapshots_by_match_and_side = _snapshot_lookup(feature_build.player_snapshots)
    persisted_rows: list[dict[str, Any]] = []
    for differential_row in feature_build.differential_rows:
        player_a_snapshot = snapshots_by_match_and_side[
            (differential_row.canonical_match_id, differential_row.player_a_side)
        ]
        player_b_snapshot = snapshots_by_match_and_side[
            (differential_row.canonical_match_id, differential_row.player_b_side)
        ]
        row = {
            "feature_version": differential_row.feature_version,
            "canonical_match_id": differential_row.canonical_match_id,
            "player_a_id": differential_row.player_a_id,
            "player_b_id": differential_row.player_b_id,
            "as_of_date": differential_row.as_of_date,
            "player_a_side": differential_row.player_a_side,
            "player_b_side": differential_row.player_b_side,
            "surface": differential_row.surface,
            "tourney_level": differential_row.tourney_level,
            "round_name": differential_row.round_name,
            "best_of": differential_row.best_of,
            **_prefixed_snapshot_columns(prefix="player_a", snapshot=player_a_snapshot),
            **_prefixed_snapshot_columns(prefix="player_b", snapshot=player_b_snapshot),
            "rank_diff": differential_row.rank_diff,
            "rank_points_diff": differential_row.rank_points_diff,
            "ranking_change_diff": differential_row.ranking_change_diff,
            "elo_diff": differential_row.elo_diff,
            "surface_elo_diff": differential_row.surface_elo_diff,
            "rest_days_diff": differential_row.rest_days_diff,
            "form_last_5_win_rate_diff": differential_row.form_last_5_win_rate_diff,
            "form_last_10_win_rate_diff": differential_row.form_last_10_win_rate_diff,
            "form_last_20_win_rate_diff": differential_row.form_last_20_win_rate_diff,
            "service_first_won_rate_diff": differential_row.service_first_won_rate_diff,
            "return_first_won_allowed_rate_diff": (
                differential_row.return_first_won_allowed_rate_diff
            ),
            "ace_rate_diff": differential_row.ace_rate_diff,
            "h2h_win_rate_diff": differential_row.h2h_win_rate_diff,
            "h2h_match_count": differential_row.h2h_match_count,
            "lineage_source_repo": differential_row.lineage.source_repo,
            "lineage_source_commit_sha": differential_row.lineage.source_commit_sha,
            "lineage_source_file_path": differential_row.lineage.source_file_path,
            "lineage_source_row_number": differential_row.lineage.source_row_number,
            "lineage_source_snapshot_root": differential_row.lineage.source_snapshot_root,
        }
        persisted_rows.append(row)
    return persisted_rows


def _build_audit_rows(feature_build: FeatureBuildResult) -> list[dict[str, Any]]:
    snapshots_by_match_and_player = _audit_snapshot_lookup(feature_build.player_snapshots)
    persisted_rows: list[dict[str, Any]] = []
    for audit_record in feature_build.state_audit_records:
        snapshot = snapshots_by_match_and_player[
            (audit_record.canonical_match_id, audit_record.canonical_player_id)
        ]
        persisted_rows.append(
            {
                "feature_version": snapshot.feature_version,
                "canonical_match_id": audit_record.canonical_match_id,
                "canonical_player_id": audit_record.canonical_player_id,
                "opponent_canonical_player_id": snapshot.opponent_canonical_player_id,
                "canonical_pair_key": _canonical_pair_key(
                    audit_record.canonical_player_id,
                    snapshot.opponent_canonical_player_id,
                ),
                "player_a_id": snapshot.player_a_id,
                "player_b_id": snapshot.player_b_id,
                "side": snapshot.side,
                "state_key": audit_record.metric_name,
                "pre_value": audit_record.pre_value,
                "post_value": audit_record.post_value,
                "pre_count": audit_record.pre_count,
                "post_count": audit_record.post_count,
                "as_of_date": audit_record.as_of_date,
                "surface": audit_record.surface,
                "cohort_date": snapshot.as_of_date,
                "cohort_round_name": snapshot.round_name,
                "lineage_source_repo": snapshot.lineage.source_repo,
                "lineage_source_commit_sha": snapshot.lineage.source_commit_sha,
                "lineage_source_file_path": snapshot.lineage.source_file_path,
                "lineage_source_row_number": snapshot.lineage.source_row_number,
                "lineage_source_snapshot_root": snapshot.lineage.source_snapshot_root,
            }
        )
    return persisted_rows


def persist_feature_build(
    feature_build: FeatureBuildResult,
    *,
    database_path: str | Path,
) -> Path:
    database_file = Path(database_path)
    database_file.parent.mkdir(parents=True, exist_ok=True)

    player_snapshot_rows = [_flatten(snapshot) for snapshot in feature_build.player_snapshots]
    differential_rows = _build_differential_rows(feature_build)
    audit_rows = _build_audit_rows(feature_build)

    connection = duckdb.connect(str(database_file))
    try:
        _replace_table(
            connection,
            table_name="feature_player_snapshots",
            rows=player_snapshot_rows,
            ddl=_ddl_for_rows(
                table_name="feature_player_snapshots",
                rows=player_snapshot_rows,
            ),
        )
        _replace_table(
            connection,
            table_name="feature_differential_rows",
            rows=differential_rows,
            ddl=_ddl_for_rows(
                table_name="feature_differential_rows",
                rows=differential_rows,
            ),
        )
        _replace_table(
            connection,
            table_name="feature_state_audit",
            rows=audit_rows,
            ddl=_ddl_for_rows(
                table_name="feature_state_audit",
                rows=audit_rows,
            ),
        )
    finally:
        connection.close()

    return database_file
