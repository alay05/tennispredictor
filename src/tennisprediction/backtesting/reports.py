from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

import pandas as pd

from tennisprediction.backtesting.metrics import BacktestSummary, BacktestUncertainty
from tennisprediction.backtesting.provenance import (
    build_provenance_payload,
    guard_profitability_claims,
)
from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    OpportunityDecisionBatch,
    OpportunityDecisionRecord,
)
from tennisprediction.config import Settings


def write_backtest_reports(
    run_id: str,
    batch: OpportunityDecisionBatch,
    summary: BacktestSummary,
    uncertainty: BacktestUncertainty,
    settings: Settings,
) -> Path:
    report_dir = settings.reports_dir / "backtesting" / run_id
    report_dir.mkdir(parents=True, exist_ok=False)

    claim_guard = guard_profitability_claims(
        summary,
        uncertainty,
        provenance_label=batch.provenance_label,
        assumption_notes=batch.assumption_notes,
    )

    _write_json(
        report_dir / "summary.json",
        {
            **asdict(summary),
            "equity_curve": [asdict(row) for row in summary.equity_curve],
            "claim_allowed": claim_guard.allowed,
            "claim_banner": claim_guard.banner,
        },
    )
    _write_json(report_dir / "uncertainty.json", asdict(uncertainty))
    _write_json(report_dir / "provenance.json", build_provenance_payload(batch, claim_guard))
    _write_parquet(
        report_dir / "accepted_opportunities.parquet",
        [_serializable_record(record) for record in batch.accepted_records],
    )
    _write_parquet(
        report_dir / "rejected_opportunities.parquet",
        [_serializable_record(record) for record in batch.rejected_records],
    )
    _write_csv(
        report_dir / "decision_reason_counts.csv",
        _reason_counts(batch),
    )
    _write_csv(
        report_dir / "equity_curve.csv",
        [asdict(row) for row in summary.equity_curve],
    )
    return report_dir


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame.from_records(rows).to_csv(path, index=False)


def _write_parquet(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame.from_records(rows).to_parquet(path, index=False)


def _serializable_record(record: OpportunityDecisionRecord) -> dict[str, object]:
    payload = asdict(record)
    provenance_label = payload.get("provenance_label")
    if isinstance(provenance_label, BacktestProvenanceLabel):
        payload["provenance_label"] = provenance_label.value
    threshold_snapshot = payload.get("threshold_snapshot")
    if isinstance(threshold_snapshot, dict):
        payload["threshold_snapshot"] = json.dumps(
            threshold_snapshot,
            sort_keys=True,
        )
    reason_codes = payload.get("rejection_reason_codes")
    if isinstance(reason_codes, tuple):
        payload["rejection_reason_codes"] = list(reason_codes)
    return dict(payload)


def _reason_counts(batch: OpportunityDecisionBatch) -> list[dict[str, object]]:
    counts: dict[str, int] = {}
    for record in batch.rejected_records:
        for reason_code in record.rejection_reason_codes:
            counts[reason_code] = counts.get(reason_code, 0) + 1
    return [
        {"reason_code": reason_code, "count": count}
        for reason_code, count in sorted(counts.items())
    ]
