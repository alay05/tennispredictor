from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import duckdb


@dataclass(frozen=True)
class SyntheticModelingFixture:
    database_path: Path
    feature_version: str
    ordered_match_ids: list[str]
    expected_feature_columns: list[str]
    resolved_train_end_date: str
    resolved_validation_end_date: str
    resolved_test_end_date: str


def membership_sha256(canonical_match_ids: list[str]) -> str:
    digest = sha256()
    for canonical_match_id in canonical_match_ids:
        digest.update(canonical_match_id.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def build_synthetic_modeling_fixture(tmp_path: Path) -> SyntheticModelingFixture:
    database_path = tmp_path / "modeling-fixture.duckdb"
    feature_rows = _feature_rows()
    ordered_feature_rows = sorted(
        feature_rows,
        key=lambda row: (
            row["as_of_date"],
            row["lineage_source_file_path"],
            row["lineage_source_row_number"],
            row["canonical_match_id"],
        ),
    )
    ordered_match_ids = [row["canonical_match_id"] for row in ordered_feature_rows]

    connection = duckdb.connect(str(database_path))
    try:
        connection.execute(
            """
            create table feature_differential_rows (
                feature_version varchar,
                canonical_match_id varchar,
                player_a_id varchar,
                player_b_id varchar,
                as_of_date varchar,
                player_a_side varchar,
                player_b_side varchar,
                surface varchar,
                tourney_level varchar,
                round_name varchar,
                best_of integer,
                player_a_rank integer,
                player_b_rank integer,
                player_a_elo_overall double,
                player_b_elo_overall double,
                player_a_form_last_5_win_rate double,
                player_b_form_last_5_win_rate double,
                player_a_stats_missing boolean,
                player_b_stats_missing boolean,
                rank_diff integer,
                elo_diff double,
                surface_elo_diff double,
                service_first_won_rate_diff double,
                return_first_won_allowed_rate_diff double,
                ace_rate_diff double,
                h2h_win_rate_diff double,
                h2h_match_count integer,
                lineage_source_repo varchar,
                lineage_source_commit_sha varchar,
                lineage_source_file_path varchar,
                lineage_source_row_number integer,
                lineage_source_snapshot_root varchar
            )
            """
        )
        connection.executemany(
            """
            insert into feature_differential_rows values (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            [
                tuple(row[column] for column in row.keys())
                for row in feature_rows
            ],
        )
        connection.execute(
            """
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
            """
        )
        connection.executemany(
            """
            insert into canonical_matches values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row["canonical_match_id"],
                    f"tournament:synthetic:{row['as_of_date']}",
                    row["player_a_id"]
                    if row["lineage_source_row_number"] % 3 != 0
                    else row["player_b_id"],
                    row["player_b_id"]
                    if row["lineage_source_row_number"] % 3 != 0
                    else row["player_a_id"],
                    "2024-001",
                    row["surface"],
                    "Example Open",
                    row["tourney_level"],
                    row["as_of_date"],
                    row["round_name"],
                    row["best_of"],
                    "6-4 6-4",
                    row["lineage_source_repo"],
                    row["lineage_source_commit_sha"],
                    row["lineage_source_file_path"],
                    row["lineage_source_row_number"],
                    row["lineage_source_snapshot_root"],
                )
                for row in feature_rows
            ],
        )
    finally:
        connection.close()

    return SyntheticModelingFixture(
        database_path=database_path,
        feature_version="03-01-test",
        ordered_match_ids=ordered_match_ids,
        expected_feature_columns=[
            "surface",
            "tourney_level",
            "round_name",
            "best_of",
            "player_a_rank",
            "player_b_rank",
            "player_a_elo_overall",
            "player_b_elo_overall",
            "player_a_form_last_5_win_rate",
            "player_b_form_last_5_win_rate",
            "player_a_stats_missing",
            "player_b_stats_missing",
            "rank_diff",
            "elo_diff",
            "surface_elo_diff",
            "service_first_won_rate_diff",
            "return_first_won_allowed_rate_diff",
            "ace_rate_diff",
            "h2h_win_rate_diff",
            "h2h_match_count",
        ],
        resolved_train_end_date="20240114",
        resolved_validation_end_date="20240117",
        resolved_test_end_date="20240120",
    )


def _feature_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    dates = {
        1: "20240101",
        2: "20240102",
        3: "20240102",
        4: "20240104",
        5: "20240105",
        6: "20240106",
        7: "20240107",
        8: "20240108",
        9: "20240108",
        10: "20240110",
        11: "20240111",
        12: "20240112",
        13: "20240113",
        14: "20240114",
        15: "20240115",
        16: "20240116",
        17: "20240117",
        18: "20240118",
        19: "20240119",
        20: "20240120",
    }
    lineage_files = {
        1: "atp_matches_2024.csv",
        2: "atp_matches_2024.csv",
        3: "atp_matches_2024_extra.csv",
        4: "atp_matches_2024.csv",
        5: "atp_matches_2024.csv",
        6: "atp_matches_2024.csv",
        7: "atp_matches_2024.csv",
        8: "atp_matches_2024.csv",
        9: "atp_matches_2024_extra.csv",
        10: "atp_matches_2024.csv",
        11: "atp_matches_2024.csv",
        12: "atp_matches_2024.csv",
        13: "atp_matches_2024.csv",
        14: "atp_matches_2024.csv",
        15: "atp_matches_2024.csv",
        16: "atp_matches_2024.csv",
        17: "atp_matches_2024.csv",
        18: "atp_matches_2024.csv",
        19: "atp_matches_2024.csv",
        20: "atp_matches_2024.csv",
    }

    for match_index in range(1, 21):
        player_a_id = f"player:sackmann:{match_index:03d}"
        player_b_id = f"player:sackmann:{match_index + 100:03d}"
        rows.append(
            {
                "feature_version": "03-01-test",
                "canonical_match_id": f"match:synthetic:{match_index:02d}",
                "player_a_id": player_a_id,
                "player_b_id": player_b_id,
                "as_of_date": dates[match_index],
                "player_a_side": "A",
                "player_b_side": "B",
                "surface": ("Hard", "Clay", "Grass")[match_index % 3],
                "tourney_level": "A" if match_index % 2 == 0 else "M",
                "round_name": ("R64", "R32", "R16", "QF")[match_index % 4],
                "best_of": 3,
                "player_a_rank": match_index + 10,
                "player_b_rank": match_index + 30,
                "player_a_elo_overall": 1500.0 + match_index,
                "player_b_elo_overall": 1475.0 + match_index,
                "player_a_form_last_5_win_rate": round(0.40 + (match_index * 0.01), 3),
                "player_b_form_last_5_win_rate": round(0.35 + (match_index * 0.01), 3),
                "player_a_stats_missing": match_index % 5 == 0,
                "player_b_stats_missing": match_index % 7 == 0,
                "rank_diff": -20,
                "elo_diff": 25.0,
                "surface_elo_diff": 18.0,
                "service_first_won_rate_diff": round(0.03 + (match_index * 0.001), 3),
                "return_first_won_allowed_rate_diff": round(-0.02 - (match_index * 0.001), 3),
                "ace_rate_diff": round(0.01 + (match_index * 0.001), 3),
                "h2h_win_rate_diff": round((match_index % 4) * 0.1, 3),
                "h2h_match_count": match_index % 6,
                "lineage_source_repo": "JeffSackmann/tennis_atp",
                "lineage_source_commit_sha": "abcdef1",
                "lineage_source_file_path": lineage_files[match_index],
                "lineage_source_row_number": match_index,
                "lineage_source_snapshot_root": "/tmp/raw-snapshot",
            }
        )

    inserted_order = [
        14,
        1,
        20,
        3,
        7,
        2,
        6,
        4,
        10,
        8,
        9,
        5,
        11,
        12,
        13,
        15,
        16,
        17,
        18,
        19,
    ]
    return [rows[index - 1] for index in inserted_order]
