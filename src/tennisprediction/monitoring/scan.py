from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from tennisprediction.backtesting.replay import predict_matches_for_canonical_ids
from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    DecisionThresholds,
    OpportunityDecisionRecord,
)
from tennisprediction.ev.opportunity import evaluate_opportunities
from tennisprediction.kalshi.client import KalshiReadClient
from tennisprediction.kalshi.executable import derive_executable_market_input
from tennisprediction.kalshi.jobs import collect_kalshi_snapshots
from tennisprediction.kalshi.snapshots import KalshiOrderbookSnapshotRow
from tennisprediction.logging import bind_audit_context
from tennisprediction.market_mapping import (
    MarketMappingEvidenceRow,
    resolve_kalshi_market_mappings,
)
from tennisprediction.market_mapping.resolver import require_matched_mapping

_LOGGER = logging.getLogger("tennisprediction.monitoring.scan")


@dataclass(frozen=True)
class ScanRunResult:
    run_id: str
    snapshot_database_path: Path
    accepted_records: list[dict[str, object]]
    rejected_records: list[dict[str, object]]


def run_kalshi_ev_scan(
    *,
    artifact_dir: str | Path,
    database_path: str | Path | None,
    expected_feature_version: str,
    expected_split_manifest_id: str,
    thresholds: DecisionThresholds,
    run_id: str,
    collect_fresh: bool = False,
    access_key: str | None = None,
    private_key: Path | None = None,
    base_url: str | None = None,
    page_limit: int = 100,
    evaluated_at_utc: datetime | None = None,
) -> ScanRunResult:
    logger = bind_audit_context(
        _LOGGER,
        run_id=run_id,
        command="scan-kalshi-ev",
        artifact_run_id=run_id,
    )
    snapshot_database_path = _resolve_snapshot_database_path(
        database_path=database_path,
        collect_fresh=collect_fresh,
        access_key=access_key,
        private_key=private_key,
        base_url=base_url,
        page_limit=page_limit,
    )
    effective_evaluated_at = evaluated_at_utc or datetime.now(UTC)

    mapping_rows = resolve_kalshi_market_mappings(database_path=snapshot_database_path)
    orderbook_rows = load_latest_orderbook_snapshots(
        database_path=snapshot_database_path,
        tickers=tuple(
            row.market_ticker
            for row in mapping_rows
            if require_matched_mapping(row) is None
        ),
    )
    replay_rows = predict_matches_for_canonical_ids(
        artifact_dir,
        snapshot_database_path,
        canonical_match_ids=tuple(
            row.canonical_match_id
            for row in mapping_rows
            if require_matched_mapping(row) is None and row.canonical_match_id is not None
        ),
        expected_feature_version=expected_feature_version,
        expected_split_manifest_id=expected_split_manifest_id,
    )
    replay_lookup = {row.canonical_match_id: row for row in replay_rows}

    accepted_records: list[dict[str, object]] = []
    rejected_records: list[dict[str, object]] = []
    matched_count = 0
    for mapping_row in mapping_rows:
        mapping_rejection = require_matched_mapping(mapping_row)
        if mapping_rejection is not None:
            rejected_records.append(
                _serialize_unscorable_mapping(mapping_row, mapping_rejection.rejection_reason_codes)
            )
            continue

        matched_count += 1
        orderbook_row = orderbook_rows.get(mapping_row.market_ticker)
        if orderbook_row is None:
            rejected_records.append(
                _serialize_unscorable_mapping(mapping_row, ("missing_orderbook_snapshot",))
            )
            continue

        replay_row = replay_lookup.get(mapping_row.canonical_match_id or "")
        if replay_row is None:
            rejected_records.append(
                _serialize_unscorable_mapping(mapping_row, ("missing_prediction",))
            )
            continue

        market_input = derive_executable_market_input(
            orderbook_row=orderbook_row,
            mapping_row=mapping_row,
            evaluated_at_utc=effective_evaluated_at,
        )
        decision_batch = evaluate_opportunities(
            [replay_row],
            [market_input],
            thresholds,
            run_id=run_id,
            provenance_label=BacktestProvenanceLabel.collected_snapshot_replay,
        )
        accepted_records.extend(
            _serialize_decision_record(record, mapping_row)
            for record in decision_batch.accepted_records
        )
        rejected_records.extend(
            _serialize_decision_record(record, mapping_row)
            for record in decision_batch.rejected_records
        )

    # Keep the matched count materialized via accepted/rejected rows, not only a transient variable.
    _ = matched_count

    logger.info(
        "Completed Kalshi EV scan",
        extra={
            "stage": "scan",
            "decision_state": "scan_completed",
            "mapping_state": "matched" if matched_count else "unmatched",
            "accepted_count": len(accepted_records),
            "rejected_count": len(rejected_records),
            "matched_count": matched_count,
            "snapshot_database_path": str(snapshot_database_path),
        },
    )
    return ScanRunResult(
        run_id=run_id,
        snapshot_database_path=snapshot_database_path,
        accepted_records=accepted_records,
        rejected_records=rejected_records,
    )


def load_latest_orderbook_snapshots(
    *,
    database_path: str | Path,
    tickers: tuple[str, ...],
) -> dict[str, KalshiOrderbookSnapshotRow]:
    if not tickers:
        return {}

    connection = duckdb.connect(str(database_path))
    try:
        records = connection.execute(
            """
            with ranked as (
                select
                    *,
                    row_number() over (
                        partition by ticker
                        order by collected_at_utc desc, response_index desc
                    ) as snapshot_rank
                from kalshi_orderbook_snapshots
                where ticker in (
                    select unnest(?::varchar[])
                )
            )
            select
                request_id,
                collected_at_utc,
                request_method,
                request_path,
                request_base_url,
                request_timestamp_ms,
                request_signed_payload,
                request_query_params_json,
                request_cursor,
                request_filter_params_json,
                response_status_code,
                response_cursor,
                response_checksum,
                response_index,
                ticker,
                yes_levels_json,
                no_levels_json,
                yes_level_count,
                no_level_count,
                yes_best_price_dollars,
                yes_best_quantity_fp,
                no_best_price_dollars,
                no_best_quantity_fp
            from ranked
            where snapshot_rank = 1
            order by ticker
            """,
            [list(tickers)],
        ).fetchall()
    finally:
        connection.close()

    rows = [
        KalshiOrderbookSnapshotRow(
            request_id=request_id,
            collected_at_utc=collected_at_utc,
            request_method=request_method,
            request_path=request_path,
            request_base_url=request_base_url,
            request_timestamp_ms=request_timestamp_ms,
            request_signed_payload=request_signed_payload,
            request_query_params_json=request_query_params_json,
            request_cursor=request_cursor,
            request_filter_params_json=request_filter_params_json,
            response_status_code=response_status_code,
            response_cursor=response_cursor,
            response_checksum=response_checksum,
            response_index=response_index,
            ticker=ticker,
            yes_levels_json=yes_levels_json,
            no_levels_json=no_levels_json,
            yes_level_count=yes_level_count,
            no_level_count=no_level_count,
            yes_best_price_dollars=yes_best_price_dollars,
            yes_best_quantity_fp=yes_best_quantity_fp,
            no_best_price_dollars=no_best_price_dollars,
            no_best_quantity_fp=no_best_quantity_fp,
        )
        for (
            request_id,
            collected_at_utc,
            request_method,
            request_path,
            request_base_url,
            request_timestamp_ms,
            request_signed_payload,
            request_query_params_json,
            request_cursor,
            request_filter_params_json,
            response_status_code,
            response_cursor,
            response_checksum,
            response_index,
            ticker,
            yes_levels_json,
            no_levels_json,
            yes_level_count,
            no_level_count,
            yes_best_price_dollars,
            yes_best_quantity_fp,
            no_best_price_dollars,
            no_best_quantity_fp,
        ) in records
    ]
    return {row.ticker: row for row in rows}


def _resolve_snapshot_database_path(
    *,
    database_path: str | Path | None,
    collect_fresh: bool,
    access_key: str | None,
    private_key: Path | None,
    base_url: str | None,
    page_limit: int,
) -> Path:
    if not collect_fresh:
        if database_path is None:
            msg = "database_path is required when collect_fresh is disabled"
            raise ValueError(msg)
        return Path(database_path)

    if access_key is None or private_key is None:
        msg = "access_key and private_key are required when collect_fresh is enabled"
        raise ValueError(msg)

    client = KalshiReadClient(
        access_key=access_key,
        private_key=private_key,
        base_url=base_url,
    )
    try:
        return collect_kalshi_snapshots(
            client,
            database_path=database_path,
            page_limit=page_limit,
            status="open",
        )
    finally:
        client.close()


def _serialize_decision_record(
    record: OpportunityDecisionRecord,
    mapping_row: MarketMappingEvidenceRow,
) -> dict[str, object]:
    payload = asdict(record)
    payload["mapping_state"] = mapping_row.mapping_state.value
    payload["mapping_confidence"] = mapping_row.mapping_confidence.value
    payload["market_ticker"] = mapping_row.market_ticker
    payload["event_ticker"] = mapping_row.event_ticker
    payload["yes_canonical_player_id"] = mapping_row.yes_canonical_player_id
    payload["no_canonical_player_id"] = mapping_row.no_canonical_player_id
    payload["yes_maps_to_player_a"] = mapping_row.yes_maps_to_player_a
    payload["no_maps_to_player_b"] = mapping_row.no_maps_to_player_b
    payload["rejection_reason_codes"] = list(record.rejection_reason_codes)
    provenance_label = payload.get("provenance_label")
    if provenance_label is not None:
        payload["provenance_label"] = str(provenance_label)
    return payload


def _serialize_unscorable_mapping(
    mapping_row: MarketMappingEvidenceRow,
    rejection_reason_codes: tuple[str, ...],
) -> dict[str, object]:
    return {
        "artifact_run_id": "",
        "canonical_match_id": mapping_row.canonical_match_id,
        "model_name": "",
        "model_family": "",
        "feature_version": "",
        "split_manifest_id": "",
        "source_commit_sha": "",
        "as_of_date": "",
        "selected_side": "",
        "model_probability": None,
        "market_probability": None,
        "edge": None,
        "expected_value_per_contract": None,
        "confidence": 0.0,
        "available_liquidity_dollars": None,
        "market_probability_source": "",
        "liquidity_source": "",
        "provenance_label": "",
        "threshold_snapshot": {},
        "accepted": False,
        "selected_entry_price": None,
        "entry_price_source": "",
        "freshness_age_seconds": None,
        "freshness_source": "",
        "rejection_reason_codes": list(rejection_reason_codes),
        "realized_outcome": None,
        "realized_pnl": None,
        "mapping_state": mapping_row.mapping_state.value,
        "mapping_confidence": mapping_row.mapping_confidence.value,
        "market_ticker": mapping_row.market_ticker,
        "event_ticker": mapping_row.event_ticker,
        "yes_canonical_player_id": mapping_row.yes_canonical_player_id,
        "no_canonical_player_id": mapping_row.no_canonical_player_id,
        "yes_maps_to_player_a": mapping_row.yes_maps_to_player_a,
        "no_maps_to_player_b": mapping_row.no_maps_to_player_b,
    }
