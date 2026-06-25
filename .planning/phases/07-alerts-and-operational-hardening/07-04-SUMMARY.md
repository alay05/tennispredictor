---
phase: 07-alerts-and-operational-hardening
plan: 04
subsystem: infra
tags: [pre-commit, github-actions, documentation, operations]
requires:
  - phase: 07-01
    provides: one-shot CLI orchestration and monitoring report seams
  - phase: 07-02
    provides: correlated audit logging and redaction
  - phase: 07-03
    provides: packaged CLI command tree and repo-local settings
provides:
  - repo-local pre-commit gates for lint, formatting, typing, and critical tests
  - GitHub Actions quality gates aligned with the local checks
  - an operator runbook for the one-shot ATP-to-Kalshi workflow and trust limits
affects: [alerts-and-operational-hardening, docs, quality-gates]
tech-stack:
  added: []
  patterns: [repo-local quality gates, venv-backed hook entrypoints, operator runbook checklist]
key-files:
  created: [docs/operations.md]
  modified:
    [
      .pre-commit-config.yaml,
      .github/workflows/ci.yml,
      .planning/STATE.md,
    ]
key-decisions:
  - "Use repo-venv binaries for pre-commit and CI execution so the quality gates remain runnable even when a standalone `uv` binary is not on PATH in this workspace."
  - "Document only the shipped one-shot commands, outputs, and trust boundaries; do not advertise polling, daemon, or trade-execution controls that the repo does not ship."
  - "Keep the monitoring/reporting path advisory-only and clarify that backtesting is a synthetic even-money proxy, not a historical Kalshi replay."
patterns-established:
  - "Local hooks and CI should run the same lint, format, typing, and critical test commands."
  - "The operator runbook should read like a checklist: setup, command flow, outputs, audit trail, then trust limits."
requirements-completed: [OPS-05, OPS-06]
duration: 15min
completed: 2026-06-25
---

# Phase 07 Plan 04: Quality Gates And Operations Runbook Summary

**Repo-local pre-commit and CI gates now match the shipped one-shot workflow, and the new operator runbook documents how to run and distrust the ATP-to-Kalshi surfaces.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-06-25T15:52:00Z
- **Completed:** 2026-06-25T16:15:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Added repo-local pre-commit hooks for Ruff, formatting, mypy, and the critical CLI/report/logging/scan/leakage/EV test surface.
- Added a matching GitHub Actions workflow that installs the locked environment and runs the same checks.
- Wrote `docs/operations.md` as the operator runbook for setup, commands, output locations, alert-channel defaults, and v1 trust boundaries.

## Task Commits

Each task was committed atomically:

1. **Task 1: Package the local and CI quality gates around the Phase 07 validation contract** - pending
2. **Task 2: Write the operator runbook and trust-boundary checklist for the final one-shot workflow** - pending

## Files Created/Modified

- `.pre-commit-config.yaml` - Repo-local hook config for lint, format, typing, and critical tests.
- `.github/workflows/ci.yml` - GitHub Actions workflow running the same quality-gate commands.
- `docs/operations.md` - Operator runbook for setup, commands, outputs, and trust boundaries.
- `.planning/STATE.md` - Execution-state refresh for the final Phase 07 closeout.

## Decisions Made

- Switched the hook/workflow launchers to the repo venv binaries so the gates stay executable in this workspace without depending on a standalone `uv` binary on PATH.
- Kept the documentation focused on the shipped one-shot surfaces and explicitly excluded polling or daemon controls from the v1 operational story.

## Deviations from Plan

### Validation Finding

**1. Repo-wide format and typing debt exists outside the wave-4 files**
- **Found during:** `pre-commit run --all-files`
- **Issue:** Ruff and mypy surfaced existing repository-wide drift in unrelated source files, so the new phase-07 gates are wired correctly but the full repo gate is not green yet.
- **Impact:** The new local and CI entrypoints are valid; the remaining work is broader cleanup, not a phase-07 artifact gap.

## Issues Encountered

- `uv` was not available as a standalone binary in this workspace, so the gate launchers were adjusted to use the repo venv binaries directly.
- `pre-commit` initially tried to use a host cache path outside the sandbox; setting `PRE_COMMIT_HOME` into the repo resolved that during verification.

## User Setup Required

None - no new external services or secrets are required for the new docs or quality gates.

## Next Phase Readiness

- Phase 07 now has the final documentation and local/CI gate surfaces requested by OPS-05 and OPS-06.
- The remaining repo-wide Ruff/mypy debt can be addressed separately from the phase artifact set.

## Self-Check: PARTIAL

- Confirmed `.pre-commit-config.yaml` exists and runs against the critical surface.
- Confirmed `.github/workflows/ci.yml` exists and mirrors the local gate commands.
- Confirmed `docs/operations.md` exists and documents the one-shot operator workflow.
