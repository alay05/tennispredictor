from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    DecisionThresholds,
)


@dataclass(frozen=True)
class SideEvaluation:
    side: Literal["positive", "negative"]
    model_probability: float
    market_probability: float | None
    entry_price: float | None
    confidence: float
    edge: float | None
    expected_value_per_contract: float | None
    accepted: bool
    reason_codes: tuple[str, ...]


def evaluate_candidate_side(
    *,
    side: Literal["positive", "negative"],
    model_probability: float,
    market_probability: float | None,
    available_liquidity_dollars: float | None,
    thresholds: DecisionThresholds,
    provenance_label: object,
    rejection_reason_codes: tuple[str, ...] = (),
) -> SideEvaluation:
    reason_codes: list[str] = list(rejection_reason_codes)
    if not _is_supported_provenance(provenance_label):
        reason_codes.append("unsupported_provenance")

    if market_probability is None:
        reason_codes.append("missing_market_probability")
    elif not 0.0 <= market_probability <= 1.0:
        reason_codes.append("invalid_probability_bounds")

    if available_liquidity_dollars is None:
        reason_codes.append("missing_liquidity")
    elif available_liquidity_dollars < thresholds.min_liquidity:
        reason_codes.append("below_min_liquidity")

    edge = None
    expected_value_per_contract = None
    if market_probability is not None and 0.0 <= market_probability <= 1.0:
        edge = model_probability - market_probability
        expected_value_per_contract = (
            edge - thresholds.fee_per_contract - thresholds.slippage_per_contract
        )
        if edge < thresholds.min_edge:
            reason_codes.append("below_min_edge")
        if model_probability < thresholds.min_confidence:
            reason_codes.append("below_min_confidence")

    accepted = not reason_codes
    return SideEvaluation(
        side=side,
        model_probability=model_probability,
        market_probability=market_probability,
        entry_price=market_probability,
        confidence=model_probability,
        edge=edge,
        expected_value_per_contract=expected_value_per_contract,
        accepted=accepted,
        reason_codes=tuple(sorted(set(reason_codes))),
    )


def _is_supported_provenance(provenance_label: object) -> bool:
    if isinstance(provenance_label, BacktestProvenanceLabel):
        return True
    if isinstance(provenance_label, str):
        return provenance_label in {label.value for label in BacktestProvenanceLabel}
    return False
