---
phase: 07-alerts-and-operational-hardening
plan: 01
subsystem: infra
tags: [monitoring, reports, rich, kalshi, operations]
requires:
  - phase: 06-market-mapping-executable-pricing-and-live-ev-monitor
    provides: ranked accepted/rejected monitoring rows and the canonical `reports/monitoring/<run_id>` artifact seam
  - phase: 07-alerts-and-operational-hardening
    provides: one-shot CLI/report configuration from 07-03
provides:
  - advisory operator report rows derived from the canonical monitoring outputs
  - persisted `operator_report.txt` exports inside `reports/monitoring/<run_id>`
  - terminal/file-only recommendation labels plus health-warning context for live monitoring runs
affects: [live-monitoring, reporting, cli]
tech-stack:
  added: []
  patterns: [shared ranked-row contract, rich record-and-export, advisory-only monitoring labels]
key-files:
  created:
    - src/tennisprediction/monitoring/alerts.py
  modified:
    - src/tennisprediction/monitoring/__init__.py
    - src/tennisprediction/monitoring/reports.py
    - tests/unit/test_live_monitor_reports.py
key-decisions:
  - "Used `monitoring/alerts.py` as a downstream presentation seam so the operator report is built from the existing Phase 06 monitoring rows instead of a second storage path."
  - "Recommendation labels stay advisory-only while stale-quote, thin-liquidity, and manual-review conditions surface separately as health warnings."
patterns-established:
  - "Accepted monitoring rows can be enriched with operator-facing fields like `recommendation` without forking the persisted Phase 06 artifact directory."
  - "One Rich render path should serve both terminal output and persisted text exports via `Console(record=True)`."
requirements-completed: [OPS-01, OPS-02]
duration: 6min
completed: 2026-06-25
---

# Phase 07 Plan 01: Opportunity Reports and Configurable Alert Settings Summary

**Advisory monitoring reports now persist a Rich-backed operator summary with ranked ATP-to-Kalshi opportunities, health warnings, and read-only recommendation labels**

## Performance

- **Duration:** 6 min
- **Started:** 2026-06-25T08:04:46-04:00
- **Completed:** 2026-06-25T08:11:02-04:00
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Added a dedicated `monitoring/alerts.py` presentation seam that turns accepted monitoring rows into operator-facing ranked report rows with advisory recommendation labels.
- Extended `write_live_monitor_reports()` to keep the existing Phase 06 machine-readable outputs and add a persisted `operator_report.txt` in the same `reports/monitoring/<run_id>` directory.
- Upgraded terminal rendering to the same advisory report surface so accepted opportunities, rejected or excluded counts, and health warnings stay consistent across terminal and file outputs.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing tests for the enriched advisory report contract** - `037c9a9` (test)
2. **Task 2: Implement the advisory terminal/file report on top of the Phase 06 seam** - `187e026` (feat)

## Files Created/Modified

- `src/tennisprediction/monitoring/alerts.py` - builds ranked operator report rows, advisory recommendation labels, and health-warning summaries for Rich rendering.
- `src/tennisprediction/monitoring/reports.py` - persists the new operator report file while keeping the canonical summary, parquet, and CSV outputs intact.
- `src/tennisprediction/monitoring/__init__.py` - exports the new alert/report presentation seam.
- `tests/unit/test_live_monitor_reports.py` - locks the persisted operator report, required OPS-01 fields, advisory-only wording, and health-warning context.

## Decisions Made

- Kept the new operator-facing report downstream of the Phase 06 monitoring row contract so accepted/rejected artifact truth remains auditable from one seam.
- Used recommendation labels such as `High-priority review`, `Review`, and `Watchlist` instead of any execution-oriented verbs to preserve the read-only v1 boundary.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected a stale ranking expectation in the RED test contract**
- **Found during:** Task 2 (Implement the advisory terminal/file report on top of the Phase 06 seam)
- **Issue:** The RED fixture changed `match-b` liquidity and freshness to trigger health warnings, but one ranking assertion still expected the older Phase 06 ordering.
- **Fix:** Updated the test expectation to match the real EV/edge/liquidity ranking contract that Phase 06 already defined.
- **Files modified:** `tests/unit/test_live_monitor_reports.py`
- **Verification:** `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_live_monitor_reports.py -x`
- **Committed in:** `187e026` (part of task commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The correction kept the TDD contract aligned with the existing ranking semantics and avoided a false regression.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 07 now has an operator-facing report seam that later logging, CLI, and documentation work can reuse without introducing a second artifact path.
- The persisted `operator_report.txt` and enriched ranked rows give the remaining operational-hardening plans one stable report contract to build on.

## Self-Check: PASSED

- Found `.planning/phases/07-alerts-and-operational-hardening/07-01-SUMMARY.md` on disk.
- Verified task commits `037c9a9` and `187e026` exist in git history.
