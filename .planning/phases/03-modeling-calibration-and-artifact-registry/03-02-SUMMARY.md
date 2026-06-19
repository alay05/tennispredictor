---
phase: 03-modeling-calibration-and-artifact-registry
plan: 02
subsystem: modeling
tags: [pandas, scikit-learn, xgboost, joblib, baselines, calibration]
requires:
  - phase: 03-01
    provides: Frozen modeling rows and immutable chronological split manifests
provides:
  - Approved `ml` dependency group limited to `pandas`, `scikit-learn`, `xgboost`, and `joblib`
  - `RawModelFitResult` contract carrying split provenance, parameters, raw probabilities, and the trained estimator handle
  - Manifest-driven logistic regression and random forest baseline trainers over the frozen Phase 03 dataset contract
affects: [phase-03-calibration, phase-03-artifact-registry, phase-04-backtesting]
tech-stack:
  added: [pandas, scikit-learn, xgboost, joblib]
  patterns:
    [
      manifest-driven baseline row selection,
      raw-fit result contracts for downstream calibration and registry work,
      categorical preprocessing over persisted differential-row feature contracts,
    ]
key-files:
  created:
    - src/tennisprediction/modeling/baselines.py
    - tests/unit/test_modeling_baselines.py
  modified:
    - pyproject.toml
    - uv.lock
    - src/tennisprediction/modeling/schemas.py
key-decisions:
  - "Keep `RawModelFitResult.trained_estimator` as the canonical cross-plan handoff in this slice, and leave `raw_model_artifact_path` null until the artifact-registry plan persists it."
  - "Select train, validation, and test rows strictly from `FrozenSplitManifest` memberships instead of re-deriving windows from dates during trainer execution."
  - "Treat persisted string and boolean feature columns as categorical preprocessing inputs so the baseline trainers can consume the full frozen feature contract without rewriting Phase 02 outputs."
patterns-established:
  - "Baseline trainers accept either a manifest object or a manifest path, but always emit the exact split provenance path/id alongside raw validation and test probabilities."
  - "Modeling tests prove manifest-driven membership selection by using custom train subsets rather than trusting split boundary dates alone."
requirements-completed: [MOD-02, MOD-03]
duration: 5min
completed: 2026-06-18
---

# Phase 03 Plan 02 Summary

**Manifest-driven logistic regression and random forest baselines with raw probability outputs and downstream-ready fit provenance**

## Performance

- **Duration:** 5 min
- **Started:** 2026-06-19T02:48:07Z
- **Completed:** 2026-06-19T02:53:00Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Added the approved Phase 03 `ml` dependency group and refreshed `uv.lock` without pulling in `mlflow` or `matplotlib`.
- Added RED coverage that proves the baseline trainers must obey frozen manifest memberships, preserve feature-column order, and return raw validation/test probabilities with explicit metadata.
- Implemented `RawModelFitResult` plus logistic regression and random forest baseline trainers that fit only on train rows and emit downstream-ready raw outputs.

## Task Commits

1. **Task 1: Approve the Phase 03 ML dependency list before any install or lockfile update** - checkpoint satisfied by user approval; no code commit
2. **Task 2: Add the approved ML dependency group and write the failing baseline trainer tests** - `8a1db18` (`test`)
3. **Task 3: Implement the logistic regression and random forest baseline trainers** - `0d5e356` (`feat`)

**Plan metadata:** pending docs close-out commit

## Files Created/Modified

- `pyproject.toml` - adds the approved `ml` dependency group and targeted mypy overrides for pandas/sklearn imports
- `uv.lock` - records the synced Phase 03 baseline-training dependency set
- `src/tennisprediction/modeling/schemas.py` - adds `RawModelFitResult` for raw estimator provenance and probability outputs
- `src/tennisprediction/modeling/baselines.py` - fits manifest-driven logistic regression and random forest baselines with categorical preprocessing
- `tests/unit/test_modeling_baselines.py` - covers dependency presence, train-only membership selection, manifest-ordered probabilities, and fit metadata
- `.planning/phases/03-modeling-calibration-and-artifact-registry/deferred-items.md` - records the host `libomp` follow-up needed before the XGBoost training slice

## Decisions Made

- Kept the raw estimator in memory inside `RawModelFitResult` for the calibration and artifact-registry plans, instead of guessing or reconstructing a model later from detached metadata.
- Treated categorical feature columns as part of the stable frozen modeling contract, so Phase 03 trainers encode them rather than forcing a Phase 02 schema rewrite.
- Let the RED dependency test verify installed `xgboost` distribution metadata instead of eagerly importing the native library, because this plan only needed package approval and baseline training, not XGBoost execution yet.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Adjusted the RED dependency proof to avoid an unrelated XGBoost native-runtime failure**
- **Found during:** Task 2 (Add the approved ML dependency group and write the failing baseline trainer tests)
- **Issue:** Eagerly importing `xgboost` in the dependency-proof test failed on this macOS host because `libxgboost.dylib` could not load `libomp.dylib`, which would have obscured the intended missing-baselines RED failure.
- **Fix:** Changed the dependency-proof test to verify the installed `xgboost` distribution version via package metadata instead of importing the native library during the baseline slice.
- **Files modified:** `tests/unit/test_modeling_baselines.py`
- **Verification:** `python3 -m uv run pytest -q tests/unit/test_modeling_baselines.py -x` then failed on the expected missing `tennisprediction.modeling.baselines` module.
- **Committed in:** `8a1db18`

**2. [Rule 2 - Missing Critical] Added categorical preprocessing to the baseline trainers**
- **Found during:** Task 3 (Implement the logistic regression and random forest baseline trainers)
- **Issue:** The frozen modeling dataset already contains string and boolean feature columns such as surface, tournament level, round, and missingness flags; a numeric-only pipeline would not fit the approved baselines correctly.
- **Fix:** Added shared preprocessing that median-imputes numeric columns, one-hot encodes categorical columns, and applies standard scaling only to the logistic-regression numeric path.
- **Files modified:** `src/tennisprediction/modeling/baselines.py`
- **Verification:** `python3 -m uv run pytest -q tests/unit/test_modeling_datasets.py tests/unit/test_modeling_splits.py tests/unit/test_modeling_baselines.py -x`
- **Committed in:** `0d5e356`

**3. [Rule 1 - Bug] Fixed the synthetic random-forest train subset used by the manifest-membership test**
- **Found during:** Task 3 (Implement the logistic regression and random forest baseline trainers)
- **Issue:** The first GREEN run used a custom random-forest train subset that accidentally selected only one target class, causing `predict_proba(... )[:, 1]` to fail.
- **Fix:** Changed the synthetic train subset to preserve both classes while still proving the trainer obeys manifest membership instead of date re-derivation.
- **Files modified:** `tests/unit/test_modeling_baselines.py`
- **Verification:** `python3 -m uv run pytest -q tests/unit/test_modeling_datasets.py tests/unit/test_modeling_splits.py tests/unit/test_modeling_baselines.py -x`
- **Committed in:** `0d5e356`

**4. [Rule 3 - Blocking] Added targeted mypy overrides for pandas and sklearn imports**
- **Found during:** Task 3 (Implement the logistic regression and random forest baseline trainers)
- **Issue:** Strict project mypy failed because the installed pandas and sklearn packages do not ship complete type information for this environment.
- **Fix:** Added a narrow `tool.mypy.overrides` block for `pandas` and `sklearn` imports so modeling code remains strict without blocking on third-party stub coverage.
- **Files modified:** `pyproject.toml`
- **Verification:** `python3 -m uv run mypy src/tennisprediction/modeling`
- **Committed in:** `0d5e356`

---

**Total deviations:** 4 auto-fixed (2 blocking issues, 1 missing critical functionality, 1 bug)
**Impact on plan:** All fixes were necessary to keep the RED/GREEN flow meaningful and to make the baseline trainers fit the actual frozen Phase 03 feature contract. No scope creep beyond the required baseline slice.

## Issues Encountered

- `xgboost` installs into the environment but its native library still requires `libomp.dylib` on this host; the follow-up was recorded in `.planning/phases/03-modeling-calibration-and-artifact-registry/deferred-items.md` for the XGBoost candidate plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 03-03 can reuse `RawModelFitResult` and the manifest-driven preprocessing/selection pattern for calibrated candidate training.
- Plan 03-04 can persist raw estimator artifacts without inferring feature order, split provenance, or model parameters from scratch.
- Before executing the XGBoost candidate slice, resolve the deferred host `libomp` runtime dependency so `xgboost` can be imported and trained on this machine.

## Self-Check: PASSED

- Verified `.planning/phases/03-modeling-calibration-and-artifact-registry/03-02-SUMMARY.md` exists on disk.
- Verified `src/tennisprediction/modeling/baselines.py` and `tests/unit/test_modeling_baselines.py` exist on disk.
- Verified task commits `8a1db18` and `0d5e356` exist in git history.
- Re-ran the GREEN verification gates: targeted modeling pytest suite passed, `ruff check` passed, and `mypy` passed for `src/tennisprediction/modeling`.
- Confirmed the Task 1 package-gate prerequisite check still passes and the RED gate was satisfied earlier by the expected missing-implementation failure before the GREEN commit.
