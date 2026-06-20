---
phase: 04
slug: backtesting-and-ev-decision-core
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-19
---

# Phase 04 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 9.1.x` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python3 -m uv run pytest -q tests/unit/test_backtesting_*.py` |
| **Full suite command** | `python3 -m uv run pytest -q` |
| **Estimated runtime** | ~20-30 seconds for task-level checks |

---

## Sampling Rate

- After every task commit: run the task-specific command from the verification map below.
- After every plan wave: run `python3 -m uv run pytest -q tests/unit/test_backtesting_*.py`
- Before `$gsd-verify-work`: full suite must be green.
- Max feedback latency: 30 seconds for task-level checks

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | BKT-01 | T-04-01-01 / T-04-01-02 | Red tests prove the trusted replay harness is still missing before implementation begins. | unit-red | `! python3 -m uv run pytest -q tests/unit/test_backtesting_replay.py -x` | ❌ planned | ⬜ pending |
| 04-01-02 | 01 | 1 | BKT-01 | T-04-01-01 / T-04-01-02 | Replay loads a trusted Phase 03 bundle, rematerializes Phase 02 rows, and regenerates deterministic probabilities in manifest order. | unit | `python3 -m uv run pytest -q tests/unit/test_backtesting_replay.py -x` | ✅ after 04-01-01 | ⬜ pending |
| 04-02-01 | 02 | 2 | BKT-02 / BKT-03 | T-04-02-01 / T-04-02-02 / T-04-02-03 | Red tests prove the EV pricing and reason-coded opportunity engine are still missing before implementation begins. | unit-red | `! python3 -m uv run pytest -q tests/unit/test_backtesting_decisions.py -x` | ❌ planned | ⬜ pending |
| 04-02-02 | 02 | 2 | BKT-02 / BKT-03 | T-04-02-01 / T-04-02-02 / T-04-02-03 | Replay rows and normalized market inputs evaluate side-symmetrically, emit accepted/rejected records, and preserve threshold snapshots plus reason codes. | unit | `python3 -m uv run pytest -q tests/unit/test_backtesting_replay.py tests/unit/test_backtesting_decisions.py -x` | ✅ after 04-02-01 | ⬜ pending |
| 04-03-01 | 03 | 3 | BKT-04 / BKT-05 / BKT-06 | T-04-03-01 / T-04-03-02 / T-04-03-03 | Red tests prove chronological backtest metrics and provenance-guarded reporting are still missing before implementation begins. | unit-red | `! python3 -m uv run pytest -q tests/unit/test_backtesting_metrics.py tests/unit/test_backtesting_reports.py -x` | ❌ planned | ⬜ pending |
| 04-03-02 | 03 | 3 | BKT-04 / BKT-05 / BKT-06 | T-04-03-01 / T-04-03-02 / T-04-03-03 | Backtest summaries compute ordered equity curves, ROI, drawdown, uncertainty bands, and provenance-guarded report outputs under repo-local paths. | unit | `python3 -m uv run pytest -q tests/unit/test_backtesting_replay.py tests/unit/test_backtesting_decisions.py tests/unit/test_backtesting_metrics.py tests/unit/test_backtesting_reports.py -x` | ✅ after 04-03-01 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None. The replay, EV, and reporting tests are all executable in the current environment using the installed Phase 03 stack.

---

## Manual-Only Verifications

- None. Phase 04 planning has no manual approval gates.

---

## Validation Sign-Off

- [x] All tasks have an automated verify or an automated preflight paired with a blocking human-gate checkpoint
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references because no MISSING references remain
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
