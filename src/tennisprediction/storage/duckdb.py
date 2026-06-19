from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

import duckdb

from tennisprediction.domain.models import CanonicalSnapshot


def _flatten(value: Any) -> Any:
    if is_dataclass(value):
        flattened: dict[str, Any] = {}
        for key, nested_value in asdict(value).items():
            if isinstance(nested_value, dict):
                for nested_key, nested_item in nested_value.items():
                    flattened[f"{key}_{nested_key}"] = nested_item
            else:
                flattened[key] = nested_value
        return flattened
    return value


def _replace_table(
    connection: duckdb.DuckDBPyConnection,
    *,
    table_name: str,
    rows: list[dict[str, Any]],
    ddl: str,
) -> None:
    connection.execute(f"drop table if exists {table_name}")
    connection.execute(ddl)
    if not rows:
        return

    columns = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    column_list = ", ".join(columns)
    values = [tuple(row[column] for column in columns) for row in rows]
    connection.executemany(
        f"insert into {table_name} ({column_list}) values ({placeholders})",
        values,
    )


def persist_canonical_snapshot(
    canonical_snapshot: CanonicalSnapshot,
    *,
    database_path: str | Path,
) -> Path:
    database_file = Path(database_path)
    database_file.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_file))
    try:
        _replace_table(
            connection,
            table_name="canonical_players",
            rows=[_flatten(player) for player in canonical_snapshot.players],
            ddl="""
                create table canonical_players (
                    canonical_player_id varchar,
                    source_player_id integer,
                    first_name varchar,
                    last_name varchar,
                    full_name varchar,
                    lineage_source_repo varchar,
                    lineage_source_commit_sha varchar,
                    lineage_source_file_path varchar,
                    lineage_source_row_number integer,
                    lineage_source_snapshot_root varchar
                )
            """,
        )
        _replace_table(
            connection,
            table_name="canonical_tournaments",
            rows=[_flatten(tournament) for tournament in canonical_snapshot.tournaments],
            ddl="""
                create table canonical_tournaments (
                    canonical_tournament_id varchar,
                    source_tourney_id varchar,
                    tourney_name varchar,
                    surface varchar,
                    tourney_level varchar,
                    tourney_date varchar,
                    lineage_source_repo varchar,
                    lineage_source_commit_sha varchar,
                    lineage_source_file_path varchar,
                    lineage_source_row_number integer,
                    lineage_source_snapshot_root varchar
                )
            """,
        )
        _replace_table(
            connection,
            table_name="canonical_matches",
            rows=[_flatten(match) for match in canonical_snapshot.matches],
            ddl="""
                create table canonical_matches (
                    canonical_match_id varchar,
                    canonical_tournament_id varchar,
                    winner_canonical_player_id varchar,
                    loser_canonical_player_id varchar,
                    source_tourney_id varchar,
                    surface varchar,
                    tourney_name varchar,
                    tourney_level varchar,
                    tourney_date varchar,
                    round_name varchar,
                    best_of integer,
                    score varchar,
                    lineage_source_repo varchar,
                    lineage_source_commit_sha varchar,
                    lineage_source_file_path varchar,
                    lineage_source_row_number integer,
                    lineage_source_snapshot_root varchar
                )
            """,
        )
        _replace_table(
            connection,
            table_name="canonical_rankings",
            rows=[_flatten(ranking) for ranking in canonical_snapshot.rankings],
            ddl="""
                create table canonical_rankings (
                    canonical_ranking_id varchar,
                    canonical_player_id varchar,
                    ranking_date varchar,
                    rank integer,
                    points integer,
                    lineage_source_repo varchar,
                    lineage_source_commit_sha varchar,
                    lineage_source_file_path varchar,
                    lineage_source_row_number integer,
                    lineage_source_snapshot_root varchar
                )
            """,
        )
        _replace_table(
            connection,
            table_name="canonical_match_stats",
            rows=[_flatten(match_stat) for match_stat in canonical_snapshot.match_stats],
            ddl="""
                create table canonical_match_stats (
                    canonical_match_stat_id varchar,
                    source_match_id integer,
                    first_won_player1 integer,
                    first_won_player2 integer,
                    ace_player1 integer,
                    ace_player2 integer,
                    serve_points_player1 integer,
                    serve_points_player2 integer,
                    lineage_source_repo varchar,
                    lineage_source_commit_sha varchar,
                    lineage_source_file_path varchar,
                    lineage_source_row_number integer,
                    lineage_source_snapshot_root varchar
                )
            """,
        )
    finally:
        connection.close()

    return database_file
