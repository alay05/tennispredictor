from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from tennisprediction.domain.models import (
    CanonicalMatch,
    CanonicalMatchStat,
    CanonicalRanking,
    SourceLineage,
)
from tennisprediction.features.persistence import persist_feature_build
from tennisprediction.features.runner import build_feature_snapshots


def _lineage(*, file_name: str, row_number: int) -> SourceLineage:
    return SourceLineage(
        source_repo="JeffSackmann/tennis_atp",
        source_commit_sha="abcdef1",
        source_file_path=file_name,
        source_row_number=row_number,
        source_snapshot_root="/tmp/raw-snapshot",
    )


def _match(
    *,
    match_id: str,
    tourney_date: str,
    round_name: str,
    winner_id: int,
    loser_id: int,
    row_number: int,
) -> CanonicalMatch:
    return CanonicalMatch(
        canonical_match_id=match_id,
        canonical_tournament_id=f"tournament:synthetic:example-open:{tourney_date}",
        winner_canonical_player_id=f"player:sackmann:{winner_id}",
        loser_canonical_player_id=f"player:sackmann:{loser_id}",
        source_tourney_id="2024-001",
        surface="Hard",
        tourney_name="Example Open",
        tourney_level="A",
        tourney_date=tourney_date,
        round_name=round_name,
        best_of=3,
        score="6-4 6-4",
        lineage=_lineage(file_name="atp_matches_2024.csv", row_number=row_number),
    )


def _ranking(
    *,
    player_id: int,
    ranking_date: str,
    rank: int,
    points: int,
    row_number: int,
) -> CanonicalRanking:
    return CanonicalRanking(
        canonical_ranking_id=f"ranking:synthetic:{player_id}:{ranking_date}",
        canonical_player_id=f"player:sackmann:{player_id}",
        ranking_date=ranking_date,
        rank=rank,
        points=points,
        lineage=_lineage(file_name="atp_rankings_2024.csv", row_number=row_number),
    )


def _match_stat(
    *,
    source_match_id: int,
    first_won_player1: int,
    first_won_player2: int,
    ace_player1: int,
    ace_player2: int,
    serve_points_player1: int,
    serve_points_player2: int,
    row_number: int,
    file_name: str = "atp_matchstats_2024.csv",
) -> CanonicalMatchStat:
    return CanonicalMatchStat(
        canonical_match_stat_id=f"match-stat:sackmann:{source_match_id}",
        source_match_id=source_match_id,
        first_won_player1=first_won_player1,
        first_won_player2=first_won_player2,
        ace_player1=ace_player1,
        ace_player2=ace_player2,
        serve_points_player1=serve_points_player1,
        serve_points_player2=serve_points_player2,
        lineage=_lineage(file_name=file_name, row_number=row_number),
    )


def _synthetic_history(*, include_cross_file_collision: bool = False) -> tuple[
    list[CanonicalMatch],
    list[CanonicalRanking],
    list[CanonicalMatchStat],
]:
    matches = [
        _match(
            match_id="match:synthetic:example-open:20240101:1",
            tourney_date="20240101",
            round_name="R32",
            winner_id=1,
            loser_id=2,
            row_number=2,
        ),
        _match(
            match_id="match:synthetic:example-open:20240108:2",
            tourney_date="20240108",
            round_name="R16",
            winner_id=2,
            loser_id=1,
            row_number=3,
        ),
        _match(
            match_id="match:synthetic:example-open:20240115:3",
            tourney_date="20240115",
            round_name="QF",
            winner_id=1,
            loser_id=2,
            row_number=4,
        ),
        _match(
            match_id="match:synthetic:example-open:20240115:4",
            tourney_date="20240115",
            round_name="QF",
            winner_id=3,
            loser_id=4,
            row_number=5,
        ),
    ]
    rankings = [
        _ranking(player_id=1, ranking_date="20240101", rank=8, points=1450, row_number=2),
        _ranking(player_id=2, ranking_date="20240101", rank=18, points=1125, row_number=3),
        _ranking(player_id=3, ranking_date="20240101", rank=24, points=980, row_number=4),
        _ranking(player_id=4, ranking_date="20240101", rank=31, points=860, row_number=5),
        _ranking(player_id=1, ranking_date="20240108", rank=7, points=1510, row_number=6),
        _ranking(player_id=2, ranking_date="20240108", rank=16, points=1180, row_number=7),
        _ranking(player_id=3, ranking_date="20240108", rank=23, points=1010, row_number=8),
        _ranking(player_id=4, ranking_date="20240108", rank=30, points=885, row_number=9),
    ]
    match_stats = [
        _match_stat(
            source_match_id=101,
            first_won_player1=28,
            first_won_player2=24,
            ace_player1=6,
            ace_player2=4,
            serve_points_player1=38,
            serve_points_player2=36,
            row_number=2,
        ),
        _match_stat(
            source_match_id=102,
            first_won_player1=27,
            first_won_player2=26,
            ace_player1=5,
            ace_player2=3,
            serve_points_player1=37,
            serve_points_player2=35,
            row_number=3,
        ),
        _match_stat(
            source_match_id=103,
            first_won_player1=29,
            first_won_player2=25,
            ace_player1=7,
            ace_player2=4,
            serve_points_player1=39,
            serve_points_player2=34,
            row_number=4,
        ),
        _match_stat(
            source_match_id=104,
            first_won_player1=30,
            first_won_player2=21,
            ace_player1=8,
            ace_player2=2,
            serve_points_player1=40,
            serve_points_player2=33,
            row_number=5,
        ),
    ]
    if include_cross_file_collision:
        match_stats.append(
            _match_stat(
                source_match_id=204,
                first_won_player1=14,
                first_won_player2=39,
                ace_player1=1,
                ace_player2=12,
                serve_points_player1=70,
                serve_points_player2=60,
                row_number=2,
                file_name="atp_matchstats_2025.csv",
            )
        )
    return matches, rankings, match_stats


def _columns(
    connection: duckdb.DuckDBPyConnection,
    *,
    table_name: str,
) -> set[str]:
    rows = connection.execute(f"pragma table_info('{table_name}')").fetchall()
    return {row[1] for row in rows}


def test_persist_feature_build_writes_snapshot_row_and_audit_tables(tmp_path: Path) -> None:
    matches, rankings, match_stats = _synthetic_history()
    feature_build = build_feature_snapshots(
        matches=matches,
        rankings=rankings,
        match_stats=match_stats,
        feature_version="02-04-test",
    )

    database_path = tmp_path / "features.duckdb"
    persisted_path = persist_feature_build(feature_build, database_path=database_path)

    connection = duckdb.connect(str(persisted_path))
    try:
        tables = {
            row[0]
            for row in connection.execute("show tables").fetchall()
        }
        assert tables == {
            "feature_differential_rows",
            "feature_player_snapshots",
            "feature_state_audit",
        }

        snapshot_columns = _columns(connection, table_name="feature_player_snapshots")
        assert {
            "feature_version",
            "canonical_match_id",
            "canonical_player_id",
            "opponent_canonical_player_id",
            "player_a_id",
            "player_b_id",
            "as_of_date",
            "side",
            "rank",
            "ranking_change",
            "elo_overall",
            "elo_surface",
            "form_last_5_count",
            "stats_match_count",
            "serve_point_exposure",
            "head_to_head_match_count",
            "lineage_source_row_number",
        } <= snapshot_columns

        differential_columns = _columns(connection, table_name="feature_differential_rows")
        assert {
            "feature_version",
            "canonical_match_id",
            "player_a_id",
            "player_b_id",
            "as_of_date",
            "player_a_side",
            "player_b_side",
            "player_a_rank",
            "player_b_rank",
            "player_a_ranking_change",
            "player_b_ranking_change",
            "player_a_elo_overall",
            "player_b_elo_overall",
            "player_a_form_last_5_count",
            "player_b_form_last_5_count",
            "player_a_stats_missing",
            "player_b_stats_missing",
            "player_a_serve_point_exposure",
            "player_b_serve_point_exposure",
            "rank_diff",
            "ranking_change_diff",
            "elo_diff",
            "surface_elo_diff",
            "form_last_5_win_rate_diff",
            "service_first_won_rate_diff",
            "return_first_won_allowed_rate_diff",
            "ace_rate_diff",
            "h2h_win_rate_diff",
            "h2h_match_count",
            "lineage_source_file_path",
            "lineage_source_row_number",
        } <= differential_columns

        audit_columns = _columns(connection, table_name="feature_state_audit")
        assert {
            "canonical_match_id",
            "canonical_player_id",
            "opponent_canonical_player_id",
            "canonical_pair_key",
            "state_key",
            "pre_value",
            "post_value",
            "pre_count",
            "post_count",
            "cohort_date",
            "cohort_round_name",
        } <= audit_columns

        persisted_row = connection.execute(
            """
            select
                feature_version,
                canonical_match_id,
                player_a_id,
                player_b_id,
                player_a_side,
                player_b_side,
                player_a_stats_missing,
                player_b_stats_missing,
                player_a_serve_point_exposure,
                player_b_serve_point_exposure
            from feature_differential_rows
            where canonical_match_id = 'match:synthetic:example-open:20240115:3'
            """
        ).fetchone()
        assert persisted_row == (
            "02-04-test",
            "match:synthetic:example-open:20240115:3",
            "player:sackmann:1",
            "player:sackmann:2",
            "A",
            "B",
            False,
            False,
            73,
            73,
        )

        persisted_h2h_audit = connection.execute(
            """
            select
                opponent_canonical_player_id,
                canonical_pair_key,
                state_key,
                cohort_date,
                cohort_round_name
            from feature_state_audit
            where canonical_match_id = 'match:synthetic:example-open:20240115:3'
              and state_key = 'head_to_head_win_rate'
            order by canonical_player_id
            """
        ).fetchall()
        assert persisted_h2h_audit == [
            (
                "player:sackmann:2",
                "player:sackmann:1::player:sackmann:2",
                "head_to_head_win_rate",
                "20240115",
                "QF",
            ),
            (
                "player:sackmann:1",
                "player:sackmann:1::player:sackmann:2",
                "head_to_head_win_rate",
                "20240115",
                "QF",
            ),
        ]
    finally:
        connection.close()


def test_persist_feature_build_preserves_collision_fixture_stat_identity(tmp_path: Path) -> None:
    matches, rankings, match_stats = _synthetic_history(include_cross_file_collision=True)
    feature_build = build_feature_snapshots(
        matches=matches,
        rankings=rankings,
        match_stats=match_stats,
        feature_version="02-05-test",
    )

    database_path = tmp_path / "collision-features.duckdb"
    persisted_path = persist_feature_build(feature_build, database_path=database_path)

    connection = duckdb.connect(str(persisted_path))
    try:
        persisted_row = connection.execute(
            """
            select
                player_a_service_first_won_rate,
                player_b_service_first_won_rate,
                player_a_serve_point_exposure,
                player_b_serve_point_exposure,
                service_first_won_rate_diff
            from feature_differential_rows
            where canonical_match_id = 'match:synthetic:example-open:20240115:3'
            """
        ).fetchone()
        assert persisted_row is not None
        assert persisted_row[0] == pytest.approx((28 + 26) / (38 + 35))
        assert persisted_row[1] == pytest.approx((24 + 27) / (36 + 37))
        assert persisted_row[2] == 73
        assert persisted_row[3] == 73
        assert persisted_row[4] == pytest.approx(((28 + 26) / (38 + 35)) - ((24 + 27) / (36 + 37)))
    finally:
        connection.close()
