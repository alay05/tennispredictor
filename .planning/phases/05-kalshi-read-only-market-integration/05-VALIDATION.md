---
phase: 05
slug: kalshi-read-only-market-integration
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-20
---

# Phase 05 - Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 9.1.x` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python3 -m uv run pytest -q tests/unit/test_kalshi_*.py` |
| **Full suite command** | `python3 -m uv run pytest -q` |
| **Estimated runtime** | ~20-30 seconds for task-level checks |

---

## Sampling Rate

- After every task commit: run the task-specific command from the verification map below.
- After every plan wave: run `python3 -m uv run pytest -q tests/unit/test_kalshi_*.py`
- Before `$gsd-verify-work`: full suite must be green.
- Max feedback latency: 30 seconds for task-level checks

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | KAL-01 / KAL-04 | T-05-01-01 / T-05-01-02 / T-05-01-03 | Red tests prove authenticated read access and DTO normalization are still missing before implementation begins. | unit-red | `! python3 -m uv run pytest -q tests/unit/test_kalshi_client.py -x` | ❌ planned | ⬜ pending |
| 05-01-02 | 01 | 1 | KAL-01 / KAL-04 | T-05-01-01 / T-05-01-02 / T-05-01-03 | Read client signs requests, exposes only read endpoints, and returns normalized DTOs. | unit | `python3 -m uv run pytest -q tests/unit/test_kalshi_client.py -x` | ✅ after 05-01-01 | ⬜ pending |
| 05-02-01 | 02 | 2 | KAL-02 | T-05-02-01 / T-05-02-02 / T-05-02-03 | Red tests prove raw snapshot persistence is still missing before implementation begins. | unit-red | `! python3 -m uv run pytest -q tests/unit/test_kalshi_storage.py -x` | ❌ planned | ⬜ pending |
| 05-02-02 | 02 | 2 | KAL-02 | T-05-02-01 / T-05-02-02 / T-05-02-03 | Snapshot rows persist request metadata, timestamps, payload lineage, and reload cleanly from repo-local DuckDB. | unit | `python3 -m uv run pytest -q tests/unit/test_kalshi_storage.py -x` | ✅ after 05-02-01 | ⬜ pending |
| 05-03-01 | 03 | 3 | KAL-03 / KAL-05 | T-05-03-01 / T-05-03-02 / T-05-03-03 | Red tests prove pagination, retry, and read-only job guardrails are still missing before implementation begins. | unit-red | `! python3 -m uv run pytest -q tests/unit/test_kalshi_jobs.py -x` | ❌ planned | ⬜ pending |
| 05-03-02 | 03 | 3 | KAL-03 / KAL-05 | T-05-03-01 / T-05-03-02 / T-05-03-03 | Collector handles cursors, 429 backoff, market states, and read-only CLI/job execution. | unit | `python3 -m uv run pytest -q tests/unit/test_kalshi_client.py tests/unit/test_kalshi_storage.py tests/unit/test_kalshi_jobs.py -x` | ✅ after 05-03-01 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None. The Phase 05 plan uses only the installed project stack and does not require external provisioning beyond Kalshi credentials when execution begins.

---

## Manual-Only Verifications

- None. Phase 05 planning has no manual approval gates.

---

## Validation Sign-Off

- [x] All tasks have an automated verify or an automated preflight paired with a blocking human-gate checkpoint
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references because no MISSING references remain
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

