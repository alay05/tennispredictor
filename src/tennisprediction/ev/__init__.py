"""EV decision-core package."""

from tennisprediction.backtesting.schemas import (
    DecisionThresholds,
    NormalizedMarketInput,
    OpportunityDecisionBatch,
    OpportunityDecisionRecord,
)
from tennisprediction.ev.opportunity import evaluate_opportunities
from tennisprediction.ev.pricing import evaluate_candidate_side

__all__ = [
    "DecisionThresholds",
    "NormalizedMarketInput",
    "OpportunityDecisionBatch",
    "OpportunityDecisionRecord",
    "evaluate_candidate_side",
    "evaluate_opportunities",
]
