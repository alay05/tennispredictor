---
phase: 06-market-mapping-executable-pricing-and-live-ev-monitor
plan: 02
subsystem: api
tags: [kalshi, atp, market-mapping, duckdb, resolver]
requires:
  - phase: 06-market-mapping-executable-pricing-and-live-ev-monitor
    provides: deterministic player normalization and auditable alias overrides from 06-01
provides:
  - fail-closed market-to-match resolution states
  - persisted mapping evidence rows with side-orientation fields
  - reusable matched-only scoring gate
affects: [executable-pricing, live-monitoring, backtesting]
tech-stack:
  added: []
  patterns: [evidence-row persistence, matched-only scorer gate, deterministic mapping confidence tiers]
key-files:
  created:
    - src/tennisprediction/market_mapping/resolver.py
    - tests/unit/test_market_mapping_resolver.py
    - tests/unit/test_live_scan_rejections.py
  modified:
    - src/tennisprediction/market_mapping/__init__.py
    - src/tennisprediction/market_mapping/schemas.py
key-decisions:
  - "Started timing alignment with same-date canonical-match matching only and failed closed on misses."
  - "Persisted explicit YES/NO orientation fields so downstream pricing never has to infer player-side identity from title text."
patterns-established:
  - "Resolver outputs should persist auditable evidence for every market attempt, including excluded and unmatched rows."
  - "Only `matched` rows with non-manual-review confidence may cross into pricing or EV evaluation."
requirements-completed: [MKT-03, MKT-04]
duration: 6min
completed: 2026-06-21
---

# Phase 06-02 Summary

**Fail-closed Kalshi market-to-ATP match resolution with persisted evidence rows and explicit YES/NO side orientation**

## Performance

- **Duration:** 6 min
- **Started:** 2026-06-21T12:36:44-04:00
- **Completed:** 2026-06-21T12:42:44-04:00
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added a resolver that classifies Kalshi ATP winner markets into `matched`, `ambiguous`, `unmatched`, or `excluded` using deterministic identity, same-date timing, and side-semantics evidence.
- Persisted `market_mapping_evidence` rows with raw strings, normalized strings, candidate match IDs, deterministic confidence tiers, and explicit YES/NO orientation fields.
- Added a reusable `require_matched_mapping()` gate and focused regression coverage that prevents unresolved mappings from reaching later pricing or EV logic.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing mapping-state and unresolved-market rejection tests** - `431da18` (`test`)
2. **Task 2: Implement fail-closed mapping resolution and evidence persistence** - `5b1c982` (`feat`)

**Plan metadata:** `41324d7` (`docs`)

## Files Created/Modified

- `src/tennisprediction/market_mapping/resolver.py` - resolves latest Kalshi snapshot rows into persisted mapping evidence and matched-only scorer inputs.
- `src/tennisprediction/market_mapping/schemas.py` - adds mapping state, confidence, evidence-row, and unscorable-record contracts.
- `src/tennisprediction/market_mapping/__init__.py` - exports the resolver surface for later executable-pricing and monitoring slices.
- `tests/unit/test_market_mapping_resolver.py` - locks matched, ambiguous, unmatched, excluded, and orientation-persistence behavior.
- `tests/unit/test_live_scan_rejections.py` - locks the fail-closed scorer gate for unresolved and manual-review mappings.

## Decisions Made

- Used same-day canonical match alignment as the initial timing rule instead of silently widening the match window.
- Carried explicit `yes_canonical_player_id`, `no_canonical_player_id`, `yes_maps_to_player_a`, and `no_maps_to_player_b` through the evidence contract so later slices can consume orientation deterministically.

## Deviations from Plan

None - plan executed as specified.

## Issues Encountered

- The executor hit the main-checkout git permission boundary again during both RED and GREEN commit steps, so the orchestrator recorded the required atomic commits with elevated repo-write permission after verifying the code and tests.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 06 now has the exact mapping contract that `06-03` needs for executable-side pricing and EV evaluation.
- Later monitor/report code can consume persisted mapping confidence and side-orientation fields without reopening resolver semantics.

---
*Phase: 06-market-mapping-executable-pricing-and-live-ev-monitor*
*Completed: 2026-06-21*
