from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal
from pathlib import Path

import duckdb
import pytest

import tennisprediction.config as config_module
from tennisprediction.kalshi.schemas import (
    KalshiMarketDetailDTO,
    KalshiMarketDTO,
    KalshiRequestMetadata,
)
from tennisprediction.kalshi.snapshots import (
    build_market_detail_snapshot_row,
    build_market_snapshot_row,
    build_request_log_row,
)
from tennisprediction.kalshi.storage import persist_kalshi_snapshot_batch
from tennisprediction.market_mapping.resolver import (
    persist_market_mapping_evidence,
    resolve_kalshi_market_mappings,
)
from tennisprediction.market_mapping.schemas import (
    MappingConfidenceTier,
    MarketMappingState,
)


def test_resolver_matches_same_day_pair_and_persists_side_orientation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = _seed_mapping_database(
        tmp_path,
        monkeypatch,
        market_title="ATP Queen's Club: Taylor Fritz vs Frances Tiafoe",
        yes_sub_title="Taylor Fritz",
        no_sub_title="Frances Tiafoe",
        canonical_players=[
            ("player:fritz", "Taylor", "Fritz", "Taylor Fritz"),
            ("player:tiafoe", "Frances", "Tiafoe", "Frances Tiafoe"),
        ],
        canonical_matches=[
            {
                "canonical_match_id": "match:queens:r16:fritz-tiafoe",
                "winner_canonical_player_id": "player:fritz",
                "loser_canonical_player_id": "player:tiafoe",
                "tourney_date": "20240620",
                "round_name": "R16",
            }
        ],
    )

    rows = resolve_kalshi_market_mappings(database_path=database_path)

    assert len(rows) == 1
    row = rows[0]
    assert row.market_ticker == "KXATP-001"
    assert row.mapping_state == MarketMappingState.matched
    assert row.mapping_confidence == MappingConfidenceTier.exact_names
    assert row.canonical_match_id == "match:queens:r16:fritz-tiafoe"
    assert row.raw_title == "ATP Queen's Club: Taylor Fritz vs Frances Tiafoe"
    assert row.raw_yes_sub_title == "Taylor Fritz"
    assert row.raw_no_sub_title == "Frances Tiafoe"
    assert row.normalized_yes_player_name == "taylor fritz"
    assert row.normalized_no_player_name == "frances tiafoe"
    assert row.yes_canonical_player_id == "player:fritz"
    assert row.no_canonical_player_id == "player:tiafoe"
    assert row.yes_maps_to_player_a is True
    assert row.no_maps_to_player_b is True
    assert row.rejection_reason_codes == ()

    persist_market_mapping_evidence(rows, database_path=database_path)

    connection = duckdb.connect(str(database_path))
    try:
        evidence_columns = tuple(
            row[1]
            for row in connection.execute("pragma table_info('market_mapping_evidence')").fetchall()
        )
        assert evidence_columns == (
            "market_ticker",
            "event_ticker",
            "collected_at_utc",
            "raw_title",
            "raw_yes_sub_title",
            "raw_no_sub_title",
            "normalized_yes_player_name",
            "normalized_no_player_name",
            "alias_hit_player_ids_json",
            "candidate_canonical_match_ids_json",
            "mapping_state",
            "mapping_confidence",
            "canonical_match_id",
            "yes_canonical_player_id",
            "no_canonical_player_id",
            "yes_maps_to_player_a",
            "no_maps_to_player_b",
            "rejection_reason_codes_json",
        )
        persisted_row = connection.execute(
            """
            select
                alias_hit_player_ids_json,
                candidate_canonical_match_ids_json,
                rejection_reason_codes_json
            from market_mapping_evidence
            where market_ticker = 'KXATP-001'
            """
        ).fetchone()
    finally:
        connection.close()

    assert persisted_row is not None
    assert json.loads(persisted_row[0]) == []
    assert json.loads(persisted_row[1]) == ["match:queens:r16:fritz-tiafoe"]
    assert json.loads(persisted_row[2]) == []


@pytest.mark.parametrize(
    ("event_ticker", "market_title", "expected_reason_code"),
    [
        ("ATP-WIN-001", "ATP Wimbledon Champion", "unsupported_contract_shape"),
        ("WTA-WIN-001", "WTA Eastbourne: Taylor Fritz vs Frances Tiafoe", "non_atp_event"),
    ],
)
def test_resolve_kalshi_market_mappings_marks_out_of_scope_markets_as_excluded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    event_ticker: str,
    market_title: str,
    expected_reason_code: str,
) -> None:
    database_path = _seed_mapping_database(
        tmp_path,
        monkeypatch,
        event_ticker=event_ticker,
        market_title=market_title,
        yes_sub_title="Taylor Fritz",
        no_sub_title="Frances Tiafoe",
        canonical_players=[
            ("player:fritz", "Taylor", "Fritz", "Taylor Fritz"),
            ("player:tiafoe", "Frances", "Tiafoe", "Frances Tiafoe"),
        ],
        canonical_matches=[
            {
                "canonical_match_id": "match:one",
                "winner_canonical_player_id": "player:fritz",
                "loser_canonical_player_id": "player:tiafoe",
                "tourney_date": "20240620",
                "round_name": "R16",
            }
        ],
    )

    rows = resolve_kalshi_market_mappings(database_path=database_path)

    assert len(rows) == 1
    row = rows[0]
    assert row.mapping_state == MarketMappingState.excluded
    assert row.mapping_confidence == MappingConfidenceTier.manual_review_required
    assert expected_reason_code in row.rejection_reason_codes
    assert row.canonical_match_id is None


def test_resolve_kalshi_market_mappings_fails_closed_for_ambiguous_and_unmatched_cases(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ambiguous_identity_database = _seed_mapping_database(
        tmp_path / "ambiguous-identity",
        monkeypatch,
        market_title="ATP London: Joao Fonseca vs Taylor Fritz",
        yes_sub_title="Joao Fonseca",
        no_sub_title="Taylor Fritz",
        canonical_players=[
            ("player:joao-1", "Joao", "Fonseca", "Joao Fonseca"),
            ("player:joao-2", "João", "Fonseca", "João Fonseca"),
            ("player:fritz", "Taylor", "Fritz", "Taylor Fritz"),
        ],
        canonical_matches=[
            {
                "canonical_match_id": "match:identity",
                "winner_canonical_player_id": "player:joao-1",
                "loser_canonical_player_id": "player:fritz",
                "tourney_date": "20240620",
                "round_name": "R16",
            }
        ],
    )
    ambiguous_identity_row = resolve_kalshi_market_mappings(
        database_path=ambiguous_identity_database
    )[0]
    assert ambiguous_identity_row.mapping_state == MarketMappingState.ambiguous
    assert ambiguous_identity_row.mapping_confidence == MappingConfidenceTier.manual_review_required
    assert "ambiguous_player_identity" in ambiguous_identity_row.rejection_reason_codes

    ambiguous_side_database = _seed_mapping_database(
        tmp_path / "ambiguous-side",
        monkeypatch,
        market_title="ATP London: Taylor Fritz vs Frances Tiafoe",
        yes_sub_title="Match Winner",
        no_sub_title="Field",
        canonical_players=[
            ("player:fritz", "Taylor", "Fritz", "Taylor Fritz"),
            ("player:tiafoe", "Frances", "Tiafoe", "Frances Tiafoe"),
        ],
        canonical_matches=[
            {
                "canonical_match_id": "match:side",
                "winner_canonical_player_id": "player:fritz",
                "loser_canonical_player_id": "player:tiafoe",
                "tourney_date": "20240620",
                "round_name": "R16",
            }
        ],
    )
    ambiguous_side_row = resolve_kalshi_market_mappings(database_path=ambiguous_side_database)[0]
    assert ambiguous_side_row.mapping_state == MarketMappingState.ambiguous
    assert ambiguous_side_row.mapping_confidence == MappingConfidenceTier.manual_review_required
    assert "ambiguous_side_orientation" in ambiguous_side_row.rejection_reason_codes

    multiple_match_database = _seed_mapping_database(
        tmp_path / "multiple-matches",
        monkeypatch,
        market_title="ATP London: Taylor Fritz vs Frances Tiafoe",
        yes_sub_title="Taylor Fritz",
        no_sub_title="Frances Tiafoe",
        canonical_players=[
            ("player:fritz", "Taylor", "Fritz", "Taylor Fritz"),
            ("player:tiafoe", "Frances", "Tiafoe", "Frances Tiafoe"),
        ],
        canonical_matches=[
            {
                "canonical_match_id": "match:duplicate:1",
                "winner_canonical_player_id": "player:fritz",
                "loser_canonical_player_id": "player:tiafoe",
                "tourney_date": "20240620",
                "round_name": "R16",
            },
            {
                "canonical_match_id": "match:duplicate:2",
                "winner_canonical_player_id": "player:tiafoe",
                "loser_canonical_player_id": "player:fritz",
                "tourney_date": "20240620",
                "round_name": "R16",
            },
        ],
    )
    multiple_match_row = resolve_kalshi_market_mappings(database_path=multiple_match_database)[0]
    assert multiple_match_row.mapping_state == MarketMappingState.ambiguous
    assert multiple_match_row.mapping_confidence == MappingConfidenceTier.exact_names
    assert multiple_match_row.candidate_canonical_match_ids == (
        "match:duplicate:1",
        "match:duplicate:2",
    )
    assert "multiple_canonical_matches" in multiple_match_row.rejection_reason_codes

    unmatched_database = _seed_mapping_database(
        tmp_path / "timing-miss",
        monkeypatch,
        market_title="ATP London: Taylor Fritz vs Frances Tiafoe",
        yes_sub_title="Taylor Fritz",
        no_sub_title="Frances Tiafoe",
        canonical_players=[
            ("player:fritz", "Taylor", "Fritz", "Taylor Fritz"),
            ("player:tiafoe", "Frances", "Tiafoe", "Frances Tiafoe"),
        ],
        canonical_matches=[
            {
                "canonical_match_id": "match:old",
                "winner_canonical_player_id": "player:fritz",
                "loser_canonical_player_id": "player:tiafoe",
                "tourney_date": "20240621",
                "round_name": "R16",
            }
        ],
    )
    unmatched_row = resolve_kalshi_market_mappings(database_path=unmatched_database)[0]
    assert unmatched_row.mapping_state == MarketMappingState.unmatched
    assert unmatched_row.mapping_confidence == MappingConfidenceTier.exact_names
    assert unmatched_row.canonical_match_id is None
    assert unmatched_row.candidate_canonical_match_ids == ()
    assert "timing_window_miss" in unmatched_row.rejection_reason_codes


def test_resolve_kalshi_market_mappings_uses_alias_override_confidence_for_matched_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    alias_rows = [
        {
            "raw_market_name": "T. Fritz",
            "normalized_market_name": "t fritz",
            "canonical_player_id": "player:fritz",
            "canonical_player_name": "Taylor Fritz",
            "source_note": "Kalshi abbreviated first initial",
            "created_at_utc": "2026-06-21T12:00:00Z",
            "updated_at_utc": "2026-06-21T12:00:00Z",
        },
        {
            "raw_market_name": "F. Tiafoe",
            "normalized_market_name": "f tiafoe",
            "canonical_player_id": "player:tiafoe",
            "canonical_player_name": "Frances Tiafoe",
            "source_note": "Kalshi abbreviated first initial",
            "created_at_utc": "2026-06-21T12:00:00Z",
            "updated_at_utc": "2026-06-21T12:00:00Z",
        },
    ]
    alias_path = _write_alias_artifact(tmp_path, alias_rows)
    database_path = _seed_mapping_database(
        tmp_path,
        monkeypatch,
        market_title="ATP London: Taylor Fritz vs Frances Tiafoe",
        yes_sub_title="T. Fritz",
        no_sub_title="F. Tiafoe",
        canonical_players=[
            ("player:fritz", "Taylor", "Fritz", "Taylor Fritz"),
            ("player:tiafoe", "Frances", "Tiafoe", "Frances Tiafoe"),
        ],
        canonical_matches=[
            {
                "canonical_match_id": "match:alias",
                "winner_canonical_player_id": "player:fritz",
                "loser_canonical_player_id": "player:tiafoe",
                "tourney_date": "20240620",
                "round_name": "R16",
            }
        ],
    )

    rows = resolve_kalshi_market_mappings(
        database_path=database_path,
        alias_overrides_path=alias_path,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.mapping_state == MarketMappingState.matched
    assert row.mapping_confidence == MappingConfidenceTier.alias_override
    assert set(row.alias_hit_player_ids) == {"player:fritz", "player:tiafoe"}


def _seed_mapping_database(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    event_ticker: str = "ATP-LON-001",
    market_title: str,
    yes_sub_title: str,
    no_sub_title: str,
    canonical_players: list[tuple[str, str, str, str]],
    canonical_matches: list[dict[str, str]],
) -> Path:
    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    database_path = tmp_path / "data" / "mapping.duckdb"
    database_path.parent.mkdir(parents=True, exist_ok=True)

    _persist_kalshi_market_snapshot(
        database_path=database_path,
        event_ticker=event_ticker,
        market_title=market_title,
        yes_sub_title=yes_sub_title,
        no_sub_title=no_sub_title,
    )

    connection = duckdb.connect(str(database_path))
    try:
        connection.execute(
            """
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
            """
        )
        connection.executemany(
            "insert into canonical_players values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    canonical_player_id,
                    index,
                    first_name,
                    last_name,
                    full_name,
                    "repo",
                    "sha",
                    "atp_players.csv",
                    index,
                    "snapshot",
                )
                for index, (
                    canonical_player_id,
                    first_name,
                    last_name,
                    full_name,
                ) in enumerate(canonical_players, start=1)
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
            (
                "insert into canonical_matches values "
                "(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
            ),
            [
                (
                    row["canonical_match_id"],
                    "tournament:synthetic:20240620",
                    row["winner_canonical_player_id"],
                    row["loser_canonical_player_id"],
                    "2024-001",
                    "grass",
                    "Queen's Club",
                    "ATP500",
                    row["tourney_date"],
                    row["round_name"],
                    3,
                    "6-4 6-4",
                    "repo",
                    "sha",
                    "atp_matches_2024.csv",
                    index,
                    "snapshot",
                )
                for index, row in enumerate(canonical_matches, start=1)
            ],
        )
    finally:
        connection.close()

    return database_path


def _persist_kalshi_market_snapshot(
    *,
    database_path: Path,
    event_ticker: str,
    market_title: str,
    yes_sub_title: str,
    no_sub_title: str,
) -> None:
    collected_at = datetime(2024, 6, 20, 10, 0, 0)
    request_metadata = KalshiRequestMetadata(
        method="GET",
        path="/trade-api/v2/markets",
        query_params=(("status", "open"),),
        timestamp_ms=1718877600000,
        base_url="https://external-api.demo.kalshi.co",
        signed_payload="1718877600000GET/trade-api/v2/markets",
    )
    market = KalshiMarketDTO(
        ticker="KXATP-001",
        event_ticker=event_ticker,
        status="open",
        title=market_title,
        yes_sub_title=yes_sub_title,
        no_sub_title=no_sub_title,
        created_time=collected_at,
        updated_time=collected_at,
        open_time=collected_at,
        close_time=datetime(2024, 6, 20, 18, 0, 0),
        latest_expiration_time=datetime(2024, 6, 20, 19, 0, 0),
        settlement_timer_seconds=120,
        yes_bid_dollars=Decimal("0.51"),
        yes_bid_size_fp=Decimal("10"),
        yes_ask_dollars=Decimal("0.52"),
        yes_ask_size_fp=Decimal("10"),
        no_bid_dollars=Decimal("0.48"),
        no_bid_size_fp=Decimal("10"),
        no_ask_dollars=Decimal("0.49"),
        no_ask_size_fp=Decimal("10"),
        last_price_dollars=Decimal("0.51"),
        volume_fp=Decimal("100"),
        volume_24h_fp=Decimal("100"),
        can_close_early=False,
        fractional_trading_enabled=True,
        open_interest_fp=Decimal("50"),
        notional_value_dollars=Decimal("1"),
        previous_yes_bid_dollars=Decimal("0.50"),
        previous_yes_ask_dollars=Decimal("0.53"),
        previous_no_bid_dollars=Decimal("0.47"),
        previous_no_ask_dollars=Decimal("0.50"),
    )
    request_log = build_request_log_row(
        request_metadata,
        response_status_code=200,
        response_payload={"markets": [{"ticker": market.ticker}]},
        collected_at_utc=collected_at,
    )
    batch = build_market_snapshot_row(request_log, market, response_index=0)
    detail = build_market_detail_snapshot_row(
        request_log,
        KalshiMarketDetailDTO(market=market, request_metadata=request_metadata),
    )
    persist_kalshi_snapshot_batch(
        batch=type(
            "SnapshotBatch",
            (),
            {
                "request_logs": (request_log,),
                "market_snapshots": (batch,),
                "market_detail_snapshots": (detail,),
                "orderbook_snapshots": (),
            },
        )(),
        database_path=database_path,
    )


def _write_alias_artifact(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    artifact_path = tmp_path / "player_alias_overrides.json"
    artifact_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return artifact_path
