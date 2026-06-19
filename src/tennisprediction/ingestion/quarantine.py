from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tennisprediction.ingestion.sackmann_contracts import classify_file_scope
from tennisprediction.ingestion.validation import FileQuarantineRecord, ValidatedSnapshot


@dataclass(frozen=True)
class QuarantineDecision:
    accepted: bool
    reason: str | None = None


@dataclass(frozen=True)
class PartitionedSnapshot:
    accepted_rows: dict[str, list[dict[str, str]]]
    quarantined_rows: dict[str, list[dict[str, str]]]
    quarantined_files: dict[str, FileQuarantineRecord]


def classify_row(relative_path: str | Path, row: dict[str, str]) -> QuarantineDecision:
    scope = classify_file_scope(relative_path)
    if not scope.accepted:
        return QuarantineDecision(accepted=False, reason=scope.reason)

    comment = row.get("comment", "").strip().lower()
    score = row.get("score", "").strip().lower()
    round_name = row.get("round", "").strip().upper()

    if comment in {"retired", "walkover", "incomplete"}:
        return QuarantineDecision(accepted=False, reason=f"excluded_{comment}")
    if "w/o" in score or "walkover" in score:
        return QuarantineDecision(accepted=False, reason="excluded_walkover")
    if round_name in {"Q1", "Q2", "Q3", "QR"}:
        return QuarantineDecision(accepted=False, reason="excluded_qualifier")

    return QuarantineDecision(accepted=True)


def split_validated_snapshot(
    validated_snapshot: ValidatedSnapshot,
) -> PartitionedSnapshot:
    accepted_rows: dict[str, list[dict[str, str]]] = {}
    quarantined_rows: dict[str, list[dict[str, str]]] = {}

    for relative_path, rows in validated_snapshot.rows_by_file.items():
        for row in rows:
            decision = classify_row(relative_path, row)
            target = accepted_rows if decision.accepted else quarantined_rows
            quarantined_row = {**row, "_quarantine_reason": decision.reason or "unknown"}
            target.setdefault(relative_path, []).append(
                row if decision.accepted else quarantined_row
            )

    return PartitionedSnapshot(
        accepted_rows=accepted_rows,
        quarantined_rows=quarantined_rows,
        quarantined_files=validated_snapshot.quarantined_files,
    )
