# Phase 03: Modeling, Calibration, and Artifact Registry - Research

**Researched:** 2026-06-18
**Domain:** Chronological dataset freezing, tabular model training, probability calibration, and local artifact registry design for ATP match-win models [CITED: .planning/ROADMAP.md][CITED: .planning/REQUIREMENTS.md][CITED: .planning/phases/02-leakage-safe-feature-engine/02-VERIFICATION.md]
**Confidence:** MEDIUM

## User Constraints

- No `03-CONTEXT.md` exists for this phase, so there are no phase-specific locked decisions from discuss-phase to copy verbatim. Research scope is constrained by `AGENTS.md`, `ROADMAP.md`, `REQUIREMENTS.md`, and verified Phase 02 outputs instead. [CITED: user request][CITED: AGENTS.md][CITED: .planning/ROADMAP.md][CITED: .planning/REQUIREMENTS.md][CITED: .planning/phases/02-leakage-safe-feature-engine/02-VERIFICATION.md]
- ATP-only scope remains locked; Phase 03 must not expand modeling inputs or diagnostics to WTA, Challenger, ITF, doubles, or other tours. [CITED: AGENTS.md]
- Kalshi-only scope remains locked for downstream consumers, but this phase is offline model work only. Model contracts should still remain tennis-match-probability specific rather than venue-generic. [CITED: AGENTS.md]
- Chronological leakage prevention is a phase gate. Phase 03 must consume persisted Phase 02 outputs and frozen chronological splits only; no random shuffled validation is acceptable. [CITED: AGENTS.md][CITED: .planning/REQUIREMENTS.md]
- Calibrated probabilities are required; Phase 03 cannot stop at uncalibrated classification metrics. [CITED: AGENTS.md][CITED: .planning/REQUIREMENTS.md]
- Profitability claims are out of scope for this phase; Phase 03 should persist enough provenance for Phase 04 backtests to replay exact datasets, model parameters, and calibrated probabilities. [CITED: AGENTS.md][CITED: .planning/ROADMAP.md]
- Engineering quality is non-negotiable: modular, typed, logged, configurable, reproducible code with focused unit tests for critical logic. [CITED: AGENTS.md]

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MOD-01 | System creates frozen chronological train, validation, and test datasets without random shuffling. [CITED: .planning/REQUIREMENTS.md] | Build datasets from persisted `feature_differential_rows` plus `canonical_matches`, then freeze explicit split manifests with boundary metadata, exact row membership hashes, and row counts. [CITED: src/tennisprediction/features/persistence.py][CITED: src/tennisprediction/storage/duckdb.py][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html][ASSUMED] |
| MOD-02 | System trains a logistic regression benchmark model. [CITED: .planning/REQUIREMENTS.md] | Use the shared feature contract with a scikit-learn pipeline: numeric imputation, optional scaling, then `LogisticRegression`. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.impute.SimpleImputer.html][ASSUMED] |
| MOD-03 | System trains a random forest benchmark model. [CITED: .planning/REQUIREMENTS.md] | Use the same ordered feature contract, but a model-specific trainer around `RandomForestClassifier`; current scikit-learn docs note native NaN support. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html] |
| MOD-04 | System trains an XGBoost production-candidate model. [CITED: .planning/REQUIREMENTS.md] | Use `XGBClassifier` via the scikit-learn interface on the same feature contract, with training-window-only early stopping or tuning so the external calibration split stays disjoint. [CITED: https://xgboost.readthedocs.io/en/stable/python/python_intro.html][CITED: https://xgboost.readthedocs.io/en/stable/python/python_api.html] |
| MOD-05 | System calibrates model probabilities using a disjoint chronological validation period. [CITED: .planning/REQUIREMENTS.md] | Fit raw estimators on the training window only, then calibrate with `CalibratedClassifierCV` and `FrozenEstimator` on the validation window so fit and calibration data remain disjoint. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html][CITED: https://scikit-learn.org/stable/modules/calibration.html] |
| MOD-06 | System evaluates models with accuracy, ROC AUC, log loss, Brier score, calibration curve, and expected calibration error. [CITED: .planning/REQUIREMENTS.md] | Report official sklearn metrics plus calibration-bin outputs; keep ECE as a small project metric helper over frozen bins because Phase 03 still needs a project-owned aggregate for it. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_auc_score.html][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.log_loss.html][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.calibration_curve.html][ASSUMED] |
| MOD-07 | System reports segment diagnostics by surface, tournament level, time period, ranking band, and confidence bucket. [CITED: .planning/REQUIREMENTS.md] | Derive segments from persisted differential-row metadata and saved calibrated probabilities; keep segment definitions explicit in the artifact manifest. [CITED: src/tennisprediction/features/persistence.py][ASSUMED] |
| MOD-08 | System persists model artifacts with source version, feature version, split boundaries, model parameters, calibrator, and metrics. [CITED: .planning/REQUIREMENTS.md] | Use an immutable local artifact directory per run, typed manifests, separate model/calibrator files, ordered feature-column lists, environment metadata, and optional MLflow tracking as a secondary ledger. [CITED: AGENTS.md][CITED: https://scikit-learn.org/stable/model_persistence.html][CITED: https://mlflow.org/docs/latest/ml/tracking/][CITED: https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/][CITED: https://xgboost.readthedocs.io/en/stable/python/python_api.html][ASSUMED] |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- The phase must stay ATP-only. Filters, diagnostics, and saved model metadata should not imply multi-tour support. [CITED: AGENTS.md]
- The historical source of truth remains Jeff Sackmann `tennis_atp`; Phase 03 provenance must point back to the Phase 01 source commit and the Phase 02 feature version instead of introducing a new upstream identity layer. [CITED: AGENTS.md][CITED: src/tennisprediction/domain/models.py][CITED: src/tennisprediction/features/schemas.py]
- Chronological feature computation and leakage prevention are locked project decisions. Phase 03 must consume frozen Phase 02 outputs, not recompute Elo, form, H2H, rankings, or stat aggregates in modeling code. [CITED: AGENTS.md][CITED: .planning/phases/02-leakage-safe-feature-engine/02-VERIFICATION.md]
- Calibrated probabilities are required. Planning should treat calibration artifacts and calibration metrics as first-class deliverables, not as report-only extras. [CITED: AGENTS.md]
- Backtesting evidence is a later phase gate, so Phase 03 artifacts must be replayable: exact feature columns, split boundaries, model parameters, calibrator method, and environment metadata should be persisted now. [CITED: AGENTS.md][CITED: .planning/ROADMAP.md]
- Current repo conventions already prefer typed contracts, repo-local storage paths, DuckDB table replacement helpers, and focused unit tests. Phase 03 should extend those patterns instead of introducing a separate service or database tier. [CITED: src/tennisprediction/config.py][CITED: src/tennisprediction/storage/duckdb.py][CITED: tests/unit/test_feature_persistence.py]
- Project workflow guidance says file-changing work should happen through GSD workflows. The planner should keep execution aligned with the phase workflow rather than bypassing planning artifacts. [CITED: AGENTS.md]

## Summary

Phase 03 should be planned as a frozen-dataset and frozen-artifact phase, not merely a “train some models” phase. The key input contract already exists: Phase 02 persists `feature_differential_rows` with match identity, feature version, `as_of_date`, surface, tournament level, round, A/B-prefixed player-side features, differential features, missingness flags, exposure counts, and raw source lineage. That means the dataset builder should read persisted rows and join only the match outcome label from `canonical_matches`; it should never rebuild tennis state in model code. [CITED: src/tennisprediction/features/persistence.py][CITED: src/tennisprediction/storage/duckdb.py][CITED: .planning/phases/02-leakage-safe-feature-engine/02-VERIFICATION.md]

The most important planning constraint is the calibration boundary. Scikit-learn’s calibration docs explicitly require fitted-model calibration data to be disjoint from the model-fitting data, while XGBoost’s docs show that early stopping consumes the validation set during fitting. The implication for this repo is straightforward: reserve the external Phase 03 validation window for calibration and model-selection reporting, and keep any XGBoost early-stopping or hyperparameter search strictly inside the training window. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html][CITED: https://scikit-learn.org/stable/modules/calibration.html][CITED: https://xgboost.readthedocs.io/en/stable/python/python_intro.html][CITED: https://xgboost.readthedocs.io/en/stable/python/python_api.html]

The artifact registry should be project-owned and filesystem-first. The repo already has `models_dir`, `reports_dir`, manifest patterns, and a local DuckDB-centric architecture. Use immutable run directories under `models/` as the canonical artifact surface, typed JSON manifests for source/feature/split/model provenance, separate saved estimator and calibrator files, and optional MLflow tracking as a secondary experiment ledger rather than the only source of truth. [CITED: src/tennisprediction/config.py][CITED: src/tennisprediction/ingestion/manifests.py][CITED: .planning/research/ARCHITECTURE.md][CITED: https://mlflow.org/docs/latest/ml/tracking/][CITED: https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/][ASSUMED]

**Primary recommendation:** Plan Phase 03 around four concrete layers: `dataset builder -> split manifest -> model/calibration runners -> immutable artifact registry`, with training code consuming only persisted Phase 02 differential rows and canonical match labels. [CITED: .planning/ROADMAP.md][CITED: src/tennisprediction/features/persistence.py][CITED: .planning/research/ARCHITECTURE.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Label-ready dataset materialization from persisted feature outputs | API / Backend | Database / Storage | The modeling layer owns column selection and label definition, but data is read from persisted DuckDB tables produced by earlier phases. [CITED: src/tennisprediction/features/persistence.py][CITED: src/tennisprediction/storage/duckdb.py] |
| Chronological split freezing and split-manifest persistence | Database / Storage | API / Backend | Split manifests are durable artifacts consumed by later phases, while the backend code computes them. [CITED: .planning/research/ARCHITECTURE.md][ASSUMED] |
| Baseline and XGBoost training | API / Backend | — | Training logic, preprocessing, and calibration orchestration belong in backend code. [CITED: .planning/ROADMAP.md][CITED: .planning/REQUIREMENTS.md] |
| Probability calibration on a disjoint validation window | API / Backend | — | Calibration is algorithmic model logic, not a storage responsibility, though its outputs must be persisted. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html] |
| Artifact registry and experiment ledger | Database / Storage | API / Backend | Artifacts, manifests, and reports are persistent assets; the backend just writes and validates them. [CITED: src/tennisprediction/config.py][CITED: https://mlflow.org/docs/latest/ml/tracking/][ASSUMED] |
| Metrics, calibration curves, and segment diagnostics | API / Backend | Database / Storage | Evaluation logic belongs in backend code, but outputs should persist under `reports/` and artifact manifests. [CITED: src/tennisprediction/config.py][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.calibration_curve.html] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `duckdb` | `1.5.3` installed locally. [CITED: pyproject.toml][CITED: local env probe: `./.venv/bin/python -c import duckdb`] | Read persisted Phase 01/02 tables and materialize dataset slices reproducibly | The repo already uses DuckDB as the canonical local analytical store and table helper pattern. [CITED: src/tennisprediction/storage/duckdb.py] |
| `pandas` [WARNING: flagged as suspicious — verify before using.] | Project target `3.0.x`; registry latest observed `3.0.3` published `2026-05-11`. [CITED: AGENTS.md][CITED: https://pypi.org/pypi/pandas/json] | DataFrame bridge into scikit-learn and XGBoost training code | Current repo transforms are Polars-first, but the project stack already treats pandas as the compatibility edge for modeling. [CITED: AGENTS.md] |
| `scikit-learn` [WARNING: flagged as suspicious — verify before using.] | Project target `1.9.x`; registry latest observed `1.9.0` published `2026-06-02`. [CITED: AGENTS.md][CITED: https://pypi.org/pypi/scikit-learn/json] | Logistic regression, random forest, calibration, metrics, and shared pipelines | Official docs cover the exact primitives Phase 03 needs: `LogisticRegression`, `RandomForestClassifier`, `Pipeline`, `SimpleImputer`, `CalibratedClassifierCV`, `roc_auc_score`, `log_loss`, `brier_score_loss`, and `calibration_curve`. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.impute.SimpleImputer.html][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html] |
| `xgboost` [WARNING: flagged as suspicious — verify before using.] | Project target `3.2.x`; registry latest observed `3.3.0` published `2026-06-17`. [CITED: AGENTS.md][CITED: https://pypi.org/pypi/xgboost/json] | Production-candidate gradient-boosted tree model | Official docs provide the Python scikit-learn interface, native `NaN` handling, and early-stopping behavior needed for a phase-appropriate candidate model. [CITED: https://xgboost.readthedocs.io/en/stable/python/python_intro.html][CITED: https://xgboost.readthedocs.io/en/stable/python/python_api.html] |
| `joblib` [WARNING: flagged as suspicious — verify before using.] | Project target `1.5.x`; registry latest observed `1.5.3` published `2025-12-15`. [CITED: AGENTS.md][CITED: https://pypi.org/pypi/joblib/json] | Trusted local persistence for sklearn-compatible estimators and calibrators | Scikit-learn’s model persistence guide explicitly lists joblib as a standard persistence option, with the caveat that it requires the same environment and should only load trusted artifacts. [CITED: https://scikit-learn.org/stable/model_persistence.html] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `matplotlib` [WARNING: flagged as suspicious — verify before using.] | Project target `3.11.x`; registry latest observed `3.11.0` published `2026-06-12`. [CITED: AGENTS.md][CITED: https://pypi.org/pypi/matplotlib/json] | Save calibration curves and evaluation plots into report artifacts | Use for static reliability diagrams and score plots referenced from the artifact manifest. [CITED: AGENTS.md][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.calibration_curve.html] |
| `mlflow` [WARNING: flagged as suspicious — verify before using.] | Project target `3.13.x`; registry latest observed `3.14.0` published `2026-06-17`. [CITED: AGENTS.md][CITED: https://pypi.org/pypi/mlflow/json] | Optional secondary experiment ledger for params, metrics, and artifact links | Use as a local tracking surface if the team wants run comparison and UI, but keep the project-owned artifact manifest as canonical. MLflow Tracking supports local file-based backend stores, while full Model Registry features require a database-backed store. [CITED: https://mlflow.org/docs/latest/ml/tracking/][CITED: https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/][ASSUMED] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Explicit split manifests as the official holdout contract | `TimeSeriesSplit` alone | `TimeSeriesSplit` is useful for inner walk-forward validation, but official docs note it assumes equally spaced samples; the repo still needs immutable final train/validation/test membership for replayable artifacts. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html][ASSUMED] |
| Project-owned local artifact directories plus optional MLflow mirroring | MLflow Model Registry as the only registry | MLflow Tracking fits local experimentation, but official docs say full Model Registry requires a database-backed store; that is unnecessary operational weight for this repo right now. [CITED: https://mlflow.org/docs/latest/ml/tracking/][CITED: https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/] |
| Separate raw estimator artifact plus separate calibrator artifact | One opaque “final predictor” blob only | A single blob is simpler to load, but it hides whether a model was trained on train only, how it was calibrated, and whether recalibration can be replayed later. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html][ASSUMED] |
| Same ordered feature contract for all model families | Bespoke column sets per model | One contract reduces downstream replay risk and makes backtesting/live prediction reuse straightforward; model-specific preprocessing can still differ by trainer. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-VERIFICATION.md][ASSUMED] |

**Installation:** Add an `ml` dependency group to `pyproject.toml`, then sync the environment with the project-standard module runner `python3 -m uv`. The standalone `uv` binary is not on `PATH` here, but the Python module is available and matches the plan verification commands. [CITED: AGENTS.md][CITED: pyproject.toml][CITED: local env probe: `python3 -m uv --version`][CITED: local env probe: `command -v uv`]

```bash
python3 -m uv sync --group dev --group ml
```

**Version verification:** The local `.venv` currently has no `pip`, so version verification had to use host `python3 -m pip index versions` plus PyPI JSON. [CITED: local env probe: `./.venv/bin/python -m pip --version`][CITED: https://pypi.org/pypi/scikit-learn/json][CITED: https://pypi.org/pypi/xgboost/json][CITED: https://pypi.org/pypi/mlflow/json][CITED: https://pypi.org/pypi/joblib/json][CITED: https://pypi.org/pypi/pandas/json][CITED: https://pypi.org/pypi/matplotlib/json]

```bash
python3 -m pip index versions scikit-learn
python3 -m pip index versions xgboost
python3 -m pip index versions mlflow
python3 -m pip index versions joblib
python3 -m pip index versions pandas
python3 -m pip index versions matplotlib
```

## Package Legitimacy Audit

> **Required** because Phase 03 adds external modeling and reporting packages beyond the current repo environment. The legitimacy seam flagged every proposed package as `SUS`, so the planner should insert `checkpoint:human-verify` before any fresh install. [CITED: local env probe: modeling imports][CITED: package-legitimacy seam]

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `scikit-learn` | PyPI [CITED: https://pypi.org/pypi/scikit-learn/json] | 15d [CITED: https://pypi.org/pypi/scikit-learn/json] | unknown [CITED: package-legitimacy seam] | none [CITED: package-legitimacy seam] | `SUS` [CITED: package-legitimacy seam] | Flagged — planner must add `checkpoint:human-verify` before install. |
| `xgboost` | PyPI [CITED: https://pypi.org/pypi/xgboost/json] | 0d [CITED: https://pypi.org/pypi/xgboost/json] | unknown [CITED: package-legitimacy seam] | none [CITED: package-legitimacy seam] | `SUS` [CITED: package-legitimacy seam] | Flagged — planner must add `checkpoint:human-verify` before install. |
| `mlflow` | PyPI [CITED: https://pypi.org/pypi/mlflow/json] | 0d [CITED: https://pypi.org/pypi/mlflow/json] | unknown [CITED: package-legitimacy seam] | none [CITED: package-legitimacy seam] | `SUS` [CITED: package-legitimacy seam] | Flagged — planner must add `checkpoint:human-verify` before install. |
| `joblib` | PyPI [CITED: https://pypi.org/pypi/joblib/json] | 184d [CITED: https://pypi.org/pypi/joblib/json] | unknown [CITED: package-legitimacy seam] | `https://github.com/joblib/joblib` [CITED: package-legitimacy seam] | `SUS` [CITED: package-legitimacy seam] | Flagged — planner must add `checkpoint:human-verify` before install. |
| `pandas` | PyPI [CITED: https://pypi.org/pypi/pandas/json] | 37d [CITED: https://pypi.org/pypi/pandas/json] | unknown [CITED: package-legitimacy seam] | none [CITED: package-legitimacy seam] | `SUS` [CITED: package-legitimacy seam] | Flagged — planner must add `checkpoint:human-verify` before install. |
| `matplotlib` | PyPI [CITED: https://pypi.org/pypi/matplotlib/json] | 5d [CITED: https://pypi.org/pypi/matplotlib/json] | unknown [CITED: package-legitimacy seam] | `https://matplotlib.org` [CITED: package-legitimacy seam] | `SUS` [CITED: package-legitimacy seam] | Flagged — planner must add `checkpoint:human-verify` before install. |

**Packages removed due to [SLOP] verdict:** none. [CITED: package-legitimacy seam]
**Packages flagged as suspicious [SUS]:** `scikit-learn`, `xgboost`, `mlflow`, `joblib`, `pandas`, `matplotlib`. The planner should gate each install behind `checkpoint:human-verify`. [CITED: package-legitimacy seam]

## Architecture Patterns

### System Architecture Diagram

```text
Persisted Phase 02 DuckDB tables
  feature_differential_rows
  canonical_matches
          |
          v
Dataset builder
  - select one ordered feature contract
  - join label: player_a_id == winner_canonical_player_id
  - assert one feature_version + one source snapshot lineage set
          |
          v
Split builder
  - sort chronologically
  - freeze train / validation / test membership
  - write split manifest with hashes + counts
          |
          +------------------------------+
          |                              |
          v                              v
Raw model trainer                    Evaluation runner
  logistic pipeline                    - accuracy / ROC AUC
  random forest                        - log loss / Brier
  XGBoost candidate                    - calibration bins / ECE
          |                             - segment diagnostics
          v                              |
Calibration runner <---------------------+
  fit calibrator on validation only
  keep raw and calibrated outputs separate
          |
          v
Artifact registry
  models/<artifact_id>/
    manifest.json
    split_manifest.json
    feature_columns.json
    model.joblib or model.ubj
    calibrator.joblib
    metrics.json
    segments.parquet
    calibration_curve.csv
    environment.json
          |
          v
Optional MLflow mirror
  params / metrics / artifact links
```

### Recommended Project Structure

```text
src/tennisprediction/modeling/
├── __init__.py          # public modeling exports
├── schemas.py           # split and artifact manifest contracts
├── datasets.py          # DuckDB reads, label joins, feature column ordering
├── splits.py            # chronological split builder and manifest writer
├── baselines.py         # logistic regression and random forest trainers
├── xgboost_model.py     # XGBoost trainer and early-stopping logic
├── calibration.py       # disjoint validation calibration helpers
├── metrics.py           # scalar metrics, calibration bins, ECE, segments
├── registry.py          # local artifact save/load and manifest validation
└── reports.py           # report-file writers under reports/

tests/unit/
├── test_modeling_datasets.py
├── test_modeling_splits.py
├── test_modeling_baselines.py
├── test_modeling_xgboost.py
├── test_modeling_calibration.py
├── test_modeling_metrics.py
└── test_modeling_registry.py
```

### Pattern 1: Build Datasets from Persisted Differential Rows
**What:** Treat `feature_differential_rows` as the single model-input table and join only the target label from `canonical_matches`. [CITED: src/tennisprediction/features/persistence.py][CITED: src/tennisprediction/storage/duckdb.py]  
**When to use:** Always; Phase 02 explicitly made persisted differential rows the downstream model-ready contract. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-VERIFICATION.md]  
**Example:**

```python
# Source: src/tennisprediction/features/persistence.py
SELECT
  d.*,
  CASE
    WHEN d.player_a_id = m.winner_canonical_player_id THEN 1
    ELSE 0
  END AS player_a_wins
FROM feature_differential_rows AS d
JOIN canonical_matches AS m USING (canonical_match_id)
ORDER BY
  d.as_of_date,
  d.round_name,
  d.lineage_source_file_path,
  d.lineage_source_row_number;
```

### Pattern 2: Freeze Split Membership in a Typed Manifest
**What:** Save a manifest that records chronological boundary dates, exact match membership, row counts, feature version, label definition, and membership hashes for train/validation/test. [CITED: src/tennisprediction/ingestion/manifests.py][ASSUMED]  
**When to use:** For every official training run and every replayable backtest input. [CITED: .planning/research/ARCHITECTURE.md]  
**Example:**

```python
# Source: src/tennisprediction/ingestion/manifests.py
class SplitManifest(BaseModel):
    dataset_id: str
    feature_version: str
    source_commit_sha: str
    label_definition: str
    train_match_ids_sha256: str
    validation_match_ids_sha256: str
    test_match_ids_sha256: str
    train_row_count: int
    validation_row_count: int
    test_row_count: int
```

### Pattern 3: Train Raw Estimator First, Calibrate Second
**What:** Fit the underlying estimator on the training window, then calibrate that fitted estimator on the disjoint validation window with `FrozenEstimator`. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html][CITED: https://scikit-learn.org/stable/modules/calibration.html]  
**When to use:** For all official Phase 03 calibrated models. [CITED: .planning/REQUIREMENTS.md]  
**Example:**

```python
# Source: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html
raw_model.fit(X_train, y_train)
calibrator = CalibratedClassifierCV(
    estimator=FrozenEstimator(raw_model),
    method="sigmoid",
)
calibrator.fit(X_validation, y_validation)
```

### Pattern 4: Immutable Local Artifact Bundle with Optional MLflow Mirror
**What:** Write one immutable run directory under `models/` as the canonical artifact bundle, then optionally mirror params, metrics, and artifact links to MLflow Tracking. [CITED: src/tennisprediction/config.py][CITED: https://mlflow.org/docs/latest/ml/tracking/][ASSUMED]  
**When to use:** For every baseline and candidate model that can be promoted to Phase 04 replay. [CITED: .planning/ROADMAP.md]  
**Example:**

```python
# Source: https://mlflow.org/docs/latest/api_reference/python_api/mlflow.html
artifact_dir = settings.models_dir / artifact_id
artifact_dir.mkdir(parents=True, exist_ok=False)
manifest_path.write_text(manifest.model_dump_json(indent=2))

with mlflow.start_run():
    mlflow.log_params(manifest.model_params)
    mlflow.log_metrics(manifest.test_metrics)
    mlflow.log_artifact(manifest_path)
```

### Anti-Patterns to Avoid

- **Reading `feature_player_snapshots` directly for training labels:** That doubles each match into two rows and bypasses the Phase 02 downstream differential contract. Use `feature_differential_rows` as the modeling table and join the outcome label from `canonical_matches`. [CITED: src/tennisprediction/features/schemas.py][CITED: src/tennisprediction/features/persistence.py]
- **Using the external calibration split for XGBoost early stopping:** XGBoost docs show that `eval_set` drives fitting-time early stopping, while sklearn calibration docs require disjoint fit and calibration data. Keep early stopping inside the training window only. [CITED: https://xgboost.readthedocs.io/en/stable/python/python_intro.html][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html]
- **Relying on `TimeSeriesSplit` alone as the official holdout contract:** It is useful for inner CV, but the repo still needs frozen membership manifests for reproducibility and later replay. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html][ASSUMED]
- **Saving only an XGBoost `.json`/`.ubj` file and calling that the registry:** XGBoost docs say model IO does not save non-model parameters and metrics; persist a separate manifest with hyperparameters, feature columns, and environment metadata. [CITED: https://xgboost.readthedocs.io/en/stable/python/python_api.html]
- **Evaluating only AUC or accuracy:** The project requires calibrated probabilities, so log loss, Brier, calibration bins, and ECE must be first-class outputs. [CITED: AGENTS.md][CITED: .planning/REQUIREMENTS.md][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Probability calibration | Custom Platt-scaling or isotonic implementations | `CalibratedClassifierCV` with `FrozenEstimator` [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html] | Official implementation already handles calibration methods and the fit/calibration separation model Phase 03 needs. [CITED: https://scikit-learn.org/stable/modules/calibration.html] |
| Gradient-boosted tree learner | A project-owned boosting algorithm | `XGBClassifier` [CITED: https://xgboost.readthedocs.io/en/stable/python/python_intro.html] | The project needs a strong tabular candidate, not a custom ML algorithm. Official docs already cover missing values, early stopping, and sklearn compatibility. [CITED: https://xgboost.readthedocs.io/en/stable/python/python_api.html] |
| Reliability-curve binning | Ad hoc calibration-bin math for the core curve | `calibration_curve` [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.calibration_curve.html] | Official binning semantics keep reliability plots consistent; project code should only add ECE aggregation on top. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.calibration_curve.html][ASSUMED] |
| Experiment-run UI / run comparison | Custom SQLite or HTML experiment browser | MLflow Tracking [CITED: https://mlflow.org/docs/latest/ml/tracking/] | MLflow already logs params, metrics, code versions, and artifacts; Phase 03 should spend custom code on domain manifests, not generic run dashboards. [CITED: https://mlflow.org/docs/latest/ml/tracking/] |
| Opaque model blob format | One pickled dict with undocumented keys | joblib for estimator/calibrator + typed JSON manifests [CITED: https://scikit-learn.org/stable/model_persistence.html][CITED: src/tennisprediction/ingestion/manifests.py] | Scikit-learn docs explicitly recommend saving environment and training metadata alongside persisted models, which Phase 04 replay will need. [CITED: https://scikit-learn.org/stable/model_persistence.html] |

**Key insight:** Custom code in this phase should be domain-specific only at the seams libraries do not cover: label joins, split manifests, exact feature-column contracts, artifact provenance, and tennis-specific segment definitions. Generic ML primitives should come from official libraries. [CITED: .planning/research/ARCHITECTURE.md][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html][CITED: https://xgboost.readthedocs.io/en/stable/python/python_intro.html]

## Common Pitfalls

### Pitfall 1: Split Drift Between Training Runs
**What goes wrong:** Two runs claim to use the same train/validation/test periods but actually contain different match sets because only date cutoffs were saved. [ASSUMED]  
**Why it happens:** ATP schedules are irregular and multiple matches can share a date boundary; cutoffs alone do not prove exact membership. [ASSUMED]  
**How to avoid:** Persist match membership hashes and row counts per split, not just cutoff dates. [ASSUMED]  
**Warning signs:** Same boundary dates but different row counts, or a rerun cannot reproduce identical match IDs. [ASSUMED]

### Pitfall 2: Leakage Through Calibration or Early Stopping
**What goes wrong:** The same validation window is used both to steer model fitting and to fit the calibrator, which contaminates reported test probabilities. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html][CITED: https://xgboost.readthedocs.io/en/stable/python/python_intro.html]  
**Why it happens:** XGBoost early stopping consumes a validation set during fitting, while sklearn calibration expects disjoint calibration data for an already fitted model. [CITED: https://xgboost.readthedocs.io/en/stable/python/python_intro.html][CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html]  
**How to avoid:** Keep any XGBoost early stopping or tuning entirely within the training window, then reserve the external validation window for calibration only. [CITED: https://xgboost.readthedocs.io/en/stable/python/python_api.html][CITED: https://scikit-learn.org/stable/modules/calibration.html][ASSUMED]  
**Warning signs:** The calibrator was fit on the same rows passed as `eval_set`, or the saved artifact manifest cannot distinguish raw-train versus calibration datasets. [ASSUMED]

### Pitfall 3: Losing the Feature Contract at Persistence Time
**What goes wrong:** A saved model loads successfully, but later prediction code cannot reconstruct the exact feature-column order or source/feature version used at train time. [CITED: https://scikit-learn.org/stable/model_persistence.html]  
**Why it happens:** A joblib or XGBoost model file is persisted without a separate manifest, and XGBoost model IO does not save all non-model parameters. [CITED: https://xgboost.readthedocs.io/en/stable/python/python_api.html][CITED: https://scikit-learn.org/stable/model_persistence.html]  
**How to avoid:** Save an ordered feature-column list, feature version, source commit SHA, dependency versions, and split manifest reference beside every persisted artifact. [CITED: https://scikit-learn.org/stable/model_persistence.html][CITED: src/tennisprediction/features/schemas.py][ASSUMED]  
**Warning signs:** Artifact load paths exist, but the loader has to “guess” the columns or infer version from the directory name. [ASSUMED]

### Pitfall 4: Choosing Calibration Method by Habit
**What goes wrong:** Isotonic calibration is applied by default on a small validation set and overfits badly, or sigmoid is used blindly despite enough data for isotonic to help. [CITED: https://scikit-learn.org/stable/modules/calibration.html]  
**Why it happens:** The calibration method is treated as a static preference instead of an evaluated model artifact attribute. [ASSUMED]  
**How to avoid:** Treat `sigmoid` as the baseline comparison, then evaluate `isotonic` only when the validation window is large enough and the resulting test metrics justify it. [CITED: https://scikit-learn.org/stable/modules/calibration.html][ASSUMED]  
**Warning signs:** Validation bins look overly stepwise, AUC changes unexpectedly after isotonic calibration, or the method is absent from the artifact manifest. [CITED: https://scikit-learn.org/stable/modules/calibration.html][ASSUMED]

### Pitfall 5: Assuming the Environment Is Already Ready
**What goes wrong:** The phase plan assumes the full ML environment is ready when, in reality, only the `python3 -m uv` runner and dev tools are present while the modeling packages themselves are still missing from the current `.venv`. [CITED: local env probe: `python3 -m uv --version`][CITED: local env probe: modeling imports]  
**Why it happens:** The foundation/feature phases passed, so it is easy to assume the full ML stack is already present. [CITED: .planning/STATE.md][CITED: local env probe: modeling imports]  
**How to avoid:** Keep verification commands on `python3 -m uv run` from Wave 1 onward, because that runner already works in this environment, and insert the ML dependency/bootstrap task before any modeling imports or sync-sensitive tests. [CITED: pyproject.toml][CITED: local env probe: `python3 -m uv run pytest --version`]  
**Warning signs:** The bare `uv` command is not found on `PATH`, `.venv` lacks `pip`, and imports for `pandas`, `sklearn`, `xgboost`, `joblib`, `mlflow`, and `matplotlib` all fail. [CITED: local env probe: `command -v uv`][CITED: local env probe: `./.venv/bin/python -m pip --version`][CITED: local env probe: modeling imports]

## Code Examples

Verified patterns from official sources and existing repo contracts:

### Join Labels Without Recomputing Features

```python
# Source: src/tennisprediction/features/persistence.py
query = """
select
  d.*,
  case when d.player_a_id = m.winner_canonical_player_id then 1 else 0 end as target
from feature_differential_rows d
join canonical_matches m using (canonical_match_id)
"""
```

### Calibrate an Already Fitted Model on a Disjoint Window

```python
# Source: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html
raw_model.fit(X_train, y_train)
calibrated_model = CalibratedClassifierCV(
    estimator=FrozenEstimator(raw_model),
    method="sigmoid",
)
calibrated_model.fit(X_validation, y_validation)
```

### Persist an Artifact Manifest Beside Saved Model Files

```python
# Source: https://scikit-learn.org/stable/model_persistence.html
joblib.dump(raw_model, artifact_dir / "model.joblib")
joblib.dump(calibrated_model, artifact_dir / "calibrator.joblib")
(artifact_dir / "feature_columns.json").write_text(json.dumps(feature_columns, indent=2))
(artifact_dir / "manifest.json").write_text(manifest.model_dump_json(indent=2))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Random shuffled classification holdouts | Frozen chronological train/validation/test datasets with optional walk-forward CV only inside training | Locked by project requirements on `2026-06-16`. [CITED: .planning/REQUIREMENTS.md] | Makes reported probabilities and later EV backtests temporally defensible. [CITED: AGENTS.md] |
| Uncalibrated class probabilities as the main output | Disjoint calibration and probability-quality metrics | Locked by project requirements on `2026-06-16`. [CITED: AGENTS.md][CITED: .planning/REQUIREMENTS.md] | Model selection must optimize trustworthy probabilities, not just discrimination. [CITED: AGENTS.md] |
| Single model blob with implicit metadata | Separate model/calibrator artifacts plus explicit manifests and reports | Recommended for this repo now. [CITED: https://scikit-learn.org/stable/model_persistence.html][CITED: https://xgboost.readthedocs.io/en/stable/python/python_api.html][ASSUMED] | Later phases can replay, inspect, and validate exact training provenance. [CITED: .planning/research/ARCHITECTURE.md] |
| MLflow registry as the only artifact surface | Project-owned local registry plus optional MLflow tracking mirror | Recommended for this repo now because local MLflow tracking works without a DB-backed model registry. [CITED: https://mlflow.org/docs/latest/ml/tracking/][CITED: https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/] | Keeps Phase 03 operationally light while still allowing experiment comparison. [ASSUMED] |

**Deprecated/outdated:**

- Treating `TimeSeriesSplit` as the sole persisted holdout definition for this domain is outdated for this repo; use it only as an inner validation helper, not as the official dataset registry. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html][ASSUMED]
- Saving only an XGBoost native model file without a manifest is insufficient because official model IO omits non-model parameters and metrics. [CITED: https://xgboost.readthedocs.io/en/stable/python/python_api.html]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The logistic regression benchmark should include a scaling step after imputation. [ASSUMED] | Phase Requirements / Standard Stack | Low to medium. The planner may over-specify preprocessing if the implementation team wants a simpler no-scaling baseline. |
| A2 | Split manifests should store exact match membership hashes, not just boundary dates. [ASSUMED] | Summary / Architecture Patterns / Common Pitfalls | Medium. Without membership hashing, replayability and dispute resolution will be weaker than recommended. |
| A3 | MLflow should be a secondary experiment ledger while the project-owned local artifact directory stays canonical. [ASSUMED] | Summary / Standard Stack / Architecture Patterns | Medium. If the team wants MLflow-first registry behavior, planner task ordering and dependency footprint will differ. |
| A4 | Segment diagnostics should persist explicit bucket definitions for ranking bands and confidence buckets in the artifact manifest. [ASSUMED] | Phase Requirements / Common Pitfalls | Low. The metrics still work, but cross-run comparability becomes weaker if bins are implicit. |
| A5 | `TimeSeriesSplit` is not sufficient as the official holdout contract for ATP match data because the repo needs immutable replayable membership, not just generated folds. [ASSUMED] | Standard Stack / State of the Art | Medium. If the team is comfortable generating folds on the fly, registry design could be simplified at the cost of reproducibility. |

## Resolved Research Decisions

> Resolved on 2026-06-18 during planning revision 2. Execution is not blocked on either item.

1. **Version drift versus project targets**
   - Decision: Hold the documented Phase 03 target bands from `AGENTS.md` for execution. Use the project-target `xgboost 3.2.x` range in the mandatory `ml` dependency group for this phase, and keep `mlflow 3.13.x` as an optional later addition rather than silently upgrading stack policy to the newest observed releases. [CITED: AGENTS.md][CITED: https://pypi.org/pypi/xgboost/json][CITED: https://pypi.org/pypi/mlflow/json]
   - Why: `AGENTS.md` is the governing stack contract for this repo, and the current Phase 03 plans do not require a stack-policy change to deliver MOD-01 through MOD-08. [CITED: AGENTS.md][CITED: .planning/REQUIREMENTS.md]
   - Execution impact: Plan `03-02` should keep the mandatory install surface limited to `pandas`, `scikit-learn`, `xgboost`, and `joblib`, with `mlflow` remaining optional and out of the required bootstrap path. [CITED: .planning/phases/03-modeling-calibration-and-artifact-registry/03-02-PLAN.md]

2. **First official split windows**
   - Decision: The first official Phase 03 split manifest uses the project-wide chronological `70/15/15` split policy already recorded in `.planning/research/FEATURES.md`, applied to the fully ordered modeling dataset materialized from persisted Phase 02 differential rows. The split freezer must persist the resolved inclusive train, validation, and test end dates plus exact ordered memberships and hashes in the manifest. [CITED: .planning/research/FEATURES.md][CITED: .planning/REQUIREMENTS.md][CITED: .planning/phases/03-modeling-calibration-and-artifact-registry/03-01-PLAN.md]
   - Why: The repo already committed to chronological `70/15/15` evaluation at the project-research level, and freezing the resolved memberships removes the last execution-time ambiguity without reintroducing shuffled or ad hoc holdouts. [CITED: .planning/research/FEATURES.md][CITED: AGENTS.md]
   - Execution impact: Plan `03-01` should derive the first canonical boundary dates from the ordered dataset using the `70/15/15` policy, then persist those dates and exact memberships as the replayable split contract for all later Phase 03 plans. [CITED: .planning/phases/03-modeling-calibration-and-artifact-registry/03-01-PLAN.md]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python `.venv` runtime | All Phase 03 code/tests | ✓ [CITED: local env probe: `./.venv/bin/python --version`] | 3.12.4 [CITED: local env probe: `./.venv/bin/python --version`] | — |
| `pytest` in `.venv` | Unit-test execution | ✓ [CITED: local env probe: baseline imports] | 9.1.0 [CITED: local env probe: baseline imports] | — |
| `git` | Provenance / optional artifact metadata | ✓ [CITED: local env probe: `git --version`] | 2.52.0 [CITED: local env probe: `git --version`] | — |
| `python3 -m uv` | Project-standard dependency sync and command runner | ✓ [CITED: local env probe: `python3 -m uv --version`] | 0.11.21 [CITED: local env probe: `python3 -m uv --version`] | Use the module runner because the standalone `uv` binary is not on `PATH`. [CITED: local env probe: `command -v uv`] |
| `pandas` | Model-input DataFrame bridge | ✗ [CITED: local env probe: modeling imports] | — | none |
| `scikit-learn` | Baselines, calibration, metrics | ✗ [CITED: local env probe: modeling imports] | — | none |
| `xgboost` | Candidate model | ✗ [CITED: local env probe: modeling imports] | — | none |
| `joblib` | Local model persistence | ✗ [CITED: local env probe: modeling imports] | — | none |
| `mlflow` | Optional run tracking | ✗ [CITED: local env probe: modeling imports] | — | Use local manifest-only registry first. [ASSUMED] |
| `matplotlib` | Plot artifacts | ✗ [CITED: local env probe: modeling imports] | — | Save calibration-bin CSV/JSON without plots until installed. [ASSUMED] |
| `duckdb`, `polars`, `pyarrow` | Existing Phase 01/02 data access | ✓ [CITED: local env probe: baseline imports] | 1.5.3 / 1.41.2 / 24.0.0 [CITED: local env probe: baseline imports] | — |

**Missing dependencies with no fallback:**

- `pandas`
- `scikit-learn`
- `xgboost`
- `joblib`

**Missing dependencies with fallback:**

- `mlflow` — Phase 03 can ship a manifest-first local registry without MLflow initially. [ASSUMED]
- `matplotlib` — Phase 03 can still persist calibration-bin tables and scalar metrics before plot rendering is installed. [ASSUMED]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.1.0` in the local `.venv`. [CITED: local env probe: baseline imports] |
| Config file | `pyproject.toml`. [CITED: pyproject.toml] |
| Quick run command | `./.venv/bin/python -m pytest -q tests/unit/test_modeling_* -x` [ASSUMED] |
| Full suite command | `./.venv/bin/python -m pytest -q` [CITED: local env probe: `./.venv/bin/python -m pytest -q tests/unit/test_feature_runner.py tests/unit/test_feature_persistence.py`] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MOD-01 | Frozen datasets come from persisted feature rows and chronological split manifests only | unit | `./.venv/bin/python -m pytest -q tests/unit/test_modeling_datasets.py tests/unit/test_modeling_splits.py -x` | ❌ Wave 0 |
| MOD-02 | Logistic regression benchmark trains on the shared feature contract | unit | `./.venv/bin/python -m pytest -q tests/unit/test_modeling_baselines.py -k logistic -x` | ❌ Wave 0 |
| MOD-03 | Random forest benchmark trains on the shared feature contract | unit | `./.venv/bin/python -m pytest -q tests/unit/test_modeling_baselines.py -k forest -x` | ❌ Wave 0 |
| MOD-04 | XGBoost candidate respects train-only fitting and saved best-iteration metadata | unit | `./.venv/bin/python -m pytest -q tests/unit/test_modeling_xgboost.py -x` | ❌ Wave 0 |
| MOD-05 | Calibration uses only the disjoint validation window | unit | `./.venv/bin/python -m pytest -q tests/unit/test_modeling_calibration.py -x` | ❌ Wave 0 |
| MOD-06 | Metrics include accuracy, ROC AUC, log loss, Brier, calibration bins, and ECE | unit | `./.venv/bin/python -m pytest -q tests/unit/test_modeling_metrics.py -x` | ❌ Wave 0 |
| MOD-07 | Segment diagnostics are saved for required slices | unit | `./.venv/bin/python -m pytest -q tests/unit/test_modeling_metrics.py -k segment -x` | ❌ Wave 0 |
| MOD-08 | Artifact registry persists source/feature/split/model/calibrator provenance and loads it safely | unit | `./.venv/bin/python -m pytest -q tests/unit/test_modeling_registry.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `./.venv/bin/python -m pytest -q tests/unit/test_modeling_* -x` [ASSUMED]
- **Per wave merge:** `./.venv/bin/python -m pytest -q tests/unit/test_modeling_* tests/unit/test_feature_*.py` [ASSUMED]
- **Phase gate:** Full suite green before `$gsd-verify-work`. [CITED: AGENTS.md][CITED: .planning/config.json]

### Wave 0 Gaps

- [ ] `tests/unit/test_modeling_datasets.py` — dataset builder and label-join coverage for MOD-01. [ASSUMED]
- [ ] `tests/unit/test_modeling_splits.py` — manifest freezing, ordering, and membership-hash coverage for MOD-01. [ASSUMED]
- [ ] `tests/unit/test_modeling_baselines.py` — logistic and random forest trainer coverage for MOD-02 and MOD-03. [ASSUMED]
- [ ] `tests/unit/test_modeling_xgboost.py` — XGBoost train-only tuning / early-stopping coverage for MOD-04. [ASSUMED]
- [ ] `tests/unit/test_modeling_calibration.py` — disjoint validation calibration coverage for MOD-05. [ASSUMED]
- [ ] `tests/unit/test_modeling_metrics.py` — scalar metrics, calibration bins, ECE, and segment diagnostics coverage for MOD-06 and MOD-07. [ASSUMED]
- [ ] `tests/unit/test_modeling_registry.py` — artifact manifest, load, and provenance coverage for MOD-08. [ASSUMED]
- [ ] Dependency bootstrap task — modeling packages are not installed in the current `.venv`, so no Phase 03 test file will run until the environment is extended. [CITED: local env probe: modeling imports]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No user-auth surface is introduced in this phase. [CITED: .planning/ROADMAP.md] |
| V3 Session Management | no | No session surface is introduced in this phase. [CITED: .planning/ROADMAP.md] |
| V4 Access Control | no | Phase 03 is local/offline model work, not a multi-user service boundary. [CITED: .planning/ROADMAP.md] |
| V5 Input Validation | yes | Validate split manifests, artifact manifests, and model metadata with typed contracts patterned after `SourceManifest`; validate label joins and ordered feature-column lists before training or loading. [CITED: src/tennisprediction/ingestion/manifests.py][CITED: AGENTS.md][ASSUMED] |
| V6 Cryptography | no | No new cryptographic primitive is required in this phase; the main artifact risk is trusted loading, not custom crypto. [CITED: .planning/ROADMAP.md][CITED: https://scikit-learn.org/stable/model_persistence.html] |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Loading untrusted `joblib` / pickle-style artifacts | Elevation of Privilege | Scikit-learn docs say pickle-based persistence can execute arbitrary code; only load artifacts produced by this repo and matched by manifest provenance. [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| Model/feature version mismatch at inference time | Tampering | Persist the ordered feature-column list, feature version, source commit SHA, and dependency versions in every artifact manifest; refuse to load on mismatch. [CITED: https://scikit-learn.org/stable/model_persistence.html][CITED: src/tennisprediction/features/schemas.py][ASSUMED] |
| Calibration-set contamination | Tampering | Separate training-window fitting from validation-window calibration and save both dataset references in the manifest. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html][ASSUMED] |
| Artifact overwrite or mutable “latest” directories | Repudiation | Use immutable run directories keyed by artifact ID and never rewrite an existing artifact path in place. [CITED: src/tennisprediction/ingestion/storage_layout.py][ASSUMED] |

## Sources

### Primary (HIGH confidence)

- `src/tennisprediction/features/persistence.py` - verified Phase 02 downstream training contract and persisted column shape.
- `src/tennisprediction/storage/duckdb.py` - verified existing table-persistence pattern to reuse for manifests and artifact indexes.
- `src/tennisprediction/ingestion/manifests.py` - verified existing typed manifest convention to reuse for split and artifact manifests.
- `src/tennisprediction/config.py` - verified existing repo-local `models_dir` and `reports_dir` boundaries.
- `.planning/phases/02-leakage-safe-feature-engine/02-VERIFICATION.md` - verified Phase 02 outputs are the trusted modeling inputs.
- Local environment probes:
  - `./.venv/bin/python --version`
  - `./.venv/bin/python -m pytest -q tests/unit/test_feature_runner.py tests/unit/test_feature_persistence.py`
  - modeling import probe for `pandas`, `sklearn`, `xgboost`, `joblib`, `mlflow`, `matplotlib`
  - baseline import probe for `duckdb`, `polars`, `pyarrow`, `pytest`

### Secondary (MEDIUM confidence)

- `https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html` - fitted-model calibration and `FrozenEstimator`.
- `https://scikit-learn.org/stable/modules/calibration.html` - sigmoid vs isotonic behavior and calibration guidance.
- `https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html` - logistic regression baseline behavior.
- `https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html` - random forest behavior and native NaN support.
- `https://scikit-learn.org/stable/modules/generated/sklearn.pipeline.Pipeline.html` - pipeline composition.
- `https://scikit-learn.org/stable/modules/generated/sklearn.impute.SimpleImputer.html` - numeric imputation options.
- `https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html` - time-ordered CV constraints.
- `https://scikit-learn.org/stable/modules/generated/sklearn.metrics.roc_auc_score.html` - ROC AUC metric.
- `https://scikit-learn.org/stable/modules/generated/sklearn.metrics.log_loss.html` - log loss metric.
- `https://scikit-learn.org/stable/modules/generated/sklearn.metrics.brier_score_loss.html` - Brier score metric.
- `https://scikit-learn.org/stable/modules/generated/sklearn.calibration.calibration_curve.html` - reliability-curve binning.
- `https://scikit-learn.org/stable/model_persistence.html` - persistence options, metadata requirements, and pickle/joblib risk.
- `https://xgboost.readthedocs.io/en/stable/python/python_intro.html` - Python interfaces and early stopping behavior.
- `https://xgboost.readthedocs.io/en/stable/python/python_api.html` - missing-value handling, best-iteration behavior, and model IO caveats.
- `https://mlflow.org/docs/latest/ml/tracking/` - tracking capabilities and local backend store support.
- `https://mlflow.org/docs/latest/self-hosting/architecture/artifact-store/` - artifact-store versus metadata-store separation.
- `https://mlflow.org/docs/latest/api_reference/python_api/mlflow.html` - `start_run`, `log_params`, `log_metrics`, `log_dict`, and `log_artifact`.
- PyPI JSON endpoints for current versions and publish dates:
  - `https://pypi.org/pypi/scikit-learn/json`
  - `https://pypi.org/pypi/xgboost/json`
  - `https://pypi.org/pypi/mlflow/json`
  - `https://pypi.org/pypi/joblib/json`
  - `https://pypi.org/pypi/pandas/json`
  - `https://pypi.org/pypi/matplotlib/json`

### Tertiary (LOW confidence)

- None beyond the explicit `[ASSUMED]` items listed in the Assumptions Log.

## Metadata

**Confidence breakdown:**

- Standard stack: MEDIUM - official docs and registry endpoints are solid, but package-legitimacy automation flagged all new modeling packages as `SUS`, and the latest registry versions for `xgboost` and `mlflow` now drift above the project’s documented minor targets. [CITED: AGENTS.md][CITED: package-legitimacy seam][CITED: https://pypi.org/pypi/xgboost/json][CITED: https://pypi.org/pypi/mlflow/json]
- Architecture: MEDIUM-HIGH - the local repo already exposes the feature persistence, manifest, storage, and config patterns this phase should extend. [CITED: src/tennisprediction/features/persistence.py][CITED: src/tennisprediction/ingestion/manifests.py][CITED: src/tennisprediction/config.py]
- Pitfalls: MEDIUM-HIGH - the highest-risk failure modes are directly grounded in official calibration/model-persistence docs and the current repo’s missing environment prerequisites. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html][CITED: https://scikit-learn.org/stable/model_persistence.html][CITED: local env probe: modeling imports]

**Research date:** 2026-06-18
**Valid until:** 2026-06-25 for package/version recommendations; local codebase findings remain valid until Phase 02 contracts change.
