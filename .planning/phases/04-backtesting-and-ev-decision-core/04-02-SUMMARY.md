---
phase: 04-backtesting-and-ev-decision-core
plan: 02
type: summary
date: 2026-06-20
---

# Phase 04-02 Summary

Implemented the EV decision core in `src/tennisprediction/ev/pricing.py` and `src/tennisprediction/ev/opportunity.py`.

The decision engine now evaluates both positive and negative sides from normalized market inputs, applies threshold snapshots, records accepted and rejected opportunity records with reason codes, and preserves the normalized market-probability/liquidity contract required by the phase plan.

Verification:
- `python3 -m uv run pytest -q tests/unit/test_backtesting_decisions.py -x`
- `python3 -m uv run pytest -q tests/unit/test_backtesting_*.py -x`
