from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from tennisprediction.kalshi.schemas import (
    KalshiMarketDetailDTO,
    KalshiMarketDTO,
    KalshiOrderbookDTO,
    KalshiRequestMetadata,
)

SNAPSHOT_LINEAGE_COLUMNS = (
    "request_id",
    "collected_at_utc",
    "request_method",
    "request_path",
    "request_base_url",
    "request_timestamp_ms",
    "request_signed_payload",
    "request_query_params_json",
    "request_cursor",
    "request_filter_params_json",
    "response_status_code",
    "response_cursor",
    "response_checksum",
)

REQUEST_LOG_COLUMNS = SNAPSHOT_LINEAGE_COLUMNS + ("response_payload_json",)

MARKET_COLUMNS = (
    "response_index",
    "ticker",
    "event_ticker",
    "status",
    "title",
    "yes_sub_title",
    "no_sub_title",
    "created_time",
    "updated_time",
    "open_time",
    "close_time",
    "latest_expiration_time",
    "settlement_timer_seconds",
    "yes_bid_dollars",
    "yes_bid_size_fp",
    "yes_ask_dollars",
    "yes_ask_size_fp",
    "no_bid_dollars",
    "no_bid_size_fp",
    "no_ask_dollars",
    "no_ask_size_fp",
    "last_price_dollars",
    "volume_fp",
    "volume_24h_fp",
    "can_close_early",
    "fractional_trading_enabled",
    "open_interest_fp",
    "notional_value_dollars",
    "previous_yes_bid_dollars",
    "previous_yes_ask_dollars",
    "previous_no_bid_dollars",
    "previous_no_ask_dollars",
)

MARKET_SNAPSHOT_COLUMNS = SNAPSHOT_LINEAGE_COLUMNS + MARKET_COLUMNS
MARKET_DETAIL_SNAPSHOT_COLUMNS = MARKET_SNAPSHOT_COLUMNS

ORDERBOOK_COLUMNS = (
    "response_index",
    "ticker",
    "yes_levels_json",
    "no_levels_json",
    "yes_level_count",
    "no_level_count",
    "yes_best_price_dollars",
    "yes_best_quantity_fp",
    "no_best_price_dollars",
    "no_best_quantity_fp",
)

ORDERBOOK_SNAPSHOT_COLUMNS = SNAPSHOT_LINEAGE_COLUMNS + ORDERBOOK_COLUMNS

_CONTROL_QUERY_PARAM_KEYS = {"limit", "cursor"}


@dataclass(frozen=True)
class KalshiRequestLogRow:
    request_id: str
    collected_at_utc: datetime
    request_method: str
    request_path: str
    request_base_url: str
    request_timestamp_ms: int
    request_signed_payload: str
    request_query_params_json: str
    request_cursor: str | None
    request_filter_params_json: str
    response_status_code: int
    response_cursor: str | None
    response_checksum: str
    response_payload_json: str


@dataclass(frozen=True)
class _KalshiMarketSnapshotBase:
    request_id: str
    collected_at_utc: datetime
    request_method: str
    request_path: str
    request_base_url: str
    request_timestamp_ms: int
    request_signed_payload: str
    request_query_params_json: str
    request_cursor: str | None
    request_filter_params_json: str
    response_status_code: int
    response_cursor: str | None
    response_checksum: str
    response_index: int
    ticker: str
    event_ticker: str
    status: str | None
    title: str | None
    yes_sub_title: str | None
    no_sub_title: str | None
    created_time: datetime | None
    updated_time: datetime | None
    open_time: datetime | None
    close_time: datetime | None
    latest_expiration_time: datetime | None
    settlement_timer_seconds: int | None
    yes_bid_dollars: Decimal | None
    yes_bid_size_fp: Decimal | None
    yes_ask_dollars: Decimal | None
    yes_ask_size_fp: Decimal | None
    no_bid_dollars: Decimal | None
    no_bid_size_fp: Decimal | None
    no_ask_dollars: Decimal | None
    no_ask_size_fp: Decimal | None
    last_price_dollars: Decimal | None
    volume_fp: Decimal | None
    volume_24h_fp: Decimal | None
    can_close_early: bool | None
    fractional_trading_enabled: bool | None
    open_interest_fp: Decimal | None
    notional_value_dollars: Decimal | None
    previous_yes_bid_dollars: Decimal | None
    previous_yes_ask_dollars: Decimal | None
    previous_no_bid_dollars: Decimal | None
    previous_no_ask_dollars: Decimal | None


@dataclass(frozen=True)
class KalshiMarketSnapshotRow(_KalshiMarketSnapshotBase):
    pass


@dataclass(frozen=True)
class KalshiMarketDetailSnapshotRow(_KalshiMarketSnapshotBase):
    pass


@dataclass(frozen=True)
class KalshiOrderbookSnapshotRow:
    request_id: str
    collected_at_utc: datetime
    request_method: str
    request_path: str
    request_base_url: str
    request_timestamp_ms: int
    request_signed_payload: str
    request_query_params_json: str
    request_cursor: str | None
    request_filter_params_json: str
    response_status_code: int
    response_cursor: str | None
    response_checksum: str
    response_index: int
    ticker: str
    yes_levels_json: str
    no_levels_json: str
    yes_level_count: int
    no_level_count: int
    yes_best_price_dollars: Decimal | None
    yes_best_quantity_fp: Decimal | None
    no_best_price_dollars: Decimal | None
    no_best_quantity_fp: Decimal | None


@dataclass(frozen=True)
class KalshiSnapshotBatch:
    request_logs: tuple[KalshiRequestLogRow, ...]
    market_snapshots: tuple[KalshiMarketSnapshotRow, ...]
    market_detail_snapshots: tuple[KalshiMarketDetailSnapshotRow, ...]
    orderbook_snapshots: tuple[KalshiOrderbookSnapshotRow, ...]


def build_request_log_row(
    request_metadata: KalshiRequestMetadata,
    *,
    response_status_code: int,
    response_payload: object | None = None,
    response_payload_json: str | None = None,
    response_cursor: str | None = None,
    collected_at_utc: datetime | None = None,
) -> KalshiRequestLogRow:
    payload_json = _canonical_payload_json(
        payload=response_payload,
        payload_json=response_payload_json,
    )
    checksum = _sha256_hex(payload_json)
    normalized_collected_at = _normalize_utc_naive(collected_at_utc)
    request_cursor = _query_param_value(request_metadata.query_params, "cursor")
    request_query_params_json = _canonical_json(list(request_metadata.query_params))
    request_filter_params_json = _canonical_json(
        {
            key: value
            for key, value in request_metadata.query_params
            if key not in _CONTROL_QUERY_PARAM_KEYS
        }
    )
    request_id = _request_id(
        request_metadata=request_metadata,
        collected_at_utc=normalized_collected_at,
        response_status_code=response_status_code,
        response_cursor=response_cursor,
        response_checksum=checksum,
    )
    return KalshiRequestLogRow(
        request_id=request_id,
        collected_at_utc=normalized_collected_at,
        request_method=request_metadata.method,
        request_path=request_metadata.path,
        request_base_url=request_metadata.base_url,
        request_timestamp_ms=request_metadata.timestamp_ms,
        request_signed_payload=request_metadata.signed_payload,
        request_query_params_json=request_query_params_json,
        request_cursor=request_cursor,
        request_filter_params_json=request_filter_params_json,
        response_status_code=response_status_code,
        response_cursor=response_cursor,
        response_checksum=checksum,
        response_payload_json=payload_json,
    )


def build_market_snapshot_row(
    request_log_row: KalshiRequestLogRow,
    market: KalshiMarketDTO,
    *,
    response_index: int,
) -> KalshiMarketSnapshotRow:
    return KalshiMarketSnapshotRow(
        **_request_log_kwargs(request_log_row),
        response_index=response_index,
        **_market_kwargs(market),
    )


def build_market_detail_snapshot_row(
    request_log_row: KalshiRequestLogRow,
    market_detail: KalshiMarketDetailDTO,
    *,
    response_index: int = 0,
) -> KalshiMarketDetailSnapshotRow:
    return KalshiMarketDetailSnapshotRow(
        **_request_log_kwargs(request_log_row),
        response_index=response_index,
        **_market_kwargs(market_detail.market),
    )


def build_orderbook_snapshot_row(
    request_log_row: KalshiRequestLogRow,
    orderbook: KalshiOrderbookDTO,
    *,
    response_index: int = 0,
) -> KalshiOrderbookSnapshotRow:
    yes_levels = tuple(orderbook.yes_levels)
    no_levels = tuple(orderbook.no_levels)
    return KalshiOrderbookSnapshotRow(
        **_request_log_kwargs(request_log_row),
        response_index=response_index,
        ticker=orderbook.ticker,
        yes_levels_json=_canonical_json([asdict(level) for level in yes_levels]),
        no_levels_json=_canonical_json([asdict(level) for level in no_levels]),
        yes_level_count=len(yes_levels),
        no_level_count=len(no_levels),
        yes_best_price_dollars=(yes_levels[0].price_dollars if yes_levels else None),
        yes_best_quantity_fp=(yes_levels[0].quantity_fp if yes_levels else None),
        no_best_price_dollars=(no_levels[0].price_dollars if no_levels else None),
        no_best_quantity_fp=(no_levels[0].quantity_fp if no_levels else None),
    )


def _request_log_kwargs(request_log_row: KalshiRequestLogRow) -> dict[str, Any]:
    return {
        "request_id": request_log_row.request_id,
        "collected_at_utc": request_log_row.collected_at_utc,
        "request_method": request_log_row.request_method,
        "request_path": request_log_row.request_path,
        "request_base_url": request_log_row.request_base_url,
        "request_timestamp_ms": request_log_row.request_timestamp_ms,
        "request_signed_payload": request_log_row.request_signed_payload,
        "request_query_params_json": request_log_row.request_query_params_json,
        "request_cursor": request_log_row.request_cursor,
        "request_filter_params_json": request_log_row.request_filter_params_json,
        "response_status_code": request_log_row.response_status_code,
        "response_cursor": request_log_row.response_cursor,
        "response_checksum": request_log_row.response_checksum,
    }


def _market_kwargs(market: KalshiMarketDTO) -> dict[str, Any]:
    return {
        "ticker": market.ticker,
        "event_ticker": market.event_ticker,
        "status": market.status,
        "title": market.title,
        "yes_sub_title": market.yes_sub_title,
        "no_sub_title": market.no_sub_title,
        "created_time": _normalize_utc_naive(market.created_time),
        "updated_time": _normalize_utc_naive(market.updated_time),
        "open_time": _normalize_utc_naive(market.open_time),
        "close_time": _normalize_utc_naive(market.close_time),
        "latest_expiration_time": _normalize_utc_naive(market.latest_expiration_time),
        "settlement_timer_seconds": market.settlement_timer_seconds,
        "yes_bid_dollars": market.yes_bid_dollars,
        "yes_bid_size_fp": market.yes_bid_size_fp,
        "yes_ask_dollars": market.yes_ask_dollars,
        "yes_ask_size_fp": market.yes_ask_size_fp,
        "no_bid_dollars": market.no_bid_dollars,
        "no_bid_size_fp": market.no_bid_size_fp,
        "no_ask_dollars": market.no_ask_dollars,
        "no_ask_size_fp": market.no_ask_size_fp,
        "last_price_dollars": market.last_price_dollars,
        "volume_fp": market.volume_fp,
        "volume_24h_fp": market.volume_24h_fp,
        "can_close_early": market.can_close_early,
        "fractional_trading_enabled": market.fractional_trading_enabled,
        "open_interest_fp": market.open_interest_fp,
        "notional_value_dollars": market.notional_value_dollars,
        "previous_yes_bid_dollars": market.previous_yes_bid_dollars,
        "previous_yes_ask_dollars": market.previous_yes_ask_dollars,
        "previous_no_bid_dollars": market.previous_no_bid_dollars,
        "previous_no_ask_dollars": market.previous_no_ask_dollars,
    }


def _request_id(
    *,
    request_metadata: KalshiRequestMetadata,
    collected_at_utc: datetime,
    response_status_code: int,
    response_cursor: str | None,
    response_checksum: str,
) -> str:
    payload = {
        "request": {
            "method": request_metadata.method,
            "path": request_metadata.path,
            "base_url": request_metadata.base_url,
            "timestamp_ms": request_metadata.timestamp_ms,
            "signed_payload": request_metadata.signed_payload,
            "query_params": list(request_metadata.query_params),
        },
        "response": {
            "status_code": response_status_code,
            "cursor": response_cursor,
            "checksum": response_checksum,
        },
        "collected_at_utc": collected_at_utc.isoformat(timespec="microseconds"),
    }
    return _sha256_hex(_canonical_json(payload))


def _query_param_value(
    query_params: tuple[tuple[str, str], ...],
    key: str,
) -> str | None:
    for candidate_key, candidate_value in query_params:
        if candidate_key == key:
            return candidate_value
    return None


def _canonical_payload_json(
    *,
    payload: object | None,
    payload_json: str | None,
) -> str:
    if payload_json is not None:
        return payload_json
    if payload is None:
        msg = "response_payload or response_payload_json is required"
        raise ValueError(msg)
    return _canonical_json(payload)


def _canonical_json(value: object) -> str:
    return json.dumps(
        _json_safe(value),
        sort_keys=True,
        separators=(",", ":"),
    )


def _json_safe(value: object) -> object:
    if is_dataclass(value):
        return _json_safe(cast(Any, asdict(cast(Any, value))))
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        return _normalize_utc_naive(value).isoformat(timespec="microseconds")
    return value


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _normalize_utc_naive(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(tz=UTC).replace(tzinfo=None)
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)
