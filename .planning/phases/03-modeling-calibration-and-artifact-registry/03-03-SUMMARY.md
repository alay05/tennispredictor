---
phase: 03-modeling-calibration-and-artifact-registry
plan: 03
subsystem: modeling
tags: [xgboost, calibration, metrics, probability-quality, pytest, mypy, ruff]
requires:
  - phase: 03-01
    provides: Frozen modeling rows and immutable chronological split manifests
  - phase: 03-02
    provides: Baseline trainers and raw-fit result contracts over the frozen feature surface
provides:
  - Manifest-driven XGBoost candidate training with train-window-only early stopping metadata
  - Validation-only calibrated prediction rows for logistic regression, random forest, and XGBoost
  - Shared probability metrics with explicit 10-bin calibration outputs, calibration-curve points, and ECE
affects: [phase-03-artifact-registry, phase-04-backtesting, phase-06-live-predictions]
tech-stack:
  added: []
  patterns:
    [
      train-tail early stopping inside the frozen train membership only,
      validation-only calibration over frozen estimators,
      model-agnostic probability metrics from one shared calibrated output contract,
    ]
key-files:
  created:
    - src/tennisprediction/modeling/xgboost_model.py
    - src/tennisprediction/modeling/calibration.py
    - src/tennisprediction/modeling/metrics.py
    - tests/unit/test_modeling_xgboost.py
    - tests/unit/test_modeling_calibration.py
    - tests/unit/test_modeling_metrics.py
  modified:
    - src/tennisprediction/modeling/schemas.py
key-decisions:
  - "The XGBoost candidate reserves only the trailing 15% of frozen train memberships for fit-time early stopping and records fit/eval membership hashes in fit metadata."
  - "Calibrated prediction rows preserve row-level downstream context including match identity, surface, tournament level, rank inputs, target, raw probability, calibrated probability, and favored-side probability."
  - "The shared probability metrics surface owns explicit 10 uniform calibration bins, a named calibration-curve artifact, and ECE so later plans do not reconstruct metric semantics ad hoc."
patterns-established:
  - "All three model families now flow through RawModelFitResult -> CalibratedModelResult -> ProbabilityMetrics without re-deriving split memberships or feature columns."
  - "Validation-only calibration is enforced against frozen estimators rather than refitting raw models on the external validation or test windows."
requirements-completed: [MOD-04, MOD-05, MOD-06]
duration: 9min
completed: 2026-06-19
---

# Phase 03 Plan 03 Summary

**XGBoost candidate training, validation-only calibrated prediction rows, and a shared probability-quality metrics surface for all Phase 03 model families**

## Performance

- **Duration:** 9 min
- **Started:** 2026-06-19T14:02:09Z
- **Completed:** 2026-06-19T14:11:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added RED coverage for the XGBoost candidate, validation-only calibration, and shared probability metrics.
- Implemented a manifest-driven XGBoost candidate trainer that keeps early stopping inside the train window and emits downstream-ready raw probabilities plus best-iteration metadata.
- Implemented calibrated prediction rows and shared probability metrics so logistic regression, random forest, and XGBoost now expose one consistent probability-quality surface.

## Task Commits

Each task was committed atomically:

1. **Task 1: Write the failing tests for the XGBoost candidate, disjoint calibration, and probability metrics** - `3d26edc` (`test`)
2. **Task 2: Implement the calibrated XGBoost candidate and shared probability metrics** - `90eb2bd` (`feat`)

**Plan metadata:** pending docs close-out commit

## Files Created/Modified

- `src/tennisprediction/modeling/schemas.py` - adds XGBoost config, calibrated prediction/result contracts, and probability metric payloads
- `src/tennisprediction/modeling/xgboost_model.py` - trains the XGBoost candidate on frozen memberships with train-tail early stopping
- `src/tennisprediction/modeling/calibration.py` - calibrates frozen raw estimators on validation rows only and emits typed calibrated prediction rows
- `src/tennisprediction/modeling/metrics.py` - computes scalar probability metrics, explicit 10-bin calibration outputs, calibration-curve points, and ECE
- `tests/unit/test_modeling_xgboost.py` - proves train-window-only early stopping behavior and fit metadata
- `tests/unit/test_modeling_calibration.py` - proves validation-only calibration behavior and downstream row metadata
- `tests/unit/test_modeling_metrics.py` - proves the shared metrics surface for logistic regression, random forest, and XGBoost

## Decisions Made

- Kept XGBoost on the same frozen feature contract and preprocessing surface as the baselines so later artifact and replay logic do not branch by model family.
- Stored fit/eval membership hashes and row counts in XGBoost fit metadata so later artifact persistence can prove the early-stopping window stayed inside training.
- Let `evaluate_probability_predictions()` remain model-agnostic by deriving model identity from the calibrated probability output contract rather than adding model-specific parameters to the function signature.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Replaced the direct `CalibratedClassifierCV` path with a project-owned validation-only calibrator over frozen estimator scores**
- **Found during:** Task 2 (Implement the calibrated XGBoost candidate and shared probability metrics)
- **Issue:** On the installed sklearn 1.9 runtime, the straightforward `CalibratedClassifierCV(FrozenEstimator(...))` path still routed the tiny three-row validation fixture through cross-validation behavior that violated the plan’s disjoint validation-only calibration goal and failed the test suite.
- **Fix:** Implemented `ValidationOnlyCalibrator` using `FrozenEstimator` plus sklearn’s sigmoid/isotonic calibration primitives so calibration fits exactly once on validation scores and only predicts on validation/test windows.
- **Files modified:** `src/tennisprediction/modeling/calibration.py`, `tests/unit/test_modeling_calibration.py`
- **Verification:** `python3 -m uv run pytest -q tests/unit/test_modeling_xgboost.py tests/unit/test_modeling_calibration.py tests/unit/test_modeling_metrics.py -x`, `python3 -m uv run pytest -q tests/unit/test_modeling_baselines.py tests/unit/test_modeling_xgboost.py tests/unit/test_modeling_calibration.py tests/unit/test_modeling_metrics.py -x`, `python3 -m uv run ruff check src/tennisprediction/modeling tests/unit/test_modeling_xgboost.py tests/unit/test_modeling_calibration.py tests/unit/test_modeling_metrics.py`, `python3 -m uv run mypy src/tennisprediction/modeling`
- **Committed in:** `90eb2bd`

---

**Total deviations:** 1 auto-fixed (1 blocking issue)
**Impact on plan:** The deviation preserved the required validation-only calibration boundary and kept the probability-quality slice within scope. No architecture outside the modeling/calibration seam changed.

## Issues Encountered

- The installed sklearn runtime’s direct `CalibratedClassifierCV` path was incompatible with the tiny frozen validation fixture for this plan, so the calibration layer had to own the validation-only fit explicitly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03-04 can persist raw estimator artifacts, calibrator metadata, calibrated prediction rows, and probability metrics without inventing new row or metric contracts.
- Phase 04 backtesting can consume one consistent calibrated probability surface across logistic regression, random forest, and XGBoost.

## Self-Check: PASSED

- Verified `.planning/phases/03-modeling-calibration-and-artifact-registry/03-03-SUMMARY.md` exists on disk.
- Verified task commits `3d26edc` and `90eb2bd` exist in git history.
- Re-ran plan verification: RED gate failed before implementation, focused modeling pytest suites passed after implementation, `ruff check` passed, and `mypy` passed for `src/tennisprediction/modeling`.

---
*Phase: 03-modeling-calibration-and-artifact-registry*
*Completed: 2026-06-19*
