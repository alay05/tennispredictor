from __future__ import annotations

import base64
import inspect
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import generate_private_key

from tennisprediction.kalshi.client import KalshiReadClient
from tennisprediction.kalshi.schemas import KalshiMarketDTO, KalshiOrderbookDTO


def test_authenticated_requests_include_kalshi_headers_and_valid_rsa_pss_signature() -> None:
    captured = _capture_single_request(
        response_payload={
            "markets": [_market_payload()],
            "cursor": "next-cursor",
        },
    )
    private_key = generate_private_key(public_exponent=65537, key_size=2048)
    client = KalshiReadClient(
        access_key="kalshi-test-key",
        private_key=private_key,
        base_url="https://external-api.demo.kalshi.co/trade-api/v2",
        transport=captured.transport,
        timestamp_provider=lambda: 1703123456789,
    )

    page = client.list_markets(limit=5)

    request = captured.request
    assert request is not None
    assert request.headers["KALSHI-ACCESS-KEY"] == "kalshi-test-key"
    assert request.headers["KALSHI-ACCESS-TIMESTAMP"] == "1703123456789"
    signature = base64.b64decode(request.headers["KALSHI-ACCESS-SIGNATURE"])
    private_key.public_key().verify(
        signature,
        b"1703123456789GET/trade-api/v2/markets",
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    assert page.cursor == "next-cursor"
    assert page.request_metadata.signed_payload == "1703123456789GET/trade-api/v2/markets"


def test_request_signing_uses_the_path_without_the_query_string() -> None:
    captured = _capture_single_request(
        response_payload={
            "markets": [_market_payload()],
            "cursor": None,
        },
    )
    private_key = generate_private_key(public_exponent=65537, key_size=2048)
    client = KalshiReadClient(
        access_key="kalshi-test-key",
        private_key=private_key,
        base_url="https://external-api.demo.kalshi.co",
        transport=captured.transport,
        timestamp_provider=lambda: 1703123456789,
    )

    client.list_markets(limit=5, status="open")

    request = captured.request
    assert request is not None
    signature = base64.b64decode(request.headers["KALSHI-ACCESS-SIGNATURE"])
    public_key = private_key.public_key()
    public_key.verify(
        signature,
        b"1703123456789GET/trade-api/v2/markets",
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    with pytest.raises(InvalidSignature):
        public_key.verify(
            signature,
            b"1703123456789GET/trade-api/v2/markets?limit=5&status=open",
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH,
            ),
            hashes.SHA256(),
        )
    assert request.url.path == "/trade-api/v2/markets"
    assert request.url.params == httpx.QueryParams("limit=5&status=open")


def test_read_methods_return_normalized_project_dtos() -> None:
    captured = _capture_routing_transport()
    private_key = generate_private_key(public_exponent=65537, key_size=2048)
    client = KalshiReadClient(
        access_key="kalshi-test-key",
        private_key=private_key,
        base_url="https://external-api.demo.kalshi.co",
        transport=captured.transport,
        timestamp_provider=lambda: 1703123456789,
    )

    page = client.list_markets(limit=2)
    detail = client.get_market("ATP-OPEN-001")
    orderbook = client.get_market_orderbook("ATP-OPEN-001")

    assert not isinstance(page, dict)
    assert not isinstance(detail, dict)
    assert not isinstance(orderbook, dict)
    assert page.markets and isinstance(page.markets[0], KalshiMarketDTO)
    assert page.markets[0].ticker == "ATP-OPEN-001"
    assert page.markets[0].yes_bid_dollars == Decimal("0.5600")
    assert detail.market.ticker == "ATP-OPEN-001"
    assert detail.market.open_time == datetime(2024, 1, 1, 15, 0, tzinfo=UTC)
    assert isinstance(orderbook, KalshiOrderbookDTO)
    assert orderbook.ticker == "ATP-OPEN-001"
    assert orderbook.yes_levels[0].price_dollars == Decimal("0.1500")
    assert orderbook.no_levels[0].quantity_fp == Decimal("75.00")
    assert orderbook.request_metadata.path == "/trade-api/v2/markets/ATP-OPEN-001/orderbook"


def test_client_public_surface_stays_read_only() -> None:
    public_methods = sorted(
        name
        for name, value in inspect.getmembers(KalshiReadClient, predicate=callable)
        if not name.startswith("_")
    )
    assert public_methods == [
        "close",
        "get_market",
        "get_market_orderbook",
        "list_markets",
    ]

    constructor_params = set(inspect.signature(KalshiReadClient).parameters)
    assert "allow_orders" not in constructor_params
    assert "write_enabled" not in constructor_params
    assert "place_order" not in constructor_params


@dataclass
class _CapturedRequest:
    transport: httpx.MockTransport
    request: httpx.Request | None = None


def _capture_single_request(*, response_payload: dict[str, object]) -> _CapturedRequest:
    captured = _CapturedRequest(
        transport=httpx.MockTransport(
            lambda request: _handle_and_respond(
                request,
                captured,
                response_payload,
            ),
        ),
    )
    return captured


def _capture_routing_transport() -> _CapturedRequest:
    captured = _CapturedRequest(
        transport=httpx.MockTransport(
            lambda request: _dispatch_request(request, captured),
        )
    )
    return captured


def _handle_and_respond(
    request: httpx.Request,
    captured: _CapturedRequest,
    response_payload: dict[str, object],
) -> httpx.Response:
    captured.request = request
    return httpx.Response(200, json=response_payload)


def _dispatch_request(request: httpx.Request, captured: _CapturedRequest) -> httpx.Response:
    captured.request = request
    if request.url.path.endswith("/orderbook"):
        return httpx.Response(
            200,
            json={
                "orderbook_fp": {
                    "yes_dollars": [["0.1500", "100.00"]],
                    "no_dollars": [["0.8500", "75.00"]],
                }
            },
        )
    if request.url.path.endswith("/ATP-OPEN-001"):
        return httpx.Response(
            200,
            json={
                "market": {
                    **_market_payload(),
                    "open_time": "2024-01-01T15:00:00Z",
                }
            },
        )
    return httpx.Response(
        200,
        json={
            "markets": [_market_payload()],
            "cursor": "page-cursor",
        },
    )


def _market_payload() -> dict[str, object]:
    return {
        "ticker": "ATP-OPEN-001",
        "event_ticker": "ATP-EVENT-001",
        "status": "open",
        "title": "ATP match market",
        "yes_sub_title": "Yes side",
        "no_sub_title": "No side",
        "created_time": "2024-01-01T10:00:00Z",
        "updated_time": "2024-01-01T12:00:00Z",
        "open_time": "2024-01-01T13:00:00Z",
        "close_time": "2024-01-01T18:00:00Z",
        "latest_expiration_time": "2024-01-01T19:00:00Z",
        "settlement_timer_seconds": 123,
        "yes_bid_dollars": "0.5600",
        "yes_bid_size_fp": "10.00",
        "yes_ask_dollars": "0.6000",
        "yes_ask_size_fp": "8.00",
        "no_bid_dollars": "0.4000",
        "no_bid_size_fp": "9.00",
        "no_ask_dollars": "0.4400",
        "no_ask_size_fp": "7.00",
        "last_price_dollars": "0.5600",
        "volume_fp": "10.00",
        "volume_24h_fp": "15.00",
        "can_close_early": True,
        "fractional_trading_enabled": True,
        "open_interest_fp": "11.00",
        "notional_value_dollars": "0.5600",
        "previous_yes_bid_dollars": "0.5400",
        "previous_yes_ask_dollars": "0.5800",
        "previous_no_bid_dollars": "0.4200",
        "previous_no_ask_dollars": "0.4600",
    }
