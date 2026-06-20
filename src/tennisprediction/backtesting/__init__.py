"""Backtesting and EV decision-core package."""

from tennisprediction.backtesting.metrics import (
    BacktestSummary,
    BacktestUncertainty,
    EquityCurvePoint,
    estimate_backtest_uncertainty,
    summarize_backtest,
)
from tennisprediction.backtesting.provenance import guard_profitability_claims
from tennisprediction.backtesting.replay import replay_model_predictions
from tennisprediction.backtesting.reports import write_backtest_reports
from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    DecisionThresholds,
    NormalizedMarketInput,
    OpportunityDecisionBatch,
    OpportunityDecisionRecord,
    ReplayPredictionRow,
    ReplayRunResult,
)

__all__ = [
    "BacktestProvenanceLabel",
    "BacktestSummary",
    "BacktestUncertainty",
    "DecisionThresholds",
    "EquityCurvePoint",
    "OpportunityDecisionBatch",
    "OpportunityDecisionRecord",
    "NormalizedMarketInput",
    "ReplayPredictionRow",
    "ReplayRunResult",
    "estimate_backtest_uncertainty",
    "guard_profitability_claims",
    "replay_model_predictions",
    "summarize_backtest",
    "write_backtest_reports",
]
