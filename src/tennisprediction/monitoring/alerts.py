from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.table import Table

STALE_QUOTE_SECONDS = 30 * 60
THIN_LIQUIDITY_DOLLARS = 10.0


def build_operator_report_rows(
    accepted_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    ranked_rows = sorted(
        accepted_rows,
        key=lambda row: (
            -_float_or_default(row.get("expected_value_per_contract"), float("-inf")),
            -_float_or_default(row.get("edge"), float("-inf")),
            -_float_or_default(row.get("available_liquidity_dollars"), float("-inf")),
            -_float_or_default(row.get("confidence"), float("-inf")),
            _float_or_default(row.get("freshness_age_seconds"), float("inf")),
        ),
    )
    return [_build_operator_row(row) for row in ranked_rows]


def build_operator_report_summary(
    *,
    accepted_rows: list[dict[str, object]],
    rejected_rows: list[dict[str, object]],
) -> dict[str, object]:
    excluded_count = _count_mapping_state(rejected_rows, "excluded")
    ambiguous_count = _count_mapping_state(rejected_rows, "ambiguous")
    unmatched_count = _count_mapping_state(rejected_rows, "unmatched")
    stale_count = sum(
        1
        for row in accepted_rows
        if _float_or_default(row.get("freshness_age_seconds"), 0.0) >= STALE_QUOTE_SECONDS
    )
    thin_liquidity_count = sum(
        1
        for row in accepted_rows
        if 0.0
        < _float_or_default(row.get("available_liquidity_dollars"), 0.0)
        < THIN_LIQUIDITY_DOLLARS
    )

    health_warnings: list[str] = []
    if stale_count:
        health_warnings.append("Stale quotes detected")
    if thin_liquidity_count:
        health_warnings.append("Thin liquidity detected")
    if ambiguous_count or unmatched_count or _requires_manual_review(rejected_rows):
        health_warnings.append("Manual review required")

    return {
        "accepted_count": len(accepted_rows),
        "rejected_count": len(rejected_rows),
        "excluded_count": excluded_count,
        "ambiguous_count": ambiguous_count,
        "unmatched_count": unmatched_count,
        "stale_count": stale_count,
        "thin_liquidity_count": thin_liquidity_count,
        "health_warnings": health_warnings,
    }


def render_operator_report(
    *,
    accepted_rows: list[dict[str, object]],
    rejected_rows: list[dict[str, object]],
    console: Console,
) -> None:
    summary = build_operator_report_summary(
        accepted_rows=accepted_rows,
        rejected_rows=rejected_rows,
    )
    ranked_rows = build_operator_report_rows(accepted_rows)

    console.rule("ATP Kalshi Opportunity Advisory")
    console.print("Advisory only: operator review surface. No execution is performed.")
    console.print(
        "Accepted: {accepted} | Rejected: {rejected} | Excluded: {excluded}".format(
            accepted=summary["accepted_count"],
            rejected=summary["rejected_count"],
            excluded=summary["excluded_count"],
        )
    )
    console.print(
        "Ambiguous mappings: {ambiguous} | Unmatched markets: {unmatched}".format(
            ambiguous=summary["ambiguous_count"],
            unmatched=summary["unmatched_count"],
        )
    )
    if summary["health_warnings"]:
        console.print("Health warnings")
        for warning in summary["health_warnings"]:
            console.print(f"- {warning}")

    table = Table(title="Accepted Opportunities")
    table.add_column("Match")
    table.add_column("Ticker")
    table.add_column("Model")
    table.add_column("Market")
    table.add_column("Edge")
    table.add_column("EV")
    table.add_column("Liquidity")
    table.add_column("Mapping")
    table.add_column("Recommendation")

    for row in ranked_rows:
        table.add_row(
            str(row.get("matchup", row.get("canonical_match_id", ""))),
            str(row.get("market_ticker", "")),
            _format_probability(row.get("model_probability")),
            _format_probability(row.get("market_probability")),
            _format_probability(row.get("edge")),
            _format_probability(row.get("expected_value_per_contract")),
            _format_currency(row.get("available_liquidity_dollars")),
            str(row.get("mapping_confidence", "")),
            str(row.get("recommendation", "")),
        )
    console.print(table)


def _build_operator_row(row: dict[str, object]) -> dict[str, object]:
    operator_row = dict(row)
    operator_row["matchup"] = str(
        row.get("matchup") or row.get("canonical_match_id") or row.get("market_ticker") or ""
    )
    operator_row["recommendation"] = _recommendation_label(row)
    return operator_row


def _recommendation_label(row: dict[str, object]) -> str:
    expected_value = _float_or_default(row.get("expected_value_per_contract"), 0.0)
    edge = _float_or_default(row.get("edge"), 0.0)
    liquidity = _float_or_default(row.get("available_liquidity_dollars"), 0.0)
    freshness = _float_or_default(row.get("freshness_age_seconds"), 0.0)
    if (
        expected_value >= 0.12
        and edge >= 0.07
        and liquidity >= THIN_LIQUIDITY_DOLLARS
        and freshness < STALE_QUOTE_SECONDS
    ):
        return "High-priority review"
    if expected_value >= 0.10 and edge >= 0.05:
        return "Review"
    return "Watchlist"


def _requires_manual_review(rows: list[dict[str, object]]) -> bool:
    return any(
        str(row.get("mapping_confidence", "")) == "manual_review_required"
        or "manual_review_required" in row.get("rejection_reason_codes", [])
        for row in rows
    )


def _count_mapping_state(rows: list[dict[str, object]], mapping_state: str) -> int:
    return sum(1 for row in rows if str(row.get("mapping_state", "")) == mapping_state)


def _float_or_default(value: object, default: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    return default


def _format_probability(value: Any) -> str:
    if isinstance(value, int | float):
        return f"{float(value) * 100:.1f}%"
    return ""


def _format_currency(value: Any) -> str:
    if isinstance(value, int | float):
        return f"${float(value):.2f}"
    return ""
