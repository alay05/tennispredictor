---
phase: 07-alerts-and-operational-hardening
plan: 03
subsystem: cli
tags: [typer, pydantic-settings, duckdb, operations, testing]
requires:
  - phase: 06-market-mapping-executable-pricing-and-live-ev-monitor
    provides: read-only Kalshi snapshot collection, artifact replay, and monitoring report primitives
provides:
  - packaged `tennisprediction` entrypoint wired to the real Typer app
  - one-shot operator commands spanning ingestion, features, training, evaluation, backtesting, collection, scanning, and report review
  - repo-local operational settings for thresholds, artifact defaults, report selection, paths, and terminal/file alert channels
affects: [alerts-and-operational-hardening, docs, quality-gates]
tech-stack:
  added: []
  patterns: [project-owned CLI orchestration helpers, repo-local one-shot operator defaults]
key-files:
  created: [src/tennisprediction/operations.py]
  modified: [pyproject.toml, src/tennisprediction/config.py, src/tennisprediction/cli.py, tests/unit/test_cli_smoke.py, tests/unit/test_cli_commands.py]
key-decisions:
  - "Point the packaged console script at the Typer app object so `tennisprediction --help` executes the real command tree."
  - "Keep CLI handlers thin and delegate through `tennisprediction.operations` so later logging, docs, and report work share one operator seam."
  - "Implement `run-backtest` as a synthetic even-money proxy over replayed predictions and preserve provenance guardrails until historical Kalshi backtest inputs exist."
patterns-established:
  - "CLI commands should echo artifact/report paths after delegating into project-owned helper functions."
  - "One-shot operational defaults belong in `Settings`, with repo-local path guards and terminal/file-only alert channel validation."
requirements-completed: [OPS-02, OPS-04]
duration: 30 min
completed: 2026-06-25
---

# Phase 07 Plan 03: CLI And Operational Settings Summary

**Packaged Typer entrypoint with one-shot ATP-to-Kalshi operator commands, repo-local operational defaults, and a shared orchestration seam in `operations.py`**

## Performance

- **Duration:** 30 min
- **Started:** 2026-06-25T02:26:00Z
- **Completed:** 2026-06-25T02:56:04Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Fixed the packaged `tennisprediction` entrypoint so help and command dispatch run through the real Typer app.
- Added one-shot CLI commands for ingestion, feature building, training, artifact evaluation, proxy backtesting, Kalshi snapshot collection, live EV scanning, and monitoring report review.
- Extended repo-local settings with alert-channel, threshold, artifact, and report defaults while preserving repository-bound path validation and the Phase 07 no-watch/no-daemon scope.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write failing packaged-entrypoint and command-dispatch tests** - `1ec2bc0` (`test`)
2. **Task 2: Fix the packaged entrypoint and add one-shot orchestration helpers plus operational settings** - `d7122cc` (`feat`)

**Plan metadata:** pending at summary creation time

## Files Created/Modified

- `pyproject.toml` - Repointed the packaged script target to the Typer app object.
- `src/tennisprediction/config.py` - Added repo-local operational defaults for alert channels, feature/model/calibration selection, monitoring run ids, and threshold knobs.
- `src/tennisprediction/cli.py` - Expanded the command tree and routed handlers through `tennisprediction.operations`.
- `src/tennisprediction/operations.py` - Added one-shot orchestration helpers for ingestion, features, training, evaluation, proxy backtesting, snapshot collection, live scan, and monitoring report review.
- `tests/unit/test_cli_smoke.py` - Locked the packaged entrypoint and operational-settings contract in smoke coverage.
- `tests/unit/test_cli_commands.py` - Added command-tree, dispatch-seam, and one-shot-scope regression coverage.

## Decisions Made

- Used `tennisprediction.cli:app` for the console-script target because the Typer app object is the real entrypoint, while the callback-only function was not sufficient for packaged command execution.
- Centralized stage composition in `tennisprediction.operations` instead of embedding pipeline logic inside CLI handlers so future alerting/logging/docs changes can reuse one operator path.
- Kept `run-backtest` read-only and one-shot by using replayed model predictions with synthetic even-money market inputs, which keeps provenance explicit and avoids implying validated historical Kalshi profitability where no such time series has been built yet.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected the unknown-option assertion for current Typer output handling**
- **Found during:** Task 2 (Fix the packaged entrypoint and add one-shot orchestration helpers plus operational settings)
- **Issue:** The `--watch` rejection test asserted against `result.stdout`, but the current Typer/Click stack surfaces the unknown-option message through `result.output`.
- **Fix:** Updated the assertion to check `result.output` so the test verifies the one-shot rejection contract instead of a stream implementation detail.
- **Files modified:** `tests/unit/test_cli_commands.py`
- **Verification:** `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_cli_smoke.py tests/unit/test_cli_commands.py -x`
- **Committed in:** `d7122cc`

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** The deviation tightened the CLI contract without widening scope. No functional scope creep.

## Issues Encountered

- The local `gsd-tools` executable was not on `PATH`; phase state updates were completed through the checked-in Node CLI path instead.
- Sandbox restrictions blocked git index writes and networked `uv` resolution, so staging, commits, and focused verification ran with explicit approval.

## User Setup Required

None - no external service configuration required for this slice.

## Next Phase Readiness

- Phase 07 now has a stable packaged operator path for the remaining logging, docs, and quality-gate plans.
- Later plans can treat `tennisprediction.operations` as the canonical one-shot orchestration seam and build operator-facing docs/reports around the shipped command names and settings contract.

## Self-Check: PASSED

- Confirmed `.planning/phases/07-alerts-and-operational-hardening/07-03-SUMMARY.md` exists.
- Confirmed task commits `1ec2bc0` and `d7122cc` exist in git history.

---
*Phase: 07-alerts-and-operational-hardening*
*Completed: 2026-06-25*
