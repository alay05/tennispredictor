from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from tennisprediction.kalshi.client import AllowedMarketStatus, KalshiReadClient
from tennisprediction.kalshi.retry import retry_kalshi_read_call
from tennisprediction.kalshi.schemas import (
    KalshiMarketDetailDTO,
    KalshiMarketDTO,
    KalshiMarketPageDTO,
    KalshiOrderbookDTO,
)
from tennisprediction.kalshi.snapshots import (
    KalshiMarketDetailSnapshotRow,
    KalshiMarketSnapshotRow,
    KalshiOrderbookSnapshotRow,
    KalshiRequestLogRow,
    KalshiSnapshotBatch,
    build_market_detail_snapshot_row,
    build_market_snapshot_row,
    build_orderbook_snapshot_row,
    build_request_log_row,
)
from tennisprediction.kalshi.storage import persist_kalshi_snapshot_batch

__all__ = ["collect_kalshi_snapshots"]

_READ_ONLY_MARKET_STATUSES = {"unopened", "open", "paused", "closed", "settled"}


@dataclass(frozen=True)
class _MarketCollectionAction:
    collect_detail: bool
    collect_orderbook: bool


def collect_kalshi_snapshots(
    client: KalshiReadClient,
    *,
    database_path: str | Path | None = None,
    page_limit: int = 100,
    status: AllowedMarketStatus | None = None,
    max_attempts: int = 4,
    initial_backoff_seconds: float = 0.25,
    max_backoff_seconds: float = 2.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Path:
    if page_limit < 1:
        raise ValueError("page_limit must be at least 1")

    request_logs: list[KalshiRequestLogRow] = []
    market_snapshots: list[KalshiMarketSnapshotRow] = []
    market_detail_snapshots: list[KalshiMarketDetailSnapshotRow] = []
    orderbook_snapshots: list[KalshiOrderbookSnapshotRow] = []

    cursor: str | None = None
    seen_cursors: set[str | None] = set()

    while True:
        if cursor in seen_cursors:
            raise ValueError("Kalshi market pagination cursor repeated")
        seen_cursors.add(cursor)

        page = retry_kalshi_read_call(
            _read_market_page(
                client=client,
                page_limit=page_limit,
                cursor=cursor,
                status=status,
            ),
            max_attempts=max_attempts,
            initial_backoff_seconds=initial_backoff_seconds,
            max_backoff_seconds=max_backoff_seconds,
            sleep_fn=sleep_fn,
        )
        page_request_log = build_request_log_row(
            page.request_metadata,
            response_status_code=200,
            response_payload=_page_response_payload(page.markets, page.cursor),
            response_cursor=page.cursor,
        )
        request_logs.append(page_request_log)

        for response_index, market in enumerate(page.markets):
            market_snapshots.append(
                build_market_snapshot_row(
                    page_request_log,
                    market,
                    response_index=response_index,
                ),
            )

            collection_action = _market_collection_action(market.status)
            if not collection_action.collect_detail:
                continue

            detail = retry_kalshi_read_call(
                _read_market_detail(client=client, ticker=market.ticker),
                max_attempts=max_attempts,
                initial_backoff_seconds=initial_backoff_seconds,
                max_backoff_seconds=max_backoff_seconds,
                sleep_fn=sleep_fn,
            )
            detail_request_log = build_request_log_row(
                detail.request_metadata,
                response_status_code=200,
                response_payload={"market": asdict(detail.market)},
            )
            request_logs.append(detail_request_log)
            market_detail_snapshots.append(
                build_market_detail_snapshot_row(detail_request_log, detail),
            )

            if not collection_action.collect_orderbook:
                continue

            orderbook = retry_kalshi_read_call(
                _read_market_orderbook(client=client, ticker=market.ticker),
                max_attempts=max_attempts,
                initial_backoff_seconds=initial_backoff_seconds,
                max_backoff_seconds=max_backoff_seconds,
                sleep_fn=sleep_fn,
            )
            orderbook_request_log = build_request_log_row(
                orderbook.request_metadata,
                response_status_code=200,
                response_payload=_orderbook_response_payload(orderbook),
            )
            request_logs.append(orderbook_request_log)
            orderbook_snapshots.append(
                build_orderbook_snapshot_row(orderbook_request_log, orderbook),
            )

        if page.cursor is None:
            break
        cursor = page.cursor

    batch = KalshiSnapshotBatch(
        request_logs=tuple(request_logs),
        market_snapshots=tuple(market_snapshots),
        market_detail_snapshots=tuple(market_detail_snapshots),
        orderbook_snapshots=tuple(orderbook_snapshots),
    )
    return persist_kalshi_snapshot_batch(batch, database_path=database_path)


def _market_collection_action(status: str | None) -> _MarketCollectionAction:
    if status == "open":
        return _MarketCollectionAction(
            collect_detail=True,
            collect_orderbook=True,
        )
    if status in _READ_ONLY_MARKET_STATUSES:
        return _MarketCollectionAction(
            collect_detail=False,
            collect_orderbook=False,
        )
    raise ValueError(f"Unsupported Kalshi market status: {status}")


def _page_response_payload(
    markets: tuple[KalshiMarketDTO, ...],
    cursor: str | None,
) -> dict[str, object]:
    return {
        "markets": [asdict(market) for market in markets],
        "cursor": cursor,
    }


def _orderbook_response_payload(orderbook: KalshiOrderbookDTO) -> dict[str, object]:
    yes_levels = [
        [str(level.price_dollars), str(level.quantity_fp)]
        for level in orderbook.yes_levels
    ]
    no_levels = [
        [str(level.price_dollars), str(level.quantity_fp)]
        for level in orderbook.no_levels
    ]
    return {
        "orderbook_fp": {
            "yes_dollars": yes_levels,
            "no_dollars": no_levels,
        }
    }


def _read_market_page(
    *,
    client: KalshiReadClient,
    page_limit: int,
    cursor: str | None,
    status: AllowedMarketStatus | None,
) -> Callable[[], KalshiMarketPageDTO]:
    def read_market_page() -> KalshiMarketPageDTO:
        return client.list_markets(
            limit=page_limit,
            cursor=cursor,
            status=status,
        )

    return read_market_page


def _read_market_detail(
    *,
    client: KalshiReadClient,
    ticker: str,
) -> Callable[[], KalshiMarketDetailDTO]:
    def read_market_detail() -> KalshiMarketDetailDTO:
        return client.get_market(ticker)

    return read_market_detail


def _read_market_orderbook(
    *,
    client: KalshiReadClient,
    ticker: str,
) -> Callable[[], KalshiOrderbookDTO]:
    def read_market_orderbook() -> KalshiOrderbookDTO:
        return client.get_market_orderbook(ticker)

    return read_market_orderbook
