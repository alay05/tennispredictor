from __future__ import annotations

import hashlib
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
    KalshiOrderbookDTO,
    KalshiOrderbookLevelDTO,
    KalshiRequestMetadata,
)
from tennisprediction.kalshi.snapshots import (
    MARKET_DETAIL_SNAPSHOT_COLUMNS,
    MARKET_SNAPSHOT_COLUMNS,
    ORDERBOOK_SNAPSHOT_COLUMNS,
    REQUEST_LOG_COLUMNS,
    KalshiSnapshotBatch,
    build_market_detail_snapshot_row,
    build_market_snapshot_row,
    build_orderbook_snapshot_row,
    build_request_log_row,
)
from tennisprediction.kalshi.storage import (
    load_kalshi_snapshot_tables,
    persist_kalshi_snapshot_batch,
)


def test_persist_and_load_kalshi_snapshot_batch_round_trips_metadata_timestamps_and_payload_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    database_path = tmp_path / "data" / "kalshi" / "snapshots.duckdb"
    collected_at = datetime(2024, 1, 1, 12, 34, 56, 123456)

    market = _market_dto()
    market_payload = _market_payload()
    page_request_metadata = _request_metadata(
        method="GET",
        path="/trade-api/v2/markets",
        timestamp_ms=1704112496123,
        query_params=(
            ("limit", "10"),
            ("cursor", "page-1"),
            ("event_ticker", "ATP-EVENT-001"),
            ("status", "open"),
        ),
    )
    page_request_log = build_request_log_row(
        page_request_metadata,
        response_status_code=200,
        response_payload={"markets": [market_payload], "cursor": "page-2"},
        response_cursor="page-2",
        collected_at_utc=collected_at,
    )
    market_snapshot = build_market_snapshot_row(
        page_request_log,
        market,
        response_index=0,
    )

    detail_request_metadata = _request_metadata(
        method="GET",
        path="/trade-api/v2/markets/ATP-OPEN-001",
        timestamp_ms=1704112497123,
    )
    detail_request_log = build_request_log_row(
        detail_request_metadata,
        response_status_code=200,
        response_payload={"market": market_payload},
        collected_at_utc=collected_at,
    )
    market_detail_snapshot = build_market_detail_snapshot_row(
        detail_request_log,
        KalshiMarketDetailDTO(market=market, request_metadata=detail_request_metadata),
    )

    orderbook_request_metadata = _request_metadata(
        method="GET",
        path="/trade-api/v2/markets/ATP-OPEN-001/orderbook",
        timestamp_ms=1704112498123,
    )
    orderbook_payload = {
        "orderbook_fp": {
            "yes_dollars": [["0.1500", "100.00"]],
            "no_dollars": [["0.8500", "75.00"]],
        }
    }
    orderbook_request_log = build_request_log_row(
        orderbook_request_metadata,
        response_status_code=200,
        response_payload=orderbook_payload,
        collected_at_utc=collected_at,
    )
    orderbook_snapshot = build_orderbook_snapshot_row(
        orderbook_request_log,
        KalshiOrderbookDTO(
            ticker="ATP-OPEN-001",
            yes_levels=(KalshiOrderbookLevelDTO(Decimal("0.1500"), Decimal("100.00")),),
            no_levels=(KalshiOrderbookLevelDTO(Decimal("0.8500"), Decimal("75.00")),),
            request_metadata=orderbook_request_metadata,
        ),
    )

    batch = KalshiSnapshotBatch(
        request_logs=(
            page_request_log,
            detail_request_log,
            orderbook_request_log,
        ),
        market_snapshots=(market_snapshot,),
        market_detail_snapshots=(market_detail_snapshot,),
        orderbook_snapshots=(orderbook_snapshot,),
    )

    persisted_path = persist_kalshi_snapshot_batch(batch, database_path=database_path)
    assert persisted_path == database_path.resolve()
    assert persisted_path.is_file()

    loaded = load_kalshi_snapshot_tables(database_path=database_path)
    assert loaded == batch

    assert loaded.request_logs[0].collected_at_utc == collected_at
    assert loaded.request_logs[0].request_cursor == "page-1"
    assert loaded.request_logs[0].request_filter_params_json == (
        '{"event_ticker":"ATP-EVENT-001","status":"open"}'
    )

    expected_checksum = hashlib.sha256(
        json.dumps(
            {"markets": [market_payload], "cursor": "page-2"},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8"),
    ).hexdigest()
    assert loaded.request_logs[0].response_checksum == expected_checksum
    assert loaded.market_snapshots[0].ticker == "ATP-OPEN-001"
    assert loaded.market_snapshots[0].response_index == 0
    assert loaded.market_detail_snapshots[0].open_time == datetime(
        2024, 1, 1, 13, 0
    )
    assert loaded.orderbook_snapshots[0].yes_best_price_dollars == Decimal("0.1500")
    assert loaded.orderbook_snapshots[0].no_best_quantity_fp == Decimal("75.00")


def test_kalshi_snapshot_tables_have_stable_schema_and_table_names(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    database_path = tmp_path / "data" / "kalshi" / "snapshots.duckdb"

    batch = KalshiSnapshotBatch(
        request_logs=(),
        market_snapshots=(),
        market_detail_snapshots=(),
        orderbook_snapshots=(),
    )
    persist_kalshi_snapshot_batch(batch, database_path=database_path)

    connection = duckdb.connect(str(database_path))
    try:
        tables = {
            row[0]
            for row in connection.execute("show tables").fetchall()
        }
        assert tables == {
            "kalshi_request_logs",
            "kalshi_market_snapshots",
            "kalshi_market_detail_snapshots",
            "kalshi_orderbook_snapshots",
        }
        assert _columns(connection, "kalshi_request_logs") == REQUEST_LOG_COLUMNS
        assert _columns(connection, "kalshi_market_snapshots") == MARKET_SNAPSHOT_COLUMNS
        assert _columns(connection, "kalshi_market_detail_snapshots") == (
            MARKET_DETAIL_SNAPSHOT_COLUMNS
        )
        assert _columns(connection, "kalshi_orderbook_snapshots") == (
            ORDERBOOK_SNAPSHOT_COLUMNS
        )
    finally:
        connection.close()


@pytest.mark.parametrize(
    "function_name",
    ["persist", "load"],
)
def test_kalshi_snapshot_storage_rejects_non_repo_local_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    function_name: str,
) -> None:
    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    outside_path = tmp_path.parent / "outside" / "snapshots.duckdb"
    batch = KalshiSnapshotBatch(
        request_logs=(),
        market_snapshots=(),
        market_detail_snapshots=(),
        orderbook_snapshots=(),
    )

    if function_name == "persist":
        with pytest.raises(ValueError, match="repository"):
            persist_kalshi_snapshot_batch(batch, database_path=outside_path)
        return

    with pytest.raises(ValueError, match="repository"):
        load_kalshi_snapshot_tables(database_path=outside_path)


def _request_metadata(
    *,
    method: str,
    path: str,
    timestamp_ms: int,
    query_params: tuple[tuple[str, str], ...] = (),
) -> KalshiRequestMetadata:
    return KalshiRequestMetadata(
        method=method,
        path=path,
        query_params=query_params,
        timestamp_ms=timestamp_ms,
        base_url="https://external-api.demo.kalshi.co",
        signed_payload=f"{timestamp_ms}{method}{path}",
    )


def _market_dto() -> KalshiMarketDTO:
    return KalshiMarketDTO(
        ticker="ATP-OPEN-001",
        event_ticker="ATP-EVENT-001",
        status="open",
        title="ATP Open Winner",
        yes_sub_title="Yes side",
        no_sub_title="No side",
        created_time=datetime(2024, 1, 1, 10, 0),
        updated_time=datetime(2024, 1, 1, 11, 0),
        open_time=datetime(2024, 1, 1, 13, 0),
        close_time=datetime(2024, 1, 1, 18, 0),
        latest_expiration_time=datetime(2024, 1, 1, 19, 0),
        settlement_timer_seconds=120,
        yes_bid_dollars=Decimal("0.5600"),
        yes_bid_size_fp=Decimal("10.00"),
        yes_ask_dollars=Decimal("0.6000"),
        yes_ask_size_fp=Decimal("8.00"),
        no_bid_dollars=Decimal("0.4000"),
        no_bid_size_fp=Decimal("9.00"),
        no_ask_dollars=Decimal("0.4400"),
        no_ask_size_fp=Decimal("7.00"),
        last_price_dollars=Decimal("0.5600"),
        volume_fp=Decimal("1234.00"),
        volume_24h_fp=Decimal("222.50"),
        can_close_early=True,
        fractional_trading_enabled=True,
        open_interest_fp=Decimal("44.00"),
        notional_value_dollars=Decimal("567.89"),
        previous_yes_bid_dollars=Decimal("0.5500"),
        previous_yes_ask_dollars=Decimal("0.5900"),
        previous_no_bid_dollars=Decimal("0.4100"),
        previous_no_ask_dollars=Decimal("0.4500"),
    )


def _market_payload() -> dict[str, object]:
    return {
        "ticker": "ATP-OPEN-001",
        "event_ticker": "ATP-EVENT-001",
        "status": "open",
        "title": "ATP Open Winner",
        "yes_sub_title": "Yes side",
        "no_sub_title": "No side",
        "created_time": "2024-01-01T10:00:00Z",
        "updated_time": "2024-01-01T11:00:00Z",
        "open_time": "2024-01-01T13:00:00Z",
        "close_time": "2024-01-01T18:00:00Z",
        "latest_expiration_time": "2024-01-01T19:00:00Z",
        "settlement_timer_seconds": 120,
        "yes_bid_dollars": "0.5600",
        "yes_bid_size_fp": "10.00",
        "yes_ask_dollars": "0.6000",
        "yes_ask_size_fp": "8.00",
        "no_bid_dollars": "0.4000",
        "no_bid_size_fp": "9.00",
        "no_ask_dollars": "0.4400",
        "no_ask_size_fp": "7.00",
        "last_price_dollars": "0.5600",
        "volume_fp": "1234.00",
        "volume_24h_fp": "222.50",
        "can_close_early": True,
        "fractional_trading_enabled": True,
        "open_interest_fp": "44.00",
        "notional_value_dollars": "567.89",
        "previous_yes_bid_dollars": "0.5500",
        "previous_yes_ask_dollars": "0.5900",
        "previous_no_bid_dollars": "0.4100",
        "previous_no_ask_dollars": "0.4500",
    }


def _columns(connection: duckdb.DuckDBPyConnection, table_name: str) -> tuple[str, ...]:
    return tuple(row[1] for row in connection.execute(
        f"pragma table_info('{table_name}')",
    ).fetchall())
