from __future__ import annotations

import base64
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal, cast

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey

from tennisprediction.config import Settings, get_settings
from tennisprediction.kalshi.schemas import (
    KalshiMarketDetailDTO,
    KalshiMarketDTO,
    KalshiMarketPageDTO,
    KalshiOrderbookDTO,
    KalshiOrderbookLevelDTO,
    KalshiRequestMetadata,
)

KALSHI_API_PATH_PREFIX = "/trade-api/v2"
KALSHI_PROD_HOST = "https://external-api.kalshi.com"
KALSHI_DEMO_HOST = "https://external-api.demo.kalshi.co"
KALSHI_ACCESS_KEY_HEADER = "KALSHI-ACCESS-KEY"
KALSHI_ACCESS_TIMESTAMP_HEADER = "KALSHI-ACCESS-TIMESTAMP"
KALSHI_ACCESS_SIGNATURE_HEADER = "KALSHI-ACCESS-SIGNATURE"
AllowedMarketStatus = Literal["unopened", "open", "paused", "closed", "settled"]
AllowedMveFilter = Literal["only", "exclude"]


@dataclass(frozen=True)
class KalshiRequestError(RuntimeError):
    status_code: int
    method: str
    path: str
    response_text: str

    def __str__(self) -> str:
        return (
            f"Kalshi request failed with status {self.status_code} for "
            f"{self.method} {self.path}: {self.response_text}"
        )


class KalshiReadClient:
    def __init__(
        self,
        *,
        access_key: str,
        private_key: RSAPrivateKey | str | Path,
        settings: Settings | None = None,
        base_url: str | None = None,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 10.0,
        timestamp_provider: Callable[[], int] | None = None,
    ) -> None:
        self._settings = settings or get_settings()
        self._access_key = access_key
        self._private_key = _load_private_key(private_key)
        self._base_url = _normalize_base_url(
            base_url or _default_base_url(self._settings),
        )
        self._timestamp_provider = timestamp_provider or _current_timestamp_ms
        self._client = httpx.Client(
            base_url=self._base_url,
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def list_markets(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        tickers: Sequence[str] | None = None,
        min_created_ts: int | None = None,
        max_created_ts: int | None = None,
        min_updated_ts: int | None = None,
        min_close_ts: int | None = None,
        max_close_ts: int | None = None,
        min_settled_ts: int | None = None,
        max_settled_ts: int | None = None,
        status: AllowedMarketStatus | None = None,
        mve_filter: AllowedMveFilter | None = None,
    ) -> KalshiMarketPageDTO:
        params = _build_market_query_params(
            limit=limit,
            cursor=cursor,
            event_ticker=event_ticker,
            series_ticker=series_ticker,
            tickers=tickers,
            min_created_ts=min_created_ts,
            max_created_ts=max_created_ts,
            min_updated_ts=min_updated_ts,
            min_close_ts=min_close_ts,
            max_close_ts=max_close_ts,
            min_settled_ts=min_settled_ts,
            max_settled_ts=max_settled_ts,
            status=status,
            mve_filter=mve_filter,
        )
        payload, metadata = self._request_json(
            "GET",
            _api_path("markets"),
            params=params,
        )
        markets_payload = payload.get("markets")
        if not isinstance(markets_payload, list):
            msg = "Kalshi markets response did not include a markets list"
            raise KalshiRequestError(
                status_code=200,
                method="GET",
                path=_api_path("markets"),
                response_text=msg,
            )

        markets = tuple(
            _normalize_market(record) for record in markets_payload if isinstance(record, Mapping)
        )
        cursor_value = payload.get("cursor")
        if cursor_value is not None and not isinstance(cursor_value, str):
            msg = "Kalshi cursor must be a string when present"
            raise KalshiRequestError(
                status_code=200,
                method="GET",
                path=_api_path("markets"),
                response_text=msg,
            )

        return KalshiMarketPageDTO(
            markets=markets,
            cursor=cursor_value,
            request_metadata=metadata,
        )

    def get_market(self, ticker: str) -> KalshiMarketDetailDTO:
        payload, metadata = self._request_json(
            "GET",
            _api_path("markets", ticker),
        )
        market_payload = payload.get("market")
        if not isinstance(market_payload, Mapping):
            msg = "Kalshi market response did not include a market object"
            raise KalshiRequestError(
                status_code=200,
                method="GET",
                path=_api_path("markets", ticker),
                response_text=msg,
            )
        return KalshiMarketDetailDTO(
            market=_normalize_market(market_payload),
            request_metadata=metadata,
        )

    def get_market_orderbook(self, ticker: str) -> KalshiOrderbookDTO:
        payload, metadata = self._request_json(
            "GET",
            _api_path("markets", ticker, "orderbook"),
        )
        orderbook_payload = payload.get("orderbook_fp")
        if not isinstance(orderbook_payload, Mapping):
            msg = "Kalshi orderbook response did not include an orderbook_fp object"
            raise KalshiRequestError(
                status_code=200,
                method="GET",
                path=_api_path("markets", ticker, "orderbook"),
                response_text=msg,
            )
        return _normalize_orderbook(
            ticker=ticker,
            payload=orderbook_payload,
            request_metadata=metadata,
        )

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, str] | None = None,
    ) -> tuple[dict[str, object], KalshiRequestMetadata]:
        timestamp_ms = self._timestamp_provider()
        signed_payload = f"{timestamp_ms}{method}{path}"
        signature = _sign_request_payload(self._private_key, signed_payload)
        query_params = httpx.QueryParams(params) if params is not None else httpx.QueryParams()
        headers = {
            KALSHI_ACCESS_KEY_HEADER: self._access_key,
            KALSHI_ACCESS_TIMESTAMP_HEADER: str(timestamp_ms),
            KALSHI_ACCESS_SIGNATURE_HEADER: signature,
        }
        response = self._client.request(
            method,
            path,
            params=query_params,
            headers=headers,
        )
        request_metadata = KalshiRequestMetadata(
            method=method,
            path=path,
            query_params=tuple(params.items()) if params is not None else (),
            timestamp_ms=timestamp_ms,
            base_url=self._base_url,
            signed_payload=signed_payload,
        )
        if response.is_error:
            raise KalshiRequestError(
                status_code=response.status_code,
                method=method,
                path=path,
                response_text=response.text,
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise KalshiRequestError(
                status_code=response.status_code,
                method=method,
                path=path,
                response_text="Kalshi responses must decode to JSON objects",
            )
        return cast(dict[str, object], payload), request_metadata


def _default_base_url(settings: Settings) -> str:
    if settings.environment == "prod":
        return KALSHI_PROD_HOST
    return KALSHI_DEMO_HOST


def _normalize_base_url(base_url: str) -> str:
    url = httpx.URL(base_url)
    if url.scheme != "https":
        raise ValueError("Kalshi base_url must use https")
    if url.host is None:
        raise ValueError("Kalshi base_url must include a host")
    host = f"{url.scheme}://{url.host}"
    if url.port is not None:
        host = f"{host}:{url.port}"
    return host


def _api_path(*parts: str) -> str:
    normalized_parts = [part.strip("/") for part in parts if part]
    return f"{KALSHI_API_PATH_PREFIX}/" + "/".join(normalized_parts)


def _build_market_query_params(
    *,
    limit: int,
    cursor: str | None,
    event_ticker: str | None,
    series_ticker: str | None,
    tickers: Sequence[str] | None,
    min_created_ts: int | None,
    max_created_ts: int | None,
    min_updated_ts: int | None,
    min_close_ts: int | None,
    max_close_ts: int | None,
    min_settled_ts: int | None,
    max_settled_ts: int | None,
    status: AllowedMarketStatus | None,
    mve_filter: AllowedMveFilter | None,
) -> dict[str, str]:
    params: dict[str, str] = {"limit": str(limit)}
    if cursor is not None:
        params["cursor"] = cursor
    if event_ticker is not None:
        params["event_ticker"] = event_ticker
    if series_ticker is not None:
        params["series_ticker"] = series_ticker
    if tickers is not None:
        params["tickers"] = ",".join(tickers)
    if min_created_ts is not None:
        params["min_created_ts"] = str(min_created_ts)
    if max_created_ts is not None:
        params["max_created_ts"] = str(max_created_ts)
    if min_updated_ts is not None:
        params["min_updated_ts"] = str(min_updated_ts)
    if min_close_ts is not None:
        params["min_close_ts"] = str(min_close_ts)
    if max_close_ts is not None:
        params["max_close_ts"] = str(max_close_ts)
    if min_settled_ts is not None:
        params["min_settled_ts"] = str(min_settled_ts)
    if max_settled_ts is not None:
        params["max_settled_ts"] = str(max_settled_ts)
    if status is not None:
        params["status"] = status
    if mve_filter is not None:
        params["mve_filter"] = mve_filter
    return params


def _normalize_market(raw: Mapping[str, object]) -> KalshiMarketDTO:
    return KalshiMarketDTO(
        ticker=_require_str(raw, "ticker"),
        event_ticker=_require_str(raw, "event_ticker"),
        status=_optional_str(raw.get("status")),
        title=_optional_str(raw.get("title")),
        yes_sub_title=_optional_str(raw.get("yes_sub_title")),
        no_sub_title=_optional_str(raw.get("no_sub_title")),
        created_time=_parse_datetime(raw.get("created_time")),
        updated_time=_parse_datetime(raw.get("updated_time")),
        open_time=_parse_datetime(raw.get("open_time")),
        close_time=_parse_datetime(raw.get("close_time")),
        latest_expiration_time=_parse_datetime(raw.get("latest_expiration_time")),
        settlement_timer_seconds=_optional_int(raw.get("settlement_timer_seconds")),
        yes_bid_dollars=_optional_decimal(raw.get("yes_bid_dollars")),
        yes_bid_size_fp=_optional_decimal(raw.get("yes_bid_size_fp")),
        yes_ask_dollars=_optional_decimal(raw.get("yes_ask_dollars")),
        yes_ask_size_fp=_optional_decimal(raw.get("yes_ask_size_fp")),
        no_bid_dollars=_optional_decimal(raw.get("no_bid_dollars")),
        no_bid_size_fp=_optional_decimal(raw.get("no_bid_size_fp")),
        no_ask_dollars=_optional_decimal(raw.get("no_ask_dollars")),
        no_ask_size_fp=_optional_decimal(raw.get("no_ask_size_fp")),
        last_price_dollars=_optional_decimal(raw.get("last_price_dollars")),
        volume_fp=_optional_decimal(raw.get("volume_fp")),
        volume_24h_fp=_optional_decimal(raw.get("volume_24h_fp")),
        can_close_early=_optional_bool(raw.get("can_close_early")),
        fractional_trading_enabled=_optional_bool(raw.get("fractional_trading_enabled")),
        open_interest_fp=_optional_decimal(raw.get("open_interest_fp")),
        notional_value_dollars=_optional_decimal(raw.get("notional_value_dollars")),
        previous_yes_bid_dollars=_optional_decimal(raw.get("previous_yes_bid_dollars")),
        previous_yes_ask_dollars=_optional_decimal(raw.get("previous_yes_ask_dollars")),
        previous_no_bid_dollars=_optional_decimal(raw.get("previous_no_bid_dollars")),
        previous_no_ask_dollars=_optional_decimal(raw.get("previous_no_ask_dollars")),
    )


def _normalize_orderbook(
    *,
    ticker: str,
    payload: Mapping[str, object],
    request_metadata: KalshiRequestMetadata,
) -> KalshiOrderbookDTO:
    yes_side = _normalize_orderbook_side(payload.get("yes_dollars"))
    no_side = _normalize_orderbook_side(payload.get("no_dollars"))
    return KalshiOrderbookDTO(
        ticker=ticker,
        yes_levels=yes_side,
        no_levels=no_side,
        request_metadata=request_metadata,
    )


def _normalize_orderbook_side(
    payload: object,
) -> tuple[KalshiOrderbookLevelDTO, ...]:
    if payload is None:
        return ()
    if not isinstance(payload, Sequence) or isinstance(payload, (str, bytes)):
        raise KalshiRequestError(
            status_code=200,
            method="GET",
            path=_api_path("markets", "orderbook"),
            response_text="Kalshi orderbook sides must be arrays",
        )
    levels: list[KalshiOrderbookLevelDTO] = []
    for level in payload:
        if not isinstance(level, Sequence) or len(level) != 2:
            raise KalshiRequestError(
                status_code=200,
                method="GET",
                path=_api_path("markets", "orderbook"),
                response_text="Kalshi orderbook levels must contain price and size",
            )
        price_raw, quantity_raw = level
        levels.append(
            KalshiOrderbookLevelDTO(
                price_dollars=_require_decimal(price_raw),
                quantity_fp=_require_decimal(quantity_raw),
            )
        )
    return tuple(levels)


def _sign_request_payload(private_key: RSAPrivateKey, payload: str) -> str:
    signature = private_key.sign(
        payload.encode("utf-8"),
        padding.PSS(
            mgf=padding.MGF1(hashes.SHA256()),
            salt_length=padding.PSS.DIGEST_LENGTH,
        ),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


def _load_private_key(
    value: RSAPrivateKey | str | Path,
) -> RSAPrivateKey:
    if isinstance(value, RSAPrivateKey):
        return value
    if isinstance(value, Path):
        private_key_bytes = value.read_bytes()
    else:
        candidate_path = Path(value)
        if "\n" not in value and candidate_path.exists():
            private_key_bytes = candidate_path.read_bytes()
        else:
            private_key_bytes = value.encode("utf-8")
    private_key = serialization.load_pem_private_key(
        private_key_bytes,
        password=None,
    )
    if not isinstance(private_key, RSAPrivateKey):
        raise TypeError("Kalshi private key must be an RSA private key")
    return private_key


def _current_timestamp_ms() -> int:
    return int(datetime.now(tz=UTC).timestamp() * 1000)


def _require_str(raw: Mapping[str, object], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str):
        raise KalshiRequestError(
            status_code=200,
            method="GET",
            path=key,
            response_text=f"Kalshi payload field {key} must be a string",
        )
    return value


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return int(value)
    return None


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() == "true"
    return bool(value)


def _optional_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _require_decimal(value: object) -> Decimal:
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _parse_datetime(value: object) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)
