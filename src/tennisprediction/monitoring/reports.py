from __future__ import annotations

import json
from io import StringIO
from pathlib import Path

import pandas as pd
from rich.console import Console

from tennisprediction.config import Settings
from tennisprediction.monitoring.alerts import (
    build_operator_report_rows,
    build_operator_report_summary,
    render_operator_report,
)


def write_live_monitor_reports(
    *,
    run_id: str,
    accepted_rows: list[dict[str, object]],
    rejected_rows: list[dict[str, object]],
    settings: Settings,
) -> Path:
    report_dir = settings.reports_dir / "monitoring" / run_id
    report_dir.mkdir(parents=True, exist_ok=False)

    ranked_rows = build_operator_report_rows(accepted_rows)
    operator_summary = build_operator_report_summary(
        accepted_rows=accepted_rows,
        rejected_rows=rejected_rows,
    )
    _write_json(
        report_dir / "summary.json",
        {
            "accepted_count": len(accepted_rows),
            "rejected_count": len(rejected_rows),
            "mapping_state_counts": _mapping_state_counts(accepted_rows, rejected_rows),
            "rejection_reason_counts": _rejection_reason_counts(rejected_rows),
            "health_warnings": operator_summary["health_warnings"],
        },
    )
    _write_parquet(report_dir / "accepted_opportunities.parquet", ranked_rows)
    _write_parquet(report_dir / "rejected_opportunities.parquet", rejected_rows)
    _write_csv(report_dir / "ranked_opportunities.csv", ranked_rows)
    record_console = Console(record=True, width=160, file=StringIO())
    render_operator_report(
        accepted_rows=accepted_rows,
        rejected_rows=rejected_rows,
        console=record_console,
    )
    (report_dir / "operator_report.txt").write_text(
        record_console.export_text(clear=False),
        encoding="utf-8",
    )
    return report_dir


def render_live_monitor_console(
    *,
    accepted_rows: list[dict[str, object]],
    rejected_rows: list[dict[str, object]],
    console: Console | None = None,
) -> None:
    active_console = console or Console()
    render_operator_report(
        accepted_rows=accepted_rows,
        rejected_rows=rejected_rows,
        console=active_console,
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
