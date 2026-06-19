---
phase: 03
slug: modeling-calibration-and-artifact-registry
status: ready
nyquist_compliant: true
wave_0_complete: true
created: 2026-06-18
---

# Phase 03 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 9.1.x` |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `python3 -m uv run pytest -q tests/unit/test_modeling_*.py` |
| **Full suite command** | `python3 -m uv run pytest -q` |
| **Estimated runtime** | ~25-30 seconds for task-level checks |

---

## Sampling Rate

- **After every task commit:** Run the task-specific command from the verification map below.
- **After every plan wave:** Run `python3 -m uv run pytest -q tests/unit/test_modeling_*.py`
- **Before `$gsd-verify-work`:** Full suite must be green.
- **Max feedback latency:** 30 seconds for task-level checks

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | MOD-01 | T-03-01-01 / T-03-01-03 | Red tests prove the dataset loader still must join canonical winners without recomputing tennis features and the split freezer still must reject overlap or empty windows. | unit-red | `! python3 -m uv run pytest -q tests/unit/test_modeling_datasets.py tests/unit/test_modeling_splits.py -x` | ❌ planned | ⬜ pending |
| 03-01-02 | 01 | 1 | MOD-01 | T-03-01-01 / T-03-01-02 / T-03-01-03 | Dataset materialization stays deterministic and split manifests persist exact memberships, row counts, and hashes for later replay. | unit | `python3 -m uv run pytest -q tests/unit/test_modeling_datasets.py tests/unit/test_modeling_splits.py -x` | ✅ after 03-01-01 | ⬜ pending |
| 03-02-01 | 02 | 2 | MOD-02 / MOD-03 | T-03-02-SC | Human legitimacy review explicitly approves `pandas`, `scikit-learn`, `xgboost`, and `joblib`, and explicitly keeps `mlflow` and `matplotlib` out of the mandatory install set before any environment mutation. | human-gate + automated-preflight | `python3 - <<'PY'` preflight validates that `03-RESEARCH.md` still contains the required package-legitimacy audit entries before the human checkpoint runs. | n/a | ⬜ pending |
| 03-02-02 | 02 | 2 | MOD-02 / MOD-03 | T-03-02-SC | Red tests prove the `ml` dependency group and baseline trainer expectations are still missing before baseline implementation begins. | unit-red | `! python3 -m uv run pytest -q tests/unit/test_modeling_baselines.py -x` | ❌ planned | ⬜ pending |
| 03-02-03 | 02 | 2 | MOD-02 / MOD-03 | T-03-02-01 / T-03-02-02 | Logistic regression and random forest fit only on train memberships from the frozen split manifest and emit raw validation/test probabilities with ordered feature metadata. | unit | `python3 -m uv run pytest -q tests/unit/test_modeling_datasets.py tests/unit/test_modeling_splits.py tests/unit/test_modeling_baselines.py -x` | ✅ after 03-02-02 | ⬜ pending |
| 03-03-01 | 03 | 3 | MOD-04 / MOD-05 / MOD-06 | T-03-03-01 / T-03-03-02 / T-03-03-03 | Red tests prove XGBoost early stopping, shared calibration, and probability metrics are still missing before the candidate and shared calibration/evaluation path are implemented. | unit-red | `! python3 -m uv run pytest -q tests/unit/test_modeling_xgboost.py tests/unit/test_modeling_calibration.py tests/unit/test_modeling_metrics.py -x` | ❌ planned | ⬜ pending |
| 03-03-02 | 03 | 3 | MOD-04 / MOD-05 / MOD-06 | T-03-03-01 / T-03-03-02 / T-03-03-03 | Logistic regression, random forest, and XGBoost all calibrate on the disjoint validation window and produce shared probability metrics from calibrated test outputs. | unit | `python3 -m uv run pytest -q tests/unit/test_modeling_baselines.py tests/unit/test_modeling_xgboost.py tests/unit/test_modeling_calibration.py tests/unit/test_modeling_metrics.py -x` | ✅ after 03-03-01 | ⬜ pending |
| 03-04-01 | 04 | 4 | MOD-07 / MOD-08 | T-03-04-02 / T-03-04-03 | Red tests prove the immutable artifact-bundle and segment-diagnostic surface for logistic regression, random forest, and XGBoost is still missing before persistence code is added. | unit-red | `! python3 -m uv run pytest -q tests/unit/test_modeling_metrics.py tests/unit/test_modeling_registry.py -x` | ❌ planned | ⬜ pending |
| 03-04-02 | 04 | 4 | MOD-06 / MOD-07 / MOD-08 | T-03-04-01 / T-03-04-02 / T-03-04-03 | Artifact bundles, reports, and trusted loads persist calibrated outputs for logistic regression, random forest, and XGBoost under one immutable manifest schema. | unit | `python3 -m uv run pytest -q tests/unit/test_modeling_datasets.py tests/unit/test_modeling_baselines.py tests/unit/test_modeling_xgboost.py tests/unit/test_modeling_calibration.py tests/unit/test_modeling_metrics.py tests/unit/test_modeling_registry.py -x` | ✅ after 03-04-01 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

None. `python3 -m uv` is already available in the current environment, so the Wave 1 verification commands are executable before Plan `03-02` adds the Phase 03 `ml` dependency group; the only manual step is the blocking package-legitimacy checkpoint in `03-02-01`. The Phase 03 plans no longer contain any `<automated>MISSING</automated>` verification entries.

---

## Manual-Only Verifications

- `03-02-01` — human legitimacy approval for `pandas`, `scikit-learn`, `xgboost`, and `joblib` before `python3 -m uv sync --group dev --group ml`

---

## Validation Sign-Off

- [x] All tasks have an automated verify or an automated preflight paired with a blocking human-gate checkpoint
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references because no MISSING references remain
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
