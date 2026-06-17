---
phase: 02
slug: leakage-safe-feature-engine
status: ready
nyquist_compliant: true
wave_0_complete: false
created: 2026-06-17
---

# Phase 02 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 9.1.0` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `./.venv/bin/python -m pytest -q tests/unit/test_feature_*.py` |
| **Full suite command** | `./.venv/bin/python -m pytest -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `./.venv/bin/python -m pytest -q tests/unit/test_feature_*.py`
- **After every plan wave:** Run `./.venv/bin/python -m pytest -q`
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | FEAT-03 | T-02-01-01 / T-02-01-02 | Ranking cutoff stays backward-only, `ranking_change` uses the immediately previous ranking row, and unknown round tokens fail loudly. | unit-red | `! ./.venv/bin/python -m pytest -q tests/unit/test_feature_runner.py tests/unit/test_feature_rankings.py tests/unit/test_feature_ordering.py` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | FEAT-01 | T-02-01-01 / T-02-01-03 | Runner emits pre-match snapshots before updates and derives minimal ranking differentials from snapshot contracts only. | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_runner.py tests/unit/test_feature_rankings.py tests/unit/test_feature_ordering.py` | ✅ after 02-01-01 | ⬜ pending |
| 02-02-01 | 02 | 2 | FEAT-04 | T-02-02-01 | Red tests prove Elo/surface Elo, recent-form, rest, and recent-form differential rows are still missing before implementation. | unit-red | `! ./.venv/bin/python -m pytest -q tests/unit/test_feature_state.py tests/unit/test_feature_runner.py` | ❌ W0 | ⬜ pending |
| 02-02-02 | 02 | 2 | FEAT-08 | T-02-02-01 / T-02-02-02 | Snapshot contract exposes Elo, surface Elo, rest, and recent-form 5/10/20 deltas from player-side snapshots, not from recomputed raw history. | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_state.py tests/unit/test_feature_runner.py` | ✅ after 02-02-01 | ⬜ pending |
| 02-03-01 | 03 | 3 | FEAT-05 | T-02-03-01 | Red tests prove prior-only stat aggregates are limited to totals-backed MVP rates and preserve missingness. | unit-red | `! ./.venv/bin/python -m pytest -q tests/unit/test_feature_state.py tests/unit/test_feature_differential.py` | ❌ W0 | ⬜ pending |
| 02-03-02 | 03 | 3 | FEAT-06 | T-02-03-01 / T-02-03-02 / T-02-03-03 | Serve/return and H2H state stay prior-only, sparse-data-aware, and reproducible through differential rows. | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_state.py tests/unit/test_feature_differential.py` | ✅ after 02-03-01 | ⬜ pending |
| 02-04-01 | 04 | 4 | FEAT-09 | T-02-04-01 / T-02-04-03 | Red tests prove persistence and leakage invariants are still missing before implementation. | unit-red | `! ./.venv/bin/python -m pytest -q tests/unit/test_feature_leakage.py tests/unit/test_feature_persistence.py` | ❌ W0 | ⬜ pending |
| 02-04-02 | 04 | 4 | FEAT-08 | T-02-04-01 / T-02-04-02 / T-02-04-03 | Persistence writes the full FEAT-08 differential contract and historical outputs stay invariant under future-row deletion and same-cohort reordering. | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_leakage.py tests/unit/test_feature_persistence.py` | ✅ after 02-04-01 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/unit/test_feature_ordering.py` — round precedence, unknown-round failure, and FEAT-07 context ordering coverage
- [ ] `tests/unit/test_feature_runner.py` — cohort emission, ranking provenance, and recent-form/rest differential coverage
- [ ] `tests/unit/test_feature_rankings.py` — backward ranking lookup, previous-row provenance, and `ranking_change` cases
- [ ] `tests/unit/test_feature_state.py` — Elo, form, serve/return, H2H, and rest transitions
- [ ] `tests/unit/test_feature_differential.py` — A/B orientation, form/stat/H2H differentials, and missingness preservation
- [ ] `tests/unit/test_feature_leakage.py` — future-row deletion and same-cohort reorder invariants
- [ ] `tests/unit/test_feature_persistence.py` — DuckDB feature snapshot, differential row, and audit-table persistence
- [ ] Shared synthetic fixture builder for canonical match, ranking, and stat histories

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
