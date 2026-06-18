---
phase: 02-leakage-safe-feature-engine
plan: 05
subsystem: features
tags: [features, leakage, match-stats, persistence, pytest]
requires:
  - phase: 02-04
    provides: Persisted feature snapshots, differential rows, and the initial FEAT-09 leakage gate
provides:
  - Collision-safe match-stat lookup keyed by source lineage instead of row number alone
  - Cross-file row-number collision regressions across state, leakage, and persistence
  - Restored FEAT-05, FEAT-08, and FEAT-09 evidence on the real multi-file canonical shape
affects: [modeling, backtesting, feature-persistence]
tech-stack:
  added: []
  patterns:
    [
      source-lineage stat lookup keyed by file path plus row number,
      multi-file regression fixtures that compare clean and colliding histories,
    ]
key-files:
  created: []
  modified:
    - src/tennisprediction/features/runner.py
    - src/tennisprediction/features/state.py
    - tests/unit/test_feature_state.py
    - tests/unit/test_feature_leakage.py
    - tests/unit/test_feature_persistence.py
key-decisions:
  - "Resolve stat lookups with a collision-safe source key, but derive the match-side file path from the corresponding `atp_matchstats_*` file family so the Phase 1 normalization contract still joins correctly."
  - "Use one duplicate-row-number regression shape across state, leakage, and persistence so FEAT-09 covers the same multi-file canonical failure that blocked verification."
patterns-established:
  - "Match-stat identity is a source-lineage concern; row number alone is never a safe key across Sackmann files."
  - "Leakage regressions for persisted features should compare clean vs colliding histories on the same historical match, not only assert one happy-path value."
requirements-completed: [FEAT-05, FEAT-08, FEAT-09]
duration: 2min
completed: 2026-06-18
---

# Phase 02 Plan 05 Summary

**Collision-safe prior match-stat lookup using stats-file lineage, with FEAT-09 regressions that prove duplicate row numbers cannot corrupt snapshots or persisted rows**

## Performance

- **Duration:** 2 min
- **Started:** 2026-06-18T21:07:18Z
- **Completed:** 2026-06-18T21:09:02Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Added failing regressions for the verified blocker in state, leakage, and persistence using a `2024` history plus a colliding `2025` stat row that reuses the same `source_row_number`.
- Replaced the integer-only match-stat index with a collision-safe `(source_file_path, source_row_number)` key and threaded that key through the runner/state update path.
- Restored trustworthy FEAT-05/08 outputs by proving the corrected lookup keeps aggregate snapshots, differential rows, and persisted feature tables bound to the right prior stat rows.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add failing cross-file collision regressions for state, leakage, and persistence** - `a48f575` (`test`)
2. **Task 2: Re-key match-stat identity with a collision-safe source key and make the regressions pass** - `adc60a8` (`feat`)

**Plan metadata:** pending docs close-out commit

## Files Created/Modified

- `src/tennisprediction/features/runner.py` - indexes `CanonicalMatchStat` rows by source-lineage key and passes the keyed lookup into batch state updates
- `src/tennisprediction/features/state.py` - derives the match-side stat lookup key from the corresponding `atp_matchstats_*` file plus row number
- `tests/unit/test_feature_state.py` - regression for player snapshot aggregates on a duplicate-row-number multi-file fixture
- `tests/unit/test_feature_leakage.py` - FEAT-09 invariant comparing clean and colliding histories for aggregate snapshot and differential fields
- `tests/unit/test_feature_persistence.py` - persistence regression proving stored `feature_differential_rows` values remain tied to the correct prior stats

## Decisions Made

- Preserved the Phase 1 normalization contract by mapping match lineage from `atp_matches_*` to the corresponding `atp_matchstats_*` file when resolving the stat lookup key, rather than changing any canonical domain model.
- Kept the regression fixture narrowly scoped to the verified blocker: one extra stat row from a different yearly Sackmann file with the same row number, no unrelated feature-family changes.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected the leakage regression to assert runner differential fields instead of persistence-only projection columns**
- **Found during:** Task 2 (Re-key match-stat identity with a collision-safe source key and make the regressions pass)
- **Issue:** The first version of the new leakage regression reached for `player_a_*` and `player_b_*` columns that exist only in persisted `feature_differential_rows`, not on the in-memory `FeatureDifferentialRow` emitted by the runner.
- **Fix:** Narrowed the invariant to the aggregate/stat differential fields that the runner actually owns: `service_first_won_rate_diff`, `return_first_won_allowed_rate_diff`, and `ace_rate_diff`.
- **Files modified:** `tests/unit/test_feature_leakage.py`
- **Verification:** `./.venv/bin/python -m pytest -q tests/unit/test_feature_state.py tests/unit/test_feature_leakage.py tests/unit/test_feature_persistence.py`
- **Committed in:** `adc60a8` (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The auto-fix corrected the regression contract without widening scope. The implemented production fix remained the planned source-lineage re-key.

## Issues Encountered

- The verified remediation needed one extra join detail: canonical matches retain `atp_matches_*` lineage while canonical stat rows retain `atp_matchstats_*` lineage, so the collision-safe key had to preserve both file-path uniqueness and the existing Phase 1 file-family boundary.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The Phase 2 verification gap is closed for the aggregate/stat path: duplicate row numbers across Sackmann files no longer corrupt prior-only snapshots or persisted outputs.
- Downstream modeling, backtesting, and live-prediction phases can continue consuming persisted Phase 2 feature artifacts without recomputing or second-guessing match-stat identity.

## Self-Check: PASSED

- Verified `.planning/phases/02-leakage-safe-feature-engine/02-05-SUMMARY.md` exists on disk.
- Verified task commits `a48f575` and `adc60a8` exist in git history.
- Re-ran plan verification: initial RED check failed before implementation, targeted collision regressions passed after implementation, and `./.venv/bin/python -m pytest -q tests/unit/test_feature_*.py` passed.
