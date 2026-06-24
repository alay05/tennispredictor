from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from rich.console import Console
from rich.table import Table

from tennisprediction.config import Settings


def write_live_monitor_reports(
    *,
    run_id: str,
    accepted_rows: list[dict[str, object]],
    rejected_rows: list[dict[str, object]],
    settings: Settings,
) -> Path:
    report_dir = settings.reports_dir / "monitoring" / run_id
    report_dir.mkdir(parents=True, exist_ok=False)

    ranked_rows = _rank_accepted_rows(accepted_rows)
    _write_json(
        report_dir / "summary.json",
        {
            "accepted_count": len(accepted_rows),
            "rejected_count": len(rejected_rows),
            "mapping_state_counts": _mapping_state_counts(accepted_rows, rejected_rows),
            "rejection_reason_counts": _rejection_reason_counts(rejected_rows),
        },
    )
    _write_parquet(report_dir / "accepted_opportunities.parquet", ranked_rows)
    _write_parquet(report_dir / "rejected_opportunities.parquet", rejected_rows)
    _write_csv(report_dir / "ranked_opportunities.csv", ranked_rows)
    return report_dir


def render_live_monitor_console(
    *,
    accepted_rows: list[dict[str, object]],
    rejected_rows: list[dict[str, object]],
    console: Console | None = None,
) -> None:
    active_console = console or Console()
    table = Table(title="Accepted Opportunities")
    table.add_column("Ticker")
    table.add_column("Match")
    table.add_column("EV")
    table.add_column("Edge")
    table.add_column("Liquidity")
    table.add_column("Confidence")
    table.add_column("Freshness")
    table.add_column("Mapping")
    for row in _rank_accepted_rows(accepted_rows):
        table.add_row(
            str(row.get("market_ticker", "")),
            str(row.get("canonical_match_id", "")),
            _format_float(row.get("expected_value_per_contract")),
            _format_float(row.get("edge")),
            _format_float(row.get("available_liquidity_dollars")),
            _format_float(row.get("confidence")),
            _format_float(row.get("freshness_age_seconds")),
            f"{row.get('mapping_state', '')}/{row.get('mapping_confidence', '')}",
        )
    active_console.print(table)
    active_console.print(
        {
            "accepted_count": len(accepted_rows),
            "rejected_count": len(rejected_rows),
            "mapping_state_counts": _mapping_state_counts(accepted_rows, rejected_rows),
            "rejection_reason_counts": _rejection_reason_counts(rejected_rows),
        }
    )


def _rank_accepted_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (
            -_float_or_default(row.get("expected_value_per_contract"), float("-inf")),
            -_float_or_default(row.get("edge"), float("-inf")),
            -_float_or_default(row.get("available_liquidity_dollars"), float("-inf")),
            -_float_or_default(row.get("confidence"), float("-inf")),
            _float_or_default(row.get("freshness_age_seconds"), float("inf")),
        ),
    )


def _mapping_state_counts(
    accepted_rows: list[dict[str, object]],
    rejected_rows: list[dict[str, object]],
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in [*accepted_rows, *rejected_rows]:
        state = str(row.get("mapping_state", ""))
        counts[state] = counts.get(state, 0) + 1
    return dict(sorted(counts.items()))


def _rejection_reason_counts(rejected_rows: list[dict[str, object]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rejected_rows:
        reason_codes = row.get("rejection_reason_codes", [])
        if not isinstance(reason_codes, list):
            continue
        for reason_code in reason_codes:
            counts[str(reason_code)] = counts.get(str(reason_code), 0) + 1
    return dict(sorted(counts.items()))


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame.from_records(rows).to_csv(path, index=False)


def _write_parquet(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame.from_records(rows).to_parquet(path, index=False)


def _float_or_default(value: object, default: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    return default


def _format_float(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{float(value):.3f}"
    return ""
