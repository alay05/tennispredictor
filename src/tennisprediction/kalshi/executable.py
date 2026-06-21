from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    ExecutableMarketInput,
    ExecutableSideInput,
)
from tennisprediction.kalshi.snapshots import KalshiOrderbookSnapshotRow
from tennisprediction.market_mapping.schemas import MarketMappingEvidenceRow

_DEFAULT_STALE_AFTER_SECONDS = 120.0


@dataclass(frozen=True)
class _OrderbookLevel:
    price_dollars: Decimal
    quantity_fp: Decimal


def derive_executable_market_input(
    *,
    orderbook_row: KalshiOrderbookSnapshotRow,
    mapping_row: MarketMappingEvidenceRow,
    evaluated_at_utc: datetime,
    stale_after_seconds: float = _DEFAULT_STALE_AFTER_SECONDS,
) -> ExecutableMarketInput:
    if mapping_row.canonical_match_id is None:
        msg = "mapping row must be matched before executable pricing"
        raise ValueError(msg)

    yes_levels = _load_levels(orderbook_row.yes_levels_json)
    no_levels = _load_levels(orderbook_row.no_levels_json)
    freshness_age_seconds = (
        evaluated_at_utc - orderbook_row.collected_at_utc
    ).total_seconds()
    stale = freshness_age_seconds > stale_after_seconds

    yes_side = _build_side_input(
        kalshi_side="yes",
        canonical_player_id=mapping_row.yes_canonical_player_id,
        maps_to_player_a=mapping_row.yes_maps_to_player_a,
        opposing_levels=no_levels,
        entry_price_source="reciprocal_no_bid_top_of_book",
        liquidity_source="top_of_book_notional_from_no_bid_quantity",
        freshness_age_seconds=freshness_age_seconds,
        stale=stale,
    )
    no_side = _build_side_input(
        kalshi_side="no",
        canonical_player_id=mapping_row.no_canonical_player_id,
        maps_to_player_a=(
            None if mapping_row.no_maps_to_player_b is None else not mapping_row.no_maps_to_player_b
        ),
        opposing_levels=yes_levels,
        entry_price_source="reciprocal_yes_bid_top_of_book",
        liquidity_source="top_of_book_notional_from_yes_bid_quantity",
        freshness_age_seconds=freshness_age_seconds,
        stale=stale,
    )

    positive_side: Literal["yes", "no"] = "yes"
    negative_side: Literal["yes", "no"] = "no"
    if mapping_row.yes_maps_to_player_a is False:
        positive_side = "no"
        negative_side = "yes"

    return ExecutableMarketInput(
        canonical_match_id=mapping_row.canonical_match_id,
        market_ticker=orderbook_row.ticker,
        positive_side=positive_side,
        negative_side=negative_side,
        yes_side=yes_side,
        no_side=no_side,
        provenance_label=BacktestProvenanceLabel.collected_snapshot_replay,
        assumption_notes="top-of-book executable pricing",
    )


def _build_side_input(
    *,
    kalshi_side: Literal["yes", "no"],
    canonical_player_id: str | None,
    maps_to_player_a: bool | None,
    opposing_levels: tuple[_OrderbookLevel, ...],
    entry_price_source: str,
    liquidity_source: str,
    freshness_age_seconds: float,
    stale: bool,
) -> ExecutableSideInput:
    reason_codes: list[str] = []
    entry_price: float | None = None
    available_liquidity_dollars: float | None = None

    if not opposing_levels:
        reason_codes.append("missing_executable_price")
    else:
        top_level = opposing_levels[0]
        entry_price = float(Decimal("1") - top_level.price_dollars)
        if top_level.quantity_fp <= 0:
            available_liquidity_dollars = 0.0
            reason_codes.append("missing_executable_liquidity")
        else:
            available_liquidity_dollars = float(entry_price * float(top_level.quantity_fp))

    if stale:
        reason_codes.append("stale_orderbook")

    return ExecutableSideInput(
        kalshi_side=kalshi_side,
        canonical_player_id=canonical_player_id,
        maps_to_player_a=maps_to_player_a,
        entry_price=entry_price,
        entry_price_source=entry_price_source,
        available_liquidity_dollars=available_liquidity_dollars,
        liquidity_source=liquidity_source,
        freshness_age_seconds=freshness_age_seconds,
        freshness_source="orderbook_collected_at_utc",
        rejection_reason_codes=tuple(reason_codes),
    )


def _load_levels(levels_json: str) -> tuple[_OrderbookLevel, ...]:
    raw_levels = json.loads(levels_json)
    if not isinstance(raw_levels, list):
        msg = "orderbook levels json must decode to a list"
        raise ValueError(msg)
    return tuple(_build_level(level) for level in raw_levels)


def _build_level(value: Any) -> _OrderbookLevel:
    if not isinstance(value, dict):
        msg = "orderbook level must be an object"
        raise ValueError(msg)
    return _OrderbookLevel(
        price_dollars=Decimal(str(value["price_dollars"])),
        quantity_fp=Decimal(str(value["quantity_fp"])),
    )
