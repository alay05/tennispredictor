---
phase: 07
slug: alerts-and-operational-hardening
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-24
---

# Phase 07 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 9.1.x` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_cli_smoke.py tests/unit/test_live_monitor_reports.py tests/unit/test_live_scan_orchestration.py tests/unit/test_feature_leakage.py tests/unit/test_backtesting_decisions.py tests/unit/test_live_scan_pricing_contract.py -x` |
| **Full suite command** | `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q` |
| **Estimated runtime** | ~30-60 seconds for task-level checks |

---

## Sampling Rate

- After every task commit: run the narrow command for the touched surface from the verification map below.
- After every plan wave: run `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q`, `UV_CACHE_DIR=.uv-cache python3 -m uv run ruff check .`, and `UV_CACHE_DIR=.uv-cache python3 -m uv run mypy src`.
- Before `$gsd-verify-work`: full suite, lint, format, and typing gates must be green, and repo quality artifacts must exist.
- Max feedback latency: 60 seconds for task-level checks

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 07-OPS-01 | 01 | 1 | OPS-01 | T-07-01 / T-07-02 | Opportunity reports preserve one canonical accepted/rejected row contract while rendering richer operator summaries without execution language. | unit | `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_live_monitor_reports.py -x` | ✅ baseline | ⬜ pending |
| 07-OPS-02 | 01 / 03 | 1 / 3 | OPS-02 | T-07-03 | New report and artifact settings remain repo-local, typed, and do not widen Phase 7 into continuous polling infrastructure. | unit | `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_cli_smoke.py -x` | ✅ baseline | ⬜ pending |
| 07-OPS-03 | 02 | 2 | OPS-03 | T-07-04 / T-07-05 | Audit logs carry stable run/command context, avoid secret leakage, and correlate pipeline decisions without free-form-only strings. | unit | `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_operational_logging.py -x` | ❌ Wave 0 | ⬜ pending |
| 07-OPS-04 | 03 | 3 | OPS-04 | T-07-06 | CLI commands work through the packaged entrypoint and cover the one-shot operator workflow end to end. | smoke | `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_cli_commands.py -x` | ❌ Wave 0 | ⬜ pending |
| 07-OPS-05 | 04 | 4 | OPS-05 | T-07-07 | Local and CI quality gates execute tests, lint, formatting, typing, leakage, EV, and scan-orchestration checks from one documented surface. | mixed | `UV_CACHE_DIR=.uv-cache python3 -m uv run ruff check . && UV_CACHE_DIR=.uv-cache python3 -m uv run ruff format --check . && UV_CACHE_DIR=.uv-cache python3 -m uv run mypy src && UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_feature_leakage.py tests/unit/test_backtesting_decisions.py tests/unit/test_live_scan_orchestration.py tests/unit/test_live_scan_pricing_contract.py -x` | ⚠️ partial | ⬜ pending |
| 07-OPS-06 | 04 | 4 | OPS-06 | T-07-08 | Documentation covers setup, commands, outputs, trust limits, and v1 scope boundaries, and matches the shipped CLI/report surfaces. | manual | `Manual review against docs/operations checklist plus CLI smoke` | ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ partial*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_operational_logging.py` — logging context, handler fan-out, and secret-redaction coverage for OPS-03
- [ ] `tests/unit/test_cli_commands.py` — packaged `tennisprediction` entrypoint and expanded command tree coverage for OPS-04
- [ ] `.pre-commit-config.yaml` — local quality gate packaging for OPS-05
- [ ] `.github/workflows/ci.yml` — repo CI packaging for OPS-05
- [ ] Operator runbook / checklist artifact — documentation verification surface for OPS-06

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Operator docs match the final one-shot workflow and trust boundaries | OPS-06 | The acceptance bar depends on clarity and completeness across multiple docs and command outputs. | Verify setup, Kalshi configuration, command flow, report locations, backtest limitations, and read-only v1 scope against the shipped docs and CLI help text. |

---

## Validation Sign-Off

- [x] All requirement surfaces have an automated verify or an explicit Wave 0 dependency
- [x] Sampling continuity: no 3 consecutive implementation slices should proceed without automated verify
- [x] Wave 0 captures the currently missing logging, CLI, CI, and documentation verification artifacts
- [x] No watch-mode flags
- [x] Feedback latency < 60s for task-level checks
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
