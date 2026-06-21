---
phase: 06-market-mapping-executable-pricing-and-live-ev-monitor
plan: 03
subsystem: api
tags: [kalshi, executable-pricing, ev, orderbook, liquidity]
requires:
  - phase: 06-market-mapping-executable-pricing-and-live-ev-monitor
    provides: persisted matched mappings with explicit YES/NO side orientation from 06-02
provides:
  - side-specific executable pricing adapter
  - executable market input contracts for yes and no sides
  - EV decision records with explicit pricing, liquidity, and freshness evidence
affects: [live-monitoring, replay, reports]
tech-stack:
  added: []
  patterns: [reciprocal bid-ladder pricing, top-of-book liquidity labeling, side-specific EV evidence]
key-files:
  created:
    - src/tennisprediction/kalshi/executable.py
    - tests/unit/test_kalshi_executable_pricing.py
    - tests/unit/test_live_scan_pricing_contract.py
  modified:
    - src/tennisprediction/backtesting/schemas.py
    - src/tennisprediction/ev/pricing.py
    - src/tennisprediction/ev/opportunity.py
key-decisions:
  - "Derived executable buy prices from the reciprocal opposing bid ladder instead of complementing one side after the fact."
  - "Locked MVP liquidity to top-of-book notional while preserving explicit source labels for later expansion."
patterns-established:
  - "Executable-side Kalshi inputs should carry explicit entry-price, liquidity, freshness, and rejection metadata per side."
  - "Opportunity records preserve accepted/rejected symmetry while surfacing the exact executable evidence used for selection."
requirements-completed: [MKT-05, MKT-06]
duration: 7min
completed: 2026-06-21
---

# Phase 06-03 Summary

**Reciprocal bid-ladder executable pricing with explicit yes/no EV contracts, liquidity labels, and freshness evidence**

## Performance

- **Duration:** 7 min
- **Started:** 2026-06-21T12:49:40-04:00
- **Completed:** 2026-06-21T12:57:02-04:00
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added an executable pricing adapter that derives buy-YES and buy-NO entry prices from the reciprocal opposing bid ladders and records top-of-book liquidity and freshness evidence.
- Extended the backtesting and EV schemas with explicit executable-side input contracts that carry canonical side orientation, rejection reasons, and pricing provenance.
- Upgraded opportunity evaluation so live pricing uses explicit yes/no entry prices and preserves entry-price, liquidity, freshness, fee, and slippage evidence on accepted and rejected records.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing executable-pricing and EV-evidence contract tests** - `53b9b36` (`test`)
2. **Task 2: Implement the executable pricing adapter and side-specific EV contracts** - `823232f` (`feat`)

**Plan metadata:** `41324d7` (`docs`)

## Files Created/Modified

- `src/tennisprediction/kalshi/executable.py` - converts persisted bid-only orderbook snapshots into explicit executable yes/no side inputs.
- `src/tennisprediction/backtesting/schemas.py` - adds executable-side input contracts and selected-entry evidence fields on decision records.
- `src/tennisprediction/ev/pricing.py` - allows candidate-side evaluation to accept explicit rejection codes and selected entry prices.
- `src/tennisprediction/ev/opportunity.py` - evaluates executable market inputs and persists side-specific pricing, liquidity, and freshness evidence.
- `tests/unit/test_kalshi_executable_pricing.py` - locks reciprocal executable pricing, stale/missing-liquidity rejection, and top-of-book semantics.
- `tests/unit/test_live_scan_pricing_contract.py` - locks explicit no-side pricing and evidence propagation into opportunity records.

## Decisions Made

- Treated reciprocal opposing bids as the canonical executable-buy source for each Kalshi side rather than relying on the old complement shortcut.
- Preserved explicit liquidity and freshness source labels in the decision contract so later monitoring and alerting can explain why a side was accepted or rejected.

## Deviations from Plan

None - plan executed as specified.

## Issues Encountered

- The initial local verification failed because the base `.venv` lacked `pandas` for replay-related tests. Running the repo-standard `uv run --group ml` verification path resolved that runtime gap and confirmed the Wave 3 contract against the intended ML dependency group.
- Ruff initially failed on three overlong test lines, which were corrected before the implementation commit.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 06 now has the executable yes/no pricing contract that `06-04` can feed into the shadow/live monitor workflow.
- The remaining Wave 4 work is now mostly orchestration, reporting, and the planned runtime checkpoint for trusted replay-backed monitoring.

---
*Phase: 06-market-mapping-executable-pricing-and-live-ev-monitor*
*Completed: 2026-06-21*
