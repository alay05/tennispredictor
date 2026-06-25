from __future__ import annotations

from dataclasses import dataclass
from random import Random

from tennisprediction.backtesting.schemas import (
    OpportunityDecisionBatch,
    OpportunityDecisionRecord,
)


@dataclass(frozen=True)
class EquityCurvePoint:
    as_of_date: str
    canonical_match_id: str
    cumulative_profit: float
    cumulative_roi: float
    peak_profit: float
    drawdown: float


@dataclass(frozen=True)
class BacktestSummary:
    run_id: str
    artifact_run_id: str
    feature_version: str
    split_manifest_id: str
    provenance_label: str
    assumption_notes: str
    sample_size: int
    accepted_count: int
    rejected_count: int
    win_rate: float
    average_edge: float
    gross_profit: float
    net_profit: float
    roi: float
    total_staked: float
    max_drawdown: float
    equity_curve: list[EquityCurvePoint]


@dataclass(frozen=True)
class BacktestUncertainty:
    sample_size: int
    confidence_level: float
    method: str
    net_profit_lower: float
    net_profit_upper: float
    roi_lower: float
    roi_upper: float


def summarize_backtest(batch: OpportunityDecisionBatch) -> BacktestSummary:
    accepted_records = _chronological_records(batch.accepted_records)
    rejected_count = len(batch.rejected_records)
    sample_size = len(accepted_records)

    total_edge = sum(record.edge or 0.0 for record in accepted_records)
    total_profit = sum(record.realized_pnl or 0.0 for record in accepted_records)
    gross_profit = sum(max(record.realized_pnl or 0.0, 0.0) for record in accepted_records)
    total_staked = sum(
        (record.market_probability or 0.0)
        + batch.thresholds.fee_per_contract
        + batch.thresholds.slippage_per_contract
        for record in accepted_records
    )

    equity_curve: list[EquityCurvePoint] = []
    cumulative_profit = 0.0
    cumulative_staked = 0.0
    peak_profit = 0.0
    max_drawdown = 0.0
    wins = 0
    for record in accepted_records:
        cumulative_profit += record.realized_pnl or 0.0
        cumulative_staked += (
            (record.market_probability or 0.0)
            + batch.thresholds.fee_per_contract
            + batch.thresholds.slippage_per_contract
        )
        peak_profit = max(peak_profit, cumulative_profit)
        drawdown = peak_profit - cumulative_profit
        max_drawdown = max(max_drawdown, drawdown)
        if (record.realized_pnl or 0.0) > 0.0:
            wins += 1
        equity_curve.append(
            EquityCurvePoint(
                as_of_date=record.as_of_date,
                canonical_match_id=record.canonical_match_id,
                cumulative_profit=cumulative_profit,
                cumulative_roi=(cumulative_profit / cumulative_staked)
                if cumulative_staked > 0.0
                else 0.0,
                peak_profit=peak_profit,
                drawdown=drawdown,
            )
        )

    return BacktestSummary(
        run_id=batch.run_id,
        artifact_run_id=batch.artifact_run_id,
        feature_version=batch.feature_version,
        split_manifest_id=batch.split_manifest_id,
        provenance_label=batch.provenance_label.value,
        assumption_notes=batch.assumption_notes,
        sample_size=sample_size,
        accepted_count=sample_size,
        rejected_count=rejected_count,
        win_rate=(wins / sample_size) if sample_size > 0 else 0.0,
        average_edge=(total_edge / sample_size) if sample_size > 0 else 0.0,
        gross_profit=gross_profit,
        net_profit=total_profit,
        roi=(total_profit / total_staked) if total_staked > 0.0 else 0.0,
        total_staked=total_staked,
        max_drawdown=max_drawdown,
        equity_curve=equity_curve,
    )


def estimate_backtest_uncertainty(
    batch: OpportunityDecisionBatch,
    *,
    confidence_level: float = 0.95,
    bootstrap_samples: int = 512,
) -> BacktestUncertainty:
    accepted_records = _chronological_records(batch.accepted_records)
    if not accepted_records:
        return BacktestUncertainty(
            sample_size=0,
            confidence_level=confidence_level,
            method="bootstrap",
            net_profit_lower=0.0,
            net_profit_upper=0.0,
            roi_lower=0.0,
            roi_upper=0.0,
        )

    realized_pnls = [record.realized_pnl or 0.0 for record in accepted_records]
    staked = [
        (record.market_probability or 0.0)
        + batch.thresholds.fee_per_contract
        + batch.thresholds.slippage_per_contract
        for record in accepted_records
    ]
    rng = Random(42)
    net_profit_samples: list[float] = []
    roi_samples: list[float] = []
    for _ in range(bootstrap_samples):
        sample_indices = [rng.randrange(len(realized_pnls)) for _ in range(len(realized_pnls))]
        sample_profit = sum(realized_pnls[index] for index in sample_indices)
        sample_staked = sum(staked[index] for index in sample_indices)
        net_profit_samples.append(sample_profit)
        roi_samples.append((sample_profit / sample_staked) if sample_staked > 0.0 else 0.0)

    lower_quantile = (1.0 - confidence_level) / 2.0
    upper_quantile = 1.0 - lower_quantile
    return BacktestUncertainty(
        sample_size=len(accepted_records),
        confidence_level=confidence_level,
        method="bootstrap",
        net_profit_lower=_quantile(net_profit_samples, lower_quantile),
        net_profit_upper=_quantile(net_profit_samples, upper_quantile),
        roi_lower=_quantile(roi_samples, lower_quantile),
        roi_upper=_quantile(roi_samples, upper_quantile),
    )


def _chronological_records(
    records: list[OpportunityDecisionRecord],
) -> list[OpportunityDecisionRecord]:
    return sorted(records, key=lambda record: (record.as_of_date, record.canonical_match_id))


def _quantile(values: list[float], quantile: float) -> float:
    ordered_values = sorted(values)
    if not ordered_values:
        return 0.0
    if quantile <= 0.0:
        return ordered_values[0]
    if quantile >= 1.0:
        return ordered_values[-1]
    position = quantile * (len(ordered_values) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered_values) - 1)
    fraction = position - lower_index
    return ordered_values[lower_index] * (1.0 - fraction) + ordered_values[upper_index] * fraction
