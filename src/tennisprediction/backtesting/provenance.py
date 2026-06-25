from __future__ import annotations

from dataclasses import dataclass

from tennisprediction.backtesting.metrics import BacktestSummary, BacktestUncertainty
from tennisprediction.backtesting.schemas import BacktestProvenanceLabel, OpportunityDecisionBatch


@dataclass(frozen=True)
class BacktestClaimGuard:
    allowed: bool
    banner: str


def guard_profitability_claims(
    summary: BacktestSummary,
    uncertainty: BacktestUncertainty,
    *,
    provenance_label: BacktestProvenanceLabel,
    assumption_notes: str,
) -> BacktestClaimGuard:
    if summary.sample_size <= 0:
        return BacktestClaimGuard(
            allowed=False,
            banner="Profitability claims suppressed: sample size is zero.",
        )
    if not assumption_notes.strip():
        return BacktestClaimGuard(
            allowed=False,
            banner="Profitability claims suppressed: assumption notes are required.",
        )
    if uncertainty.sample_size != summary.sample_size:
        return BacktestClaimGuard(
            allowed=False,
            banner="Profitability claims suppressed: uncertainty metadata is incomplete.",
        )
    if provenance_label is not BacktestProvenanceLabel.actual_kalshi_historical:
        return BacktestClaimGuard(
            allowed=False,
            banner=(
                f"Profitability claims suppressed: {provenance_label.value} "
                "is not actual historical Kalshi evidence."
            ),
        )
    return BacktestClaimGuard(
        allowed=True,
        banner=(
            f"Backtest profitability claim allowed for {summary.sample_size} accepted records "
            f"with ROI {summary.roi:.4f}."
        ),
    )


def build_provenance_payload(
    batch: OpportunityDecisionBatch,
    claim_guard: BacktestClaimGuard,
) -> dict[str, object]:
    return {
        "run_id": batch.run_id,
        "artifact_run_id": batch.artifact_run_id,
        "feature_version": batch.feature_version,
        "split_manifest_id": batch.split_manifest_id,
        "source_commit_sha": batch.source_commit_sha,
        "provenance_label": batch.provenance_label.value,
        "assumption_notes": batch.assumption_notes,
        "thresholds": batch.thresholds.as_dict(),
        "claim_allowed": claim_guard.allowed,
        "claim_banner": claim_guard.banner,
    }
