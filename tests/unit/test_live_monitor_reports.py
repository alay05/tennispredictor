from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

import tennisprediction.config as config_module
from tennisprediction.config import Settings
from tennisprediction.monitoring.reports import write_live_monitor_reports


def test_write_live_monitor_reports_ranks_rows_and_persists_accepted_rejected_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    settings = Settings(
        data_dir=Path("data"),
        models_dir=Path("models"),
        reports_dir=Path("reports"),
        duckdb_path=Path("data/testing.duckdb"),
    )
    accepted_rows = [
        _accepted_row(
            canonical_match_id="match-c",
            market_ticker="KXATP-C",
            expected_value_per_contract=0.08,
            edge=0.05,
            available_liquidity_dollars=15.0,
            confidence=0.70,
            freshness_age_seconds=18.0,
        ),
        _accepted_row(
            canonical_match_id="match-a",
            market_ticker="KXATP-A",
            expected_value_per_contract=0.12,
            edge=0.07,
            available_liquidity_dollars=12.0,
            confidence=0.65,
            freshness_age_seconds=11.0,
        ),
        _accepted_row(
            canonical_match_id="match-b",
            market_ticker="KXATP-B",
            expected_value_per_contract=0.12,
            edge=0.07,
            available_liquidity_dollars=12.0,
            confidence=0.65,
            freshness_age_seconds=9.0,
        ),
    ]
    rejected_rows = [
        _rejected_row(
            canonical_match_id=None,
            market_ticker="KXATP-U",
            mapping_state="unmatched",
            mapping_confidence="exact_names",
            rejection_reason_codes=["timing_window_miss"],
        ),
        _rejected_row(
            canonical_match_id="match-x",
            market_ticker="KXATP-X",
            mapping_state="excluded",
            mapping_confidence="manual_review_required",
            rejection_reason_codes=["non_atp_event"],
        ),
        _rejected_row(
            canonical_match_id="match-y",
            market_ticker="KXATP-Y",
            mapping_state="ambiguous",
            mapping_confidence="manual_review_required",
            rejection_reason_codes=["manual_review_required", "multiple_candidate_matches"],
        ),
    ]

    report_dir = write_live_monitor_reports(
        run_id="scan-001",
        accepted_rows=accepted_rows,
        rejected_rows=rejected_rows,
        settings=settings,
    )

    assert report_dir == settings.reports_dir / "monitoring" / "scan-001"
    assert (report_dir / "summary.json").is_file()
    assert (report_dir / "accepted_opportunities.parquet").is_file()
    assert (report_dir / "rejected_opportunities.parquet").is_file()
    assert (report_dir / "ranked_opportunities.csv").is_file()

    ranked = pd.read_csv(report_dir / "ranked_opportunities.csv")
    assert ranked["canonical_match_id"].tolist() == ["match-b", "match-a", "match-c"]
    assert {"mapping_state", "mapping_confidence"}.issubset(ranked.columns)

    accepted = pd.read_parquet(report_dir / "accepted_opportunities.parquet")
    rejected = pd.read_parquet(report_dir / "rejected_opportunities.parquet")
    assert len(accepted) == 3
    assert len(rejected) == 3
    assert accepted["mapping_state"].tolist() == ["matched", "matched", "matched"]
    assert rejected["mapping_state"].tolist() == ["unmatched", "excluded", "ambiguous"]

    summary = json.loads((report_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["accepted_count"] == 3
    assert summary["rejected_count"] == 3
    assert summary["mapping_state_counts"] == {
        "matched": 3,
        "ambiguous": 1,
        "unmatched": 1,
        "excluded": 1,
    }
    assert summary["rejection_reason_counts"] == {
        "manual_review_required": 1,
        "multiple_candidate_matches": 1,
        "non_atp_event": 1,
        "timing_window_miss": 1,
    }


def _accepted_row(
    *,
    canonical_match_id: str,
    market_ticker: str,
    expected_value_per_contract: float,
    edge: float,
    available_liquidity_dollars: float,
    confidence: float,
    freshness_age_seconds: float,
) -> dict[str, object]:
    return {
        "artifact_run_id": "artifact-run",
        "canonical_match_id": canonical_match_id,
        "market_ticker": market_ticker,
        "selected_side": "positive",
        "model_probability": 0.64,
        "market_probability": 0.58,
        "edge": edge,
        "expected_value_per_contract": expected_value_per_contract,
        "available_liquidity_dollars": available_liquidity_dollars,
        "confidence": confidence,
        "selected_entry_price": 0.58,
        "entry_price_source": "reciprocal_no_bid_top_of_book",
        "freshness_age_seconds": freshness_age_seconds,
        "freshness_source": "orderbook_collected_at_utc",
        "mapping_state": "matched",
        "mapping_confidence": "exact_names",
        "rejection_reason_codes": [],
    }


def _rejected_row(
    *,
    canonical_match_id: str | None,
    market_ticker: str,
    mapping_state: str,
    mapping_confidence: str,
    rejection_reason_codes: list[str],
) -> dict[str, object]:
    return {
        "artifact_run_id": "artifact-run",
        "canonical_match_id": canonical_match_id,
        "market_ticker": market_ticker,
        "selected_side": "positive",
        "model_probability": 0.64,
        "market_probability": None,
        "edge": None,
        "expected_value_per_contract": None,
        "available_liquidity_dollars": None,
        "confidence": 0.0,
        "selected_entry_price": None,
        "entry_price_source": "",
        "freshness_age_seconds": None,
        "freshness_source": "",
        "mapping_state": mapping_state,
        "mapping_confidence": mapping_confidence,
        "rejection_reason_codes": rejection_reason_codes,
    }
