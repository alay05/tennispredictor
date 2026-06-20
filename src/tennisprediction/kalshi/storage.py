from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import duckdb

from tennisprediction.config import Settings, get_settings
from tennisprediction.kalshi.snapshots import (
    MARKET_DETAIL_SNAPSHOT_COLUMNS,
    MARKET_SNAPSHOT_COLUMNS,
    ORDERBOOK_SNAPSHOT_COLUMNS,
    REQUEST_LOG_COLUMNS,
    KalshiMarketDetailSnapshotRow,
    KalshiMarketSnapshotRow,
    KalshiOrderbookSnapshotRow,
    KalshiRequestLogRow,
    KalshiSnapshotBatch,
)
from tennisprediction.storage.duckdb import _replace_table

_REQUEST_LOG_TABLE = "kalshi_request_logs"
_MARKET_SNAPSHOT_TABLE = "kalshi_market_snapshots"
_MARKET_DETAIL_SNAPSHOT_TABLE = "kalshi_market_detail_snapshots"
_ORDERBOOK_SNAPSHOT_TABLE = "kalshi_orderbook_snapshots"

_REQUEST_LOG_SCHEMA = (
    ("request_id", "varchar"),
    ("collected_at_utc", "timestamp"),
    ("request_method", "varchar"),
    ("request_path", "varchar"),
    ("request_base_url", "varchar"),
    ("request_timestamp_ms", "bigint"),
    ("request_signed_payload", "varchar"),
    ("request_query_params_json", "varchar"),
    ("request_cursor", "varchar"),
    ("request_filter_params_json", "varchar"),
    ("response_status_code", "integer"),
    ("response_cursor", "varchar"),
    ("response_checksum", "varchar"),
    ("response_payload_json", "varchar"),
)

_MARKET_SCHEMA = _REQUEST_LOG_SCHEMA[:-1] + (
    ("response_index", "integer"),
    ("ticker", "varchar"),
    ("event_ticker", "varchar"),
    ("status", "varchar"),
    ("title", "varchar"),
    ("yes_sub_title", "varchar"),
    ("no_sub_title", "varchar"),
    ("created_time", "timestamp"),
    ("updated_time", "timestamp"),
    ("open_time", "timestamp"),
    ("close_time", "timestamp"),
    ("latest_expiration_time", "timestamp"),
    ("settlement_timer_seconds", "integer"),
    ("yes_bid_dollars", "decimal(18,4)"),
    ("yes_bid_size_fp", "decimal(18,4)"),
    ("yes_ask_dollars", "decimal(18,4)"),
    ("yes_ask_size_fp", "decimal(18,4)"),
    ("no_bid_dollars", "decimal(18,4)"),
    ("no_bid_size_fp", "decimal(18,4)"),
    ("no_ask_dollars", "decimal(18,4)"),
    ("no_ask_size_fp", "decimal(18,4)"),
    ("last_price_dollars", "decimal(18,4)"),
    ("volume_fp", "decimal(18,4)"),
    ("volume_24h_fp", "decimal(18,4)"),
    ("can_close_early", "boolean"),
    ("fractional_trading_enabled", "boolean"),
    ("open_interest_fp", "decimal(18,4)"),
    ("notional_value_dollars", "decimal(18,4)"),
    ("previous_yes_bid_dollars", "decimal(18,4)"),
    ("previous_yes_ask_dollars", "decimal(18,4)"),
    ("previous_no_bid_dollars", "decimal(18,4)"),
    ("previous_no_ask_dollars", "decimal(18,4)"),
)

_ORDERBOOK_SCHEMA = _REQUEST_LOG_SCHEMA[:-1] + (
    ("response_index", "integer"),
    ("ticker", "varchar"),
    ("yes_levels_json", "varchar"),
    ("no_levels_json", "varchar"),
    ("yes_level_count", "integer"),
    ("no_level_count", "integer"),
    ("yes_best_price_dollars", "decimal(18,4)"),
    ("yes_best_quantity_fp", "decimal(18,4)"),
    ("no_best_price_dollars", "decimal(18,4)"),
    ("no_best_quantity_fp", "decimal(18,4)"),
)

_TABLE_SCHEMAS = {
    _REQUEST_LOG_TABLE: _REQUEST_LOG_SCHEMA,
    _MARKET_SNAPSHOT_TABLE: _MARKET_SCHEMA,
    _MARKET_DETAIL_SNAPSHOT_TABLE: _MARKET_SCHEMA,
    _ORDERBOOK_SNAPSHOT_TABLE: _ORDERBOOK_SCHEMA,
}

def persist_kalshi_snapshot_batch(
    batch: KalshiSnapshotBatch,
    *,
    database_path: str | Path | None = None,
) -> Path:
    database_file = _resolve_database_path(database_path)
    database_file.parent.mkdir(parents=True, exist_ok=True)

    connection = duckdb.connect(str(database_file))
    try:
        _replace_table(
            connection,
            table_name=_REQUEST_LOG_TABLE,
            rows=_rows_as_dicts(batch.request_logs),
            ddl=_ddl_for_table(_REQUEST_LOG_TABLE),
        )
        _replace_table(
            connection,
            table_name=_MARKET_SNAPSHOT_TABLE,
            rows=_rows_as_dicts(batch.market_snapshots),
            ddl=_ddl_for_table(_MARKET_SNAPSHOT_TABLE),
        )
        _replace_table(
            connection,
            table_name=_MARKET_DETAIL_SNAPSHOT_TABLE,
            rows=_rows_as_dicts(batch.market_detail_snapshots),
            ddl=_ddl_for_table(_MARKET_DETAIL_SNAPSHOT_TABLE),
        )
        _replace_table(
            connection,
            table_name=_ORDERBOOK_SNAPSHOT_TABLE,
            rows=_rows_as_dicts(batch.orderbook_snapshots),
            ddl=_ddl_for_table(_ORDERBOOK_SNAPSHOT_TABLE),
        )
    finally:
        connection.close()

    return database_file


def load_kalshi_snapshot_tables(
    *,
    database_path: str | Path | None = None,
) -> KalshiSnapshotBatch:
    database_file = _resolve_database_path(database_path)
    if not database_file.exists():
        raise FileNotFoundError(database_file)
    if not database_file.is_file():
        msg = "Kalshi snapshot database path must be a file"
        raise ValueError(msg)

    connection = duckdb.connect(str(database_file))
    try:
        request_logs = _load_rows(
            connection,
            table_name=_REQUEST_LOG_TABLE,
            row_type=KalshiRequestLogRow,
            expected_columns=REQUEST_LOG_COLUMNS,
        )
        market_snapshots = _load_rows(
            connection,
            table_name=_MARKET_SNAPSHOT_TABLE,
            row_type=KalshiMarketSnapshotRow,
            expected_columns=MARKET_SNAPSHOT_COLUMNS,
        )
        market_detail_snapshots = _load_rows(
            connection,
            table_name=_MARKET_DETAIL_SNAPSHOT_TABLE,
            row_type=KalshiMarketDetailSnapshotRow,
            expected_columns=MARKET_DETAIL_SNAPSHOT_COLUMNS,
        )
        orderbook_snapshots = _load_rows(
            connection,
            table_name=_ORDERBOOK_SNAPSHOT_TABLE,
            row_type=KalshiOrderbookSnapshotRow,
            expected_columns=ORDERBOOK_SNAPSHOT_COLUMNS,
        )
    finally:
        connection.close()

    return KalshiSnapshotBatch(
        request_logs=tuple(request_logs),
        market_snapshots=tuple(market_snapshots),
        market_detail_snapshots=tuple(market_detail_snapshots),
        orderbook_snapshots=tuple(orderbook_snapshots),
    )


def _resolve_database_path(database_path: str | Path | None) -> Path:
    settings = get_settings()
    if database_path is None:
        return settings.duckdb_path
    return Settings._resolve_repo_path(Path(database_path))


def _rows_as_dicts(rows: tuple[Any, ...]) -> list[dict[str, Any]]:
    return [asdict(cast(Any, row)) for row in rows]


def _load_rows(
    connection: duckdb.DuckDBPyConnection,
    *,
    table_name: str,
    row_type: type[Any],
    expected_columns: tuple[str, ...],
) -> list[Any]:
    _validate_table_columns(
        connection,
        table_name=table_name,
        expected_columns=expected_columns,
    )
    column_list = ", ".join(expected_columns)
    records = connection.execute(
        f"select {column_list} from {table_name}",
    ).fetchall()
    return [
        row_type(**dict(zip(expected_columns, record, strict=True)))
        for record in records
    ]


def _ddl_for_table(table_name: str) -> str:
    schema = _TABLE_SCHEMAS[table_name]
    column_block = ",\n                    ".join(
        f"{column_name} {column_type}" for column_name, column_type in schema
    )
    return f"""
                create table {table_name} (
                    {column_block}
                )
            """


def _validate_table_columns(
    connection: duckdb.DuckDBPyConnection,
    *,
    table_name: str,
    expected_columns: tuple[str, ...],
) -> None:
    actual_columns = tuple(
        row[1]
        for row in connection.execute(
            f"pragma table_info('{table_name}')",
        ).fetchall()
    )
    if actual_columns != expected_columns:
        msg = (
            f"{table_name} schema drifted: expected {expected_columns}, "
            f"found {actual_columns}"
        )
        raise ValueError(msg)
