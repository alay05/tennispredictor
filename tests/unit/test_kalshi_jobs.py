from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pytest
import typer

import tennisprediction.cli as cli_module
import tennisprediction.kalshi.jobs as jobs_module
from tennisprediction.kalshi.client import KalshiRequestError
from tennisprediction.kalshi.jobs import collect_kalshi_snapshots
from tennisprediction.kalshi.retry import retry_kalshi_read_call
from tennisprediction.kalshi.schemas import (
    KalshiMarketDetailDTO,
    KalshiMarketDTO,
    KalshiMarketPageDTO,
    KalshiOrderbookDTO,
    KalshiOrderbookLevelDTO,
    KalshiRequestMetadata,
)


def test_retry_kalshi_read_call_backs_off_on_429s_and_stops_after_the_configured_cap() -> None:
    attempts = 0
    sleep_calls: list[float] = []

    def flaky_call() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise _retryable_429()
        return "ok"

    result = retry_kalshi_read_call(
        flaky_call,
        max_attempts=4,
        initial_backoff_seconds=0.25,
        max_backoff_seconds=1.0,
        sleep_fn=sleep_calls.append,
    )

    assert result == "ok"
    assert attempts == 3
    assert sleep_calls == [0.25, 0.5]

    attempts = 0
    sleep_calls = []

    def always_rate_limited() -> str:
        nonlocal attempts
        attempts += 1
        raise _retryable_429()

    with pytest.raises(KalshiRequestError, match="429"):
        retry_kalshi_read_call(
            always_rate_limited,
            max_attempts=3,
            initial_backoff_seconds=0.1,
            max_backoff_seconds=1.0,
            sleep_fn=sleep_calls.append,
        )

    assert attempts == 3
    assert sleep_calls == [0.1, 0.2]


def test_collect_kalshi_snapshots_paginates_until_cursor_exhaustion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeKalshiClient(
        pages=[
            _market_page(
                request_index=1,
                cursor="cursor-2",
                markets=(_market("ATP-CLOSED-001", "closed"),),
            ),
            _market_page(
                request_index=2,
                cursor=None,
                markets=(_market("ATP-SETTLED-001", "settled"),),
            ),
        ],
    )
    captured_batches: list[object] = []
    monkeypatch.setattr(
        "tennisprediction.kalshi.jobs.persist_kalshi_snapshot_batch",
        lambda batch, database_path=None: _capture_batch(
            batch=batch,
            database_path=database_path,
            captured_batches=captured_batches,
        ),
    )

    persisted_path = collect_kalshi_snapshots(
        client,
        database_path=tmp_path / "snapshots.duckdb",
        page_limit=2,
        sleep_fn=lambda _seconds: None,
    )

    assert persisted_path == tmp_path / "snapshots.duckdb"
    assert client.list_calls == [
        {"limit": 2, "cursor": None, "status": None},
        {"limit": 2, "cursor": "cursor-2", "status": None},
    ]
    assert client.detail_calls == []
    assert client.orderbook_calls == []
    assert len(captured_batches) == 1
    batch = captured_batches[0]
    assert len(batch.request_logs) == 2
    assert len(batch.market_snapshots) == 2
    assert len(batch.market_detail_snapshots) == 0
    assert len(batch.orderbook_snapshots) == 0
    assert [row.ticker for row in batch.market_snapshots] == [
        "ATP-CLOSED-001",
        "ATP-SETTLED-001",
    ]


def test_collect_kalshi_snapshots_handles_market_states_explicitly_and_stays_read_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _FakeKalshiClient(
        pages=[
            _market_page(
                request_index=1,
                cursor=None,
                markets=(
                    _market("ATP-CLOSED-001", "closed"),
                    _market("ATP-SETTLED-001", "settled"),
                    _market("ATP-PAUSED-001", "paused"),
                    _market("ATP-UNOPENED-001", "unopened"),
                    _market("ATP-OPEN-001", "open"),
                ),
            ),
        ],
        detail_markets={
            "ATP-OPEN-001": _market_detail("ATP-OPEN-001", "open"),
        },
        orderbooks={
            "ATP-OPEN-001": _market_orderbook("ATP-OPEN-001"),
        },
    )
    captured_batches: list[object] = []
    monkeypatch.setattr(
        "tennisprediction.kalshi.jobs.persist_kalshi_snapshot_batch",
        lambda batch, database_path=None: _capture_batch(
            batch=batch,
            database_path=database_path,
            captured_batches=captured_batches,
        ),
    )

    collect_kalshi_snapshots(
        client,
        database_path=tmp_path / "snapshots.duckdb",
        page_limit=10,
        sleep_fn=lambda _seconds: None,
    )

    assert client.detail_calls == ["ATP-OPEN-001"]
    assert client.orderbook_calls == ["ATP-OPEN-001"]
    batch = captured_batches[0]
    assert [row.status for row in batch.market_snapshots] == [
        "closed",
        "settled",
        "paused",
        "unopened",
        "open",
    ]
    assert [row.ticker for row in batch.market_detail_snapshots] == [
        "ATP-OPEN-001",
    ]
    assert [row.ticker for row in batch.orderbook_snapshots] == [
        "ATP-OPEN-001",
    ]

    public_command_names = sorted(
        typer.main.get_command(cli_module.app).commands,
    )
    assert public_command_names == [
        "build-features",
        "collect-kalshi-snapshots",
        "evaluate-artifact",
        "health",
        "ingest-snapshot",
        "review-monitoring-report",
        "run-backtest",
        "scan-kalshi-ev",
        "train-artifact-bundle",
        "version",
    ]
    assert not any(
        forbidden in " ".join(public_command_names)
        for forbidden in ("order", "execute", "prep", "trade", "write")
    )

    public_symbols = [
        name for name, value in inspect.getmembers(jobs_module) if not name.startswith("_")
    ]
    assert not any(
        forbidden in " ".join(public_symbols)
        for forbidden in ("place_order", "execute", "execution", "write")
    )


def test_collect_kalshi_snapshots_rejects_unknown_market_states() -> None:
    with pytest.raises(ValueError, match="Unsupported Kalshi market status"):
        jobs_module._market_collection_action("mystery")


@dataclass
class _FakeKalshiClient:
    pages: list[KalshiMarketPageDTO]
    detail_markets: dict[str, KalshiMarketDetailDTO] = field(default_factory=dict)
    orderbooks: dict[str, KalshiOrderbookDTO] = field(default_factory=dict)
    list_calls: list[dict[str, object | None]] = field(default_factory=list)
    detail_calls: list[str] = field(default_factory=list)
    orderbook_calls: list[str] = field(default_factory=list)

    def list_markets(
        self,
        *,
        limit: int = 100,
        cursor: str | None = None,
        event_ticker: str | None = None,
        series_ticker: str | None = None,
        tickers: object | None = None,
        min_created_ts: int | None = None,
        max_created_ts: int | None = None,
        min_updated_ts: int | None = None,
        min_close_ts: int | None = None,
        max_close_ts: int | None = None,
        min_settled_ts: int | None = None,
        max_settled_ts: int | None = None,
        status: str | None = None,
        mve_filter: str | None = None,
    ) -> KalshiMarketPageDTO:
        self.list_calls.append({"limit": limit, "cursor": cursor, "status": status})
        return self.pages.pop(0)

    def get_market(self, ticker: str) -> KalshiMarketDetailDTO:
        self.detail_calls.append(ticker)
        return self.detail_markets[ticker]

    def get_market_orderbook(self, ticker: str) -> KalshiOrderbookDTO:
        self.orderbook_calls.append(ticker)
        return self.orderbooks[ticker]


def _capture_batch(
    *,
    batch: object,
    database_path: Path | None,
    captured_batches: list[object],
) -> Path:
    captured_batches.append(batch)
    return Path(database_path) if database_path is not None else Path("captured.duckdb")


def _retryable_429() -> KalshiRequestError:
    return KalshiRequestError(
        status_code=429,
        method="GET",
        path="/trade-api/v2/markets",
        response_text="rate limited",
    )


def _market(
    ticker: str,
    status: str,
) -> KalshiMarketDTO:
    return KalshiMarketDTO(
        ticker=ticker,
        event_ticker=f"{ticker}-EVENT",
        status=status,
        title=f"{ticker} title",
        yes_sub_title="Yes side",
        no_sub_title="No side",
        created_time=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        updated_time=datetime(2024, 1, 1, 11, 0, tzinfo=UTC),
        open_time=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
        close_time=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
        latest_expiration_time=datetime(2024, 1, 1, 14, 0, tzinfo=UTC),
        settlement_timer_seconds=120,
        yes_bid_dollars=Decimal("0.55"),
        yes_bid_size_fp=Decimal("10"),
        yes_ask_dollars=Decimal("0.57"),
        yes_ask_size_fp=Decimal("8"),
        no_bid_dollars=Decimal("0.43"),
        no_bid_size_fp=Decimal("9"),
        no_ask_dollars=Decimal("0.45"),
        no_ask_size_fp=Decimal("7"),
        last_price_dollars=Decimal("0.56"),
        volume_fp=Decimal("100"),
        volume_24h_fp=Decimal("50"),
        can_close_early=True,
        fractional_trading_enabled=True,
        open_interest_fp=Decimal("25"),
        notional_value_dollars=Decimal("1.00"),
        previous_yes_bid_dollars=Decimal("0.54"),
        previous_yes_ask_dollars=Decimal("0.58"),
        previous_no_bid_dollars=Decimal("0.42"),
        previous_no_ask_dollars=Decimal("0.46"),
    )


def _market_page(
    *,
    request_index: int,
    cursor: str | None,
    markets: tuple[KalshiMarketDTO, ...],
) -> KalshiMarketPageDTO:
    return KalshiMarketPageDTO(
        markets=markets,
        cursor=cursor,
        request_metadata=_request_metadata(
            request_index=request_index,
            path="/trade-api/v2/markets",
            query_params=(("limit", "2"),) if request_index == 1 else (("cursor", "cursor-2"),),
        ),
    )


def _market_detail(
    ticker: str,
    status: str,
) -> KalshiMarketDetailDTO:
    return KalshiMarketDetailDTO(
        market=_market(ticker, status),
        request_metadata=_request_metadata(
            request_index=99,
            path=f"/trade-api/v2/markets/{ticker}",
        ),
    )


def _market_orderbook(ticker: str) -> KalshiOrderbookDTO:
    return KalshiOrderbookDTO(
        ticker=ticker,
        yes_levels=(KalshiOrderbookLevelDTO(Decimal("0.15"), Decimal("100")),),
        no_levels=(KalshiOrderbookLevelDTO(Decimal("0.85"), Decimal("75")),),
        request_metadata=_request_metadata(
            request_index=100,
            path=f"/trade-api/v2/markets/{ticker}/orderbook",
        ),
    )


def _request_metadata(
    *,
    request_index: int,
    path: str,
    query_params: tuple[tuple[str, str], ...] = (),
) -> KalshiRequestMetadata:
    timestamp_ms = 1704112496000 + request_index
    return KalshiRequestMetadata(
        method="GET",
        path=path,
        query_params=query_params,
        timestamp_ms=timestamp_ms,
        base_url="https://external-api.demo.kalshi.co",
        signed_payload=f"{timestamp_ms}GET{path}",
    )


def _market_collection_action(status: str) -> None:
    if status not in {"open", "paused", "closed", "settled", "unopened"}:
        raise ValueError("Unsupported Kalshi market status")
