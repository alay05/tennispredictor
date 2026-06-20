from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass(frozen=True)
class KalshiRequestMetadata:
    method: str
    path: str
    query_params: tuple[tuple[str, str], ...]
    timestamp_ms: int
    base_url: str
    signed_payload: str


@dataclass(frozen=True)
class KalshiMarketDTO:
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
class KalshiMarketDetailDTO:
    market: KalshiMarketDTO
    request_metadata: KalshiRequestMetadata


@dataclass(frozen=True)
class KalshiOrderbookLevelDTO:
    price_dollars: Decimal
    quantity_fp: Decimal


@dataclass(frozen=True)
class KalshiOrderbookDTO:
    ticker: str
    yes_levels: tuple[KalshiOrderbookLevelDTO, ...]
    no_levels: tuple[KalshiOrderbookLevelDTO, ...]
    request_metadata: KalshiRequestMetadata


@dataclass(frozen=True)
class KalshiMarketPageDTO:
    markets: tuple[KalshiMarketDTO, ...]
    cursor: str | None
    request_metadata: KalshiRequestMetadata
