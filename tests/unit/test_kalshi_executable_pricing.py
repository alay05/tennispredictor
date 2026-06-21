from __future__ import annotations

import json
from datetime import datetime
from decimal import Decimal

import pytest

from tennisprediction.kalshi.executable import derive_executable_market_input
from tennisprediction.kalshi.snapshots import KalshiOrderbookSnapshotRow
from tennisprediction.market_mapping.schemas import (
    MappingConfidenceTier,
    MarketMappingEvidenceRow,
    MarketMappingState,
)


def test_derive_executable_market_input_uses_reciprocal_bid_ladders_and_top_of_book_notional(
) -> None:
    collected_at = datetime(2024, 6, 20, 14, 0, 0)
    evaluated_at = datetime(2024, 6, 20, 14, 0, 45)
    market_input = derive_executable_market_input(
        orderbook_row=_orderbook_snapshot_row(
            collected_at_utc=collected_at,
            yes_levels=((Decimal("0.37"), Decimal("3")),),
            no_levels=((Decimal("0.41"), Decimal("7")),),
        ),
        mapping_row=_mapping_row(),
        evaluated_at_utc=evaluated_at,
    )

    assert market_input.canonical_match_id == "match:queens:r16:fritz-tiafoe"
    assert market_input.market_ticker == "KXATP-001"
    assert market_input.positive_side == "yes"
    assert market_input.negative_side == "no"

    assert market_input.yes_side.entry_price == pytest.approx(0.59)
    assert market_input.yes_side.entry_price_source == "reciprocal_no_bid_top_of_book"
    assert market_input.yes_side.available_liquidity_dollars == pytest.approx(4.13)
    assert (
        market_input.yes_side.liquidity_source
        == "top_of_book_notional_from_no_bid_quantity"
    )
    assert market_input.yes_side.freshness_age_seconds == pytest.approx(45.0)
    assert market_input.yes_side.freshness_source == "orderbook_collected_at_utc"
    assert market_input.yes_side.rejection_reason_codes == ()

    assert market_input.no_side.entry_price == pytest.approx(0.63)
    assert market_input.no_side.entry_price_source == "reciprocal_yes_bid_top_of_book"
    assert market_input.no_side.available_liquidity_dollars == pytest.approx(1.89)
    assert (
        market_input.no_side.liquidity_source
        == "top_of_book_notional_from_yes_bid_quantity"
    )
    assert market_input.no_side.freshness_age_seconds == pytest.approx(45.0)
    assert market_input.no_side.freshness_source == "orderbook_collected_at_utc"
    assert market_input.no_side.rejection_reason_codes == ()


@pytest.mark.parametrize(
    ("yes_levels", "no_levels", "evaluated_at", "expected_yes_reasons", "expected_no_reasons"),
    [
        (
            ((Decimal("0.30"), Decimal("5")),),
            (),
            datetime(2024, 6, 20, 14, 0, 30),
            ("missing_executable_price",),
            (),
        ),
        (
            ((Decimal("0.30"), Decimal("0")),),
            ((Decimal("0.42"), Decimal("5")),),
            datetime(2024, 6, 20, 14, 0, 30),
            (),
            ("missing_executable_liquidity",),
        ),
        (
            ((Decimal("0.30"), Decimal("5")),),
            ((Decimal("0.42"), Decimal("5")),),
            datetime(2024, 6, 20, 14, 2, 5),
            ("stale_orderbook",),
            ("stale_orderbook",),
        ),
    ],
)
def test_derive_executable_market_input_marks_unscorable_sides_explicitly(
    yes_levels: tuple[tuple[Decimal, Decimal], ...],
    no_levels: tuple[tuple[Decimal, Decimal], ...],
    evaluated_at: datetime,
    expected_yes_reasons: tuple[str, ...],
    expected_no_reasons: tuple[str, ...],
) -> None:
    market_input = derive_executable_market_input(
        orderbook_row=_orderbook_snapshot_row(
            collected_at_utc=datetime(2024, 6, 20, 14, 0, 0),
            yes_levels=yes_levels,
            no_levels=no_levels,
        ),
        mapping_row=_mapping_row(),
        evaluated_at_utc=evaluated_at,
    )

    assert market_input.yes_side.rejection_reason_codes == expected_yes_reasons
    assert market_input.no_side.rejection_reason_codes == expected_no_reasons


def _orderbook_snapshot_row(
    *,
    collected_at_utc: datetime,
    yes_levels: tuple[tuple[Decimal, Decimal], ...],
    no_levels: tuple[tuple[Decimal, Decimal], ...],
) -> KalshiOrderbookSnapshotRow:
    return KalshiOrderbookSnapshotRow(
        request_id="request-001",
        collected_at_utc=collected_at_utc,
        request_method="GET",
        request_path="/trade-api/v2/markets/KXATP-001/orderbook",
        request_base_url="https://demo-api.kalshi.co",
        request_timestamp_ms=1718892000000,
        request_signed_payload="fixture-signature",
        request_query_params_json="[]",
        request_cursor=None,
        request_filter_params_json="{}",
        response_status_code=200,
        response_cursor=None,
        response_checksum="checksum-001",
        response_index=0,
        ticker="KXATP-001",
        yes_levels_json=_level_json(yes_levels),
        no_levels_json=_level_json(no_levels),
        yes_level_count=len(yes_levels),
        no_level_count=len(no_levels),
        yes_best_price_dollars=yes_levels[0][0] if yes_levels else None,
        yes_best_quantity_fp=yes_levels[0][1] if yes_levels else None,
        no_best_price_dollars=no_levels[0][0] if no_levels else None,
        no_best_quantity_fp=no_levels[0][1] if no_levels else None,
    )


def _mapping_row() -> MarketMappingEvidenceRow:
    return MarketMappingEvidenceRow(
        market_ticker="KXATP-001",
        event_ticker="KXATP-EVT-001",
        collected_at_utc=datetime(2024, 6, 20, 14, 0, 0),
        raw_title="ATP Queen's Club: Taylor Fritz vs Frances Tiafoe",
        raw_yes_sub_title="Taylor Fritz",
        raw_no_sub_title="Frances Tiafoe",
        normalized_yes_player_name="taylor fritz",
        normalized_no_player_name="frances tiafoe",
        alias_hit_player_ids=(),
        candidate_canonical_match_ids=("match:queens:r16:fritz-tiafoe",),
        mapping_state=MarketMappingState.matched,
        mapping_confidence=MappingConfidenceTier.exact_names,
        canonical_match_id="match:queens:r16:fritz-tiafoe",
        yes_canonical_player_id="player:fritz",
        no_canonical_player_id="player:tiafoe",
        yes_maps_to_player_a=True,
        no_maps_to_player_b=True,
        rejection_reason_codes=(),
    )


def _level_json(levels: tuple[tuple[Decimal, Decimal], ...]) -> str:
    return json.dumps(
        [
            {
                "price_dollars": str(price_dollars),
                "quantity_fp": str(quantity_fp),
            }
            for price_dollars, quantity_fp in levels
        ],
        sort_keys=True,
        separators=(",", ":"),
    )
