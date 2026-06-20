# Phase 4: Backtesting and EV Decision Core - Research

**Researched:** 2026-06-19  
**Domain:** Replayable ATP model backtesting, Kalshi-aligned EV decision logic, and profitability-report guardrails [CITED: .planning/ROADMAP.md] [CITED: .planning/REQUIREMENTS.md] [CITED: .planning/PROJECT.md]  
**Confidence:** MEDIUM

## User Constraints

- No `04-CONTEXT.md` exists, so there are no phase-specific locked decisions to copy verbatim; scope is constrained by `AGENTS.md`, `PROJECT.md`, `ROADMAP.md`, `REQUIREMENTS.md`, `STATE.md`, and completed Phase 02/03 artifacts instead. [CITED: AGENTS.md] [CITED: .planning/PROJECT.md] [CITED: .planning/ROADMAP.md] [CITED: .planning/REQUIREMENTS.md] [CITED: .planning/STATE.md]
- Scope remains ATP only. Phase 04 must not introduce WTA, Challenger, ITF, doubles, or venue-generic abstractions. [CITED: AGENTS.md] [CITED: .planning/PROJECT.md]
- Scope remains Kalshi only. Phase 04 can define a reusable decision core, but any market semantics and provenance labels must stay Kalshi-specific. [CITED: AGENTS.md] [CITED: .planning/PROJECT.md]
- Automated trade execution remains out of scope. Phase 04 is evidence and recommendation logic only. [CITED: AGENTS.md] [CITED: .planning/REQUIREMENTS.md]
- Chronological leakage prevention remains locked. Replay must consume persisted Phase 02 feature snapshots and frozen Phase 03 manifests/artifacts only; it must not recompute tennis state or shuffle rows. [CITED: AGENTS.md] [CITED: src/tennisprediction/features/persistence.py] [CITED: src/tennisprediction/modeling/datasets.py] [CITED: src/tennisprediction/modeling/splits.py]
- Profitability claims require provenance, sample size, and backtest evidence. Phase 04 must fail closed on unsupported provenance. [CITED: AGENTS.md] [CITED: .planning/REQUIREMENTS.md]
- Engineering quality remains mandatory: modular, typed, logged, configurable, reproducible code with focused unit tests for critical logic. [CITED: AGENTS.md]

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| BKT-01 | System replays historical predictions using frozen chronological model artifacts and feature snapshots. [CITED: .planning/REQUIREMENTS.md] | Load the Phase 03 artifact bundle by manifest, rematerialize the Phase 03 dataset from persisted Phase 02 `feature_differential_rows`, enforce `feature_version` and `split_manifest_id`, then regenerate predictions through the saved raw estimator plus saved calibrator instead of trusting cached probabilities alone. [CITED: src/tennisprediction/modeling/registry.py] [CITED: src/tennisprediction/modeling/datasets.py] [CITED: src/tennisprediction/modeling/schemas.py] |
| BKT-02 | System implements market probability, edge, expected value, confidence, liquidity, and threshold filtering as reusable decision logic. [CITED: .planning/REQUIREMENTS.md] | Keep decision math in a project-owned backtesting module that consumes normalized positive-side market inputs and model outputs. Do not entangle it with HTTP clients or raw Kalshi payload parsing. [CITED: .planning/ROADMAP.md] [CITED: https://docs.kalshi.com/api-reference/market/get-market] [CITED: https://docs.kalshi.com/getting_started/orderbook_responses] [ASSUMED] |
| BKT-03 | System records accepted and rejected opportunities with reason codes. [CITED: .planning/REQUIREMENTS.md] | Persist two explicit record surfaces, accepted and rejected, with threshold snapshots, selected side, price source, provenance label, and rejection reason codes rather than silently dropping failed candidates. [CITED: .planning/ROADMAP.md] [ASSUMED] |
| BKT-04 | System calculates ROI, profit curve, win rate, average edge, max drawdown, sample size, and backtest provenance. [CITED: .planning/REQUIREMENTS.md] | Persist a run summary plus time-ordered equity-curve data derived from settled replay records; max drawdown should be computed from the cumulative-profit peak-to-trough path, not from unordered aggregates. [CITED: .planning/ROADMAP.md] [ASSUMED] |
| BKT-05 | System labels every market/EV backtest as actual Kalshi historical data, collected snapshot replay, or synthetic/proxy assumptions. [CITED: .planning/REQUIREMENTS.md] | Make provenance a required run-level and row-level field, with a closed enum and report bannering before any profitability numbers are shown. [CITED: .planning/ROADMAP.md] [CITED: https://docs.kalshi.com/getting_started/historical_data] [ASSUMED] |
| BKT-06 | System prevents profitability claims unless sample size, uncertainty, and data provenance are included in the report. [CITED: .planning/REQUIREMENTS.md] | Gate summary generation so ROI/profit claims are rendered only together with sample size, provenance label, and assumption metadata. Synthetic/proxy runs should carry an explicit limitation notice. [CITED: .planning/REQUIREMENTS.md] [ASSUMED] |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Reuse Phase 03’s immutable artifact bundle as the replay authority; do not invent a second model-registry surface. [CITED: AGENTS.md] [CITED: .planning/phases/03-modeling-calibration-and-artifact-registry/03-04-SUMMARY.md] [CITED: src/tennisprediction/modeling/registry.py]
- Reuse Phase 02’s persisted `feature_differential_rows` as the model-input authority; do not rebuild Elo, form, H2H, rankings, or aggregates inside backtesting code. [CITED: AGENTS.md] [CITED: .planning/phases/02-leakage-safe-feature-engine/02-04-SUMMARY.md] [CITED: src/tennisprediction/features/persistence.py]
- Preserve ATP-only and Kalshi-only boundaries in all DTOs, reports, and filenames. [CITED: AGENTS.md]
- Keep market monitoring and recommendation logic read-only. No order-placement, order-staging, or execution-prep interfaces belong in this phase. [CITED: AGENTS.md] [CITED: .planning/PROJECT.md]
- Keep provenance explicit. Phase 04 sits between offline modeling and future Kalshi ingestion/mapping phases, so every decision record must say which artifact, feature version, split, and market-data provenance it used. [CITED: AGENTS.md] [CITED: .planning/STATE.md] [CITED: src/tennisprediction/modeling/schemas.py]
- Extend existing repo patterns: repo-local paths, typed contracts, filesystem-first artifacts, DuckDB-backed source tables, and focused `pytest` coverage. [CITED: AGENTS.md] [CITED: src/tennisprediction/config.py] [CITED: src/tennisprediction/storage/duckdb.py] [CITED: tests/unit/test_modeling_registry.py]

## Summary

Phase 04 should be planned as a three-slice bridge between Phase 03 probability artifacts and later Kalshi data integration. The first slice should prove deterministic replay from frozen Phase 03 artifacts and persisted Phase 02 feature snapshots. The second slice should encapsulate EV decision math, thresholding, and reason-coded accepted/rejected records over normalized market inputs. The third slice should generate profitability reports with hard provenance guardrails, so unsupported ROI claims cannot appear by accident. [CITED: .planning/ROADMAP.md] [CITED: .planning/REQUIREMENTS.md] [CITED: .planning/phases/03-modeling-calibration-and-artifact-registry/03-04-SUMMARY.md]

The most important planning constraint is that Phase 04 does not yet have live or persisted Kalshi snapshots from this repo. Phase 05 introduces the read-only Kalshi client and raw snapshot persistence, and Phase 06 introduces market mapping plus executable pricing. That means Phase 04 can and should define the normalized decision contract now, but the initial replay runs will be limited to synthetic/proxy market inputs or manually prepared historical fixtures unless future phases are pulled forward. Profitability reporting must make that limitation obvious. [CITED: .planning/ROADMAP.md] [CITED: .planning/REQUIREMENTS.md] [CITED: https://docs.kalshi.com/getting_started/historical_data]

Phase 03 already persisted the pieces Phase 04 needs: trusted artifact loading with repo-local path checks, `feature_version` and `split_manifest_id` validation, saved raw estimators and calibrators, and metadata-rich calibrated test predictions. The backtesting harness should treat those artifacts as verifiable inputs, not as optional conveniences. [CITED: .planning/phases/03-modeling-calibration-and-artifact-registry/03-04-SUMMARY.md] [CITED: src/tennisprediction/modeling/registry.py] [CITED: src/tennisprediction/modeling/reports.py]

**Primary recommendation:** Plan Phase 04 in strict dependency order as `replay harness -> decision engine -> reporting and provenance guardrails`, with no Kalshi client work and no execution surfaces in this phase. [CITED: .planning/ROADMAP.md] [CITED: .planning/PROJECT.md]

## Recommended Vertical Slices

| Slice | Requirements | Depends On | Inputs | Outputs | Why First/Next |
|------|--------------|------------|--------|---------|----------------|
| `04-01` Prediction replay and frozen-artifact harness | `BKT-01` [CITED: .planning/REQUIREMENTS.md] | Phase 03 artifacts and Phase 02 feature persistence [CITED: .planning/ROADMAP.md] | `models/runs/<run_id>/manifest.json`, `split_manifest.json`, raw model, calibrator, and DuckDB `feature_differential_rows` / `canonical_matches` [CITED: src/tennisprediction/modeling/registry.py] [CITED: src/tennisprediction/modeling/datasets.py] | Deterministic replay rows with regenerated raw/calibrated probabilities plus artifact/feature provenance [ASSUMED] | All later EV logic depends on trustworthy replay. Do this before any EV math. [CITED: .planning/phases/03-modeling-calibration-and-artifact-registry/03-04-SUMMARY.md] |
| `04-02` EV decision logic, filters, and reason-coded records | `BKT-02`, `BKT-03` [CITED: .planning/REQUIREMENTS.md] | `04-01` replay rows | Side-aligned model probabilities plus normalized market-probability/liquidity inputs [ASSUMED] | Accepted and rejected opportunity records with reason codes and threshold snapshots [ASSUMED] | Decision logic should be developed against replay outputs, not mixed into artifact loading. [CITED: .planning/ROADMAP.md] |
| `04-03` Betting metrics, provenance labels, and profitability-claim guardrails | `BKT-04`, `BKT-05`, `BKT-06` [CITED: .planning/REQUIREMENTS.md] | `04-02` decision records | Accepted/rejected records, realized outcomes, provenance labels, assumption metadata [ASSUMED] | Summary JSON, equity curve, ROI/drawdown metrics, reason counts, and claim-guarded report surfaces [ASSUMED] | Reporting is only meaningful once decision records and provenance exist. [CITED: .planning/ROADMAP.md] |

**Dependency order:** `04-01` must finish first because `04-02` depends on replayed calibrated probabilities and artifact provenance. `04-03` depends on `04-02` because report metrics must be computed from accepted/rejected records, not from raw predictions alone. [CITED: .planning/ROADMAP.md]

## Critical Ambiguities

1. **Liquidity semantics are not yet locked in repo context.** Kalshi market docs expose fields such as `liquidity_dollars`, orderbook bid sizes, open interest, and candlestick volume, but the project does not yet define which one should drive Phase 04’s `min_liquidity` filter. Recommendation: make liquidity a normalized input field plus `liquidity_source` metadata in Phase 04, and defer raw derivation from Kalshi payloads to Phase 06 executable-pricing work. [CITED: https://docs.kalshi.com/api-reference/market/get-market] [CITED: https://docs.kalshi.com/getting_started/orderbook_responses] [CITED: .planning/ROADMAP.md]
2. **Market-probability source precedence is not yet locked.** Kalshi docs expose `yes_bid_dollars`, `yes_ask_dollars`, `no_bid_dollars`, `no_ask_dollars`, `last_price_dollars`, and candlestick price fields, but repo context does not decide which should be canonical for backtests. Recommendation: Phase 04 should require an explicit `market_probability_source` enum and persist it on every record instead of hardcoding a single source now. [CITED: https://docs.kalshi.com/api-reference/market/get-market] [CITED: https://docs.kalshi.com/api-reference/historical/get-historical-market-candlesticks] [CITED: .planning/ROADMAP.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Artifact loading and replay validation | API / Backend | Database / Storage | Backtesting code owns replay orchestration, but artifacts and feature tables are persisted assets. [CITED: src/tennisprediction/modeling/registry.py] [CITED: src/tennisprediction/modeling/datasets.py] |
| Frozen feature snapshot reuse | Database / Storage | API / Backend | Persisted Phase 02 differential rows are the authoritative data source; backend code should read them, not recreate them. [CITED: src/tennisprediction/features/persistence.py] |
| Side-symmetric EV decision logic | API / Backend | — | Thresholding, side selection, and reason coding are pure domain logic and should remain independent from clients or storage formats. [CITED: .planning/ROADMAP.md] [ASSUMED] |
| Accepted/rejected record persistence | Database / Storage | API / Backend | Record outputs are durable artifacts for audit and later analysis, while the backend only materializes them. [CITED: .planning/PROJECT.md] [ASSUMED] |
| Profitability reporting and provenance guardrails | API / Backend | Database / Storage | Report logic belongs in backend code, but outputs should persist under repo-local report paths. [CITED: src/tennisprediction/config.py] [CITED: src/tennisprediction/modeling/reports.py] |

## EV Decision Contract

| Field | Definition |
|------|------------|
| `model_probability_positive` | The replayed calibrated probability of the positive label already defined by Phase 03 as `player_a_id == winner_canonical_player_id`. [CITED: src/tennisprediction/modeling/datasets.py] [CITED: src/tennisprediction/modeling/schemas.py] |
| `model_probability_negative` | `1 - model_probability_positive`, used to evaluate the opposite side without a second model pass. [ASSUMED] |
| `market_probability_positive` | The Kalshi-implied probability for the same positive label, supplied by a normalized replay input and tagged with a `market_probability_source`. [CITED: https://docs.kalshi.com/api-reference/market/get-market] [ASSUMED] |
| `market_probability_negative` | `1 - market_probability_positive`, used for the opposite side. [ASSUMED] |
| `selected_side` | The side with the higher positive expected value after evaluating both positive and negative outcomes against the same model row. [ASSUMED] |
| `confidence` | The model probability of the selected side. Phase 03 already persists `favored_probability`, which is the same concept on replayed prediction rows. [CITED: src/tennisprediction/modeling/schemas.py] [ASSUMED] |
| `edge` | `model_probability_selected - market_probability_selected`; this is the probability-space advantage before fees or slippage. [ASSUMED] |
| `expected_value_per_contract` | For a unit-payout binary contract with zero fees, EV per contract is the same as `edge`; if fees or slippage are modeled, subtract them explicitly and persist the assumption. [ASSUMED] |
| `liquidity` | A normalized numeric field compared to thresholds only. Phase 04 should not derive it from raw Kalshi books yet. [CITED: .planning/ROADMAP.md] [ASSUMED] |
| `threshold_snapshot` | Persist the exact `min_edge`, `min_confidence`, `min_liquidity`, and any fee/slippage assumptions used for the decision so accepted and rejected records remain replayable. [ASSUMED] |

**Decision rules:**  
`selected_side_probability = max(model_probability_positive, model_probability_negative)` for confidence and thresholding. [ASSUMED]  
`selected_market_probability` must be aligned to the same side before computing `edge` or `expected_value_per_contract`. [ASSUMED]  
Accepted rows should require all configured thresholds to pass. Rejected rows should persist one or more explicit reason codes such as `below_min_edge`, `below_min_confidence`, `below_min_liquidity`, `missing_market_probability`, `invalid_probability_bounds`, or `unsupported_provenance`. [ASSUMED]

## Required Record and Report Outputs

### Opportunity Records

| Output | Required Fields | Why |
|--------|-----------------|-----|
| `accepted_opportunities.parquet` | `canonical_match_id`, `artifact_run_id`, `model_name`, `model_family`, `feature_version`, `split_manifest_id`, `source_commit_sha`, `selected_side`, `model_probability`, `market_probability`, `edge`, `expected_value_per_contract`, `confidence`, `liquidity`, `market_probability_source`, `liquidity_source`, `provenance_label`, `threshold_snapshot`, `realized_outcome`, `realized_pnl` [ASSUMED] | This is the auditable set of “would have bet” decisions. It must be row-complete enough to reproduce summaries later without reopening raw clients. [CITED: .planning/REQUIREMENTS.md] [ASSUMED] |
| `rejected_opportunities.parquet` | Same core identity/provenance fields plus `rejection_reason_codes` and optional partially computed decision metrics [ASSUMED] | Requirement `BKT-03` explicitly demands reason-coded rejected opportunities, not just accepted bets. [CITED: .planning/REQUIREMENTS.md] |
| `decision_reason_counts.csv` | `reason_code`, `count` [ASSUMED] | Planners and later operators need to see whether thresholds are too strict, liquidity is missing, or provenance is unsupported. [ASSUMED] |

### Run-Level Reports

| Output | Required Contents | Why |
|--------|-------------------|-----|
| `summary.json` | `sample_size`, `accepted_count`, `rejected_count`, `win_rate`, `average_edge`, `roi`, `gross_profit`, `net_profit`, `max_drawdown`, `provenance_label`, `assumption_notes`, `artifact_run_id`, `feature_version`, `split_manifest_id` [ASSUMED] | The phase goal is evidence, not just row dumps. Summary metrics must carry provenance. [CITED: .planning/ROADMAP.md] [CITED: .planning/REQUIREMENTS.md] |
| `equity_curve.csv` | time-ordered cumulative profit/equity rows with at least `as_of_date`, `canonical_match_id`, `cumulative_profit`, `cumulative_roi`, `peak_profit`, `drawdown` [ASSUMED] | `BKT-04` explicitly requires a profit curve and max drawdown, which both require path data, not just aggregates. [CITED: .planning/REQUIREMENTS.md] |
| `provenance.json` | run-level label `actual_kalshi_historical`, `collected_snapshot_replay`, or `synthetic_proxy`, plus any fee/slippage/price-source assumptions [CITED: .planning/REQUIREMENTS.md] [ASSUMED] | `BKT-05` and `BKT-06` require visible provenance before profitability claims. [CITED: .planning/REQUIREMENTS.md] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `duckdb` | `1.5.3` installed in `.venv`. [VERIFIED: local env] [CITED: pyproject.toml] | Reload persisted Phase 02 feature rows and canonical match outcomes for replay | The repo already stores canonical and feature tables in DuckDB and Phase 03 dataset materialization is DuckDB-backed. [CITED: src/tennisprediction/storage/duckdb.py] [CITED: src/tennisprediction/modeling/datasets.py] |
| `joblib` | `1.5.3` installed in `.venv`. [VERIFIED: local env] [CITED: pyproject.toml] | Load saved calibrators and non-XGBoost estimators | Phase 03 artifact bundles already persist calibrators and sklearn-compatible estimators with joblib. [CITED: src/tennisprediction/modeling/registry.py] |
| `scikit-learn` | `1.9.0` installed in `.venv`. [VERIFIED: local env] [CITED: pyproject.toml] | Shared estimator and calibration interfaces during replay | Official docs say fitted models can be calibrated via `FrozenEstimator`, and the same environment must be available when loading pickle/joblib-style artifacts. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html] [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| `pandas` | `3.0.3` installed in `.venv`. [VERIFIED: local env] [CITED: pyproject.toml] | Build report frames and write tabular outputs | Phase 03 report writers already use pandas to persist CSV and Parquet outputs. [CITED: src/tennisprediction/modeling/reports.py] |
| `pyarrow` | `24.0.0` installed in `.venv`. [VERIFIED: local env] [CITED: pyproject.toml] | Parquet interchange for accepted/rejected records and replay outputs | The project stack already treats Parquet as the durable intermediate/report format. [CITED: AGENTS.md] [CITED: src/tennisprediction/modeling/reports.py] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `xgboost` | `3.2.0` installed in `.venv`. [VERIFIED: local env] [CITED: pyproject.toml] | Replay Phase 03 XGBoost artifacts when the selected run family is `xgboost` | Phase 03 persists `raw_model.ubj` plus a preprocessing sidecar specifically so XGBoost replay can use the same bundle contract as other families. [CITED: .planning/phases/03-modeling-calibration-and-artifact-registry/03-04-SUMMARY.md] [CITED: src/tennisprediction/modeling/registry.py] |
| Python `decimal` stdlib | Python `3.12.4` runtime in `.venv`. [VERIFIED: local env] | Stable money/probability arithmetic for EV and ROI reporting | Kalshi market/orderbook docs express prices as dollar strings and reciprocal YES/NO relationships, so decimal-safe parsing is preferable at the decision boundary. [CITED: https://docs.kalshi.com/getting_started/orderbook_responses] [ASSUMED] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Replaying through the saved raw estimator + calibrator | Reading Phase 03 `test_predictions.parquet` as the sole backtest source | Saved predictions are useful as an audit artifact, but they do not prove the artifact bundle can still be loaded and run correctly in the current environment. Phase 04 needs the stronger replay guarantee. [CITED: src/tennisprediction/modeling/reports.py] [CITED: src/tennisprediction/modeling/registry.py] |
| Normalized decision inputs with explicit source fields | Directly passing raw Kalshi payloads into the EV engine | Kalshi integration, pagination, and payload normalization are Phase 05 concerns; mixing them into Phase 04 would create the wrong dependency order. [CITED: .planning/ROADMAP.md] |
| Side-symmetric decision evaluation | Only evaluating the positive class / YES-equivalent side | Binary markets expose both sides, and the better EV can sit on the complement. Restricting to one side would distort both accepted and rejected records. [CITED: https://docs.kalshi.com/getting_started/orderbook_responses] [ASSUMED] |

**Installation:** No new external packages are required for Phase 04. Reuse the existing project environment created for Phase 03. [VERIFIED: local env] [CITED: pyproject.toml]

```bash
python3 -m uv sync --group dev --group ml
```

**Version verification:** Verified in the project `.venv` rather than the host `python3`, because the host interpreter is Python `3.14.0` and does not carry the project stack. [VERIFIED: local env]

```bash
./.venv/bin/python --version
./.venv/bin/python - <<'PY'
import duckdb, pandas, sklearn, joblib, pyarrow, xgboost
print(duckdb.__version__, pandas.__version__, sklearn.__version__)
print(joblib.__version__, pyarrow.__version__, xgboost.__version__)
PY
```

## Package Legitimacy Audit

No new external packages are recommended for this phase. Reuse the already installed Phase 03 stack instead, so a new package-legitimacy gate is not required here. [VERIFIED: local env] [CITED: pyproject.toml]

## Architecture Patterns

### System Architecture Diagram

```text
DuckDB persisted feature tables
  feature_differential_rows
  canonical_matches
          |
          v
Phase 03 artifact bundle
  manifest.json
  split_manifest.json
  feature_columns.json
  raw model + calibrator
          |
          v
Replay harness
  - validate repo-local artifact path
  - validate feature_version + split_manifest_id
  - rematerialize ordered dataset rows
  - regenerate raw + calibrated probabilities
          |
          v
Decision engine
  - align market side to positive label
  - compute both sides
  - apply thresholds
  - emit accepted/rejected rows
          |
          v
Backtest metrics
  - realized PnL
  - ROI
  - equity curve
  - max drawdown
  - average edge / win rate / sample size
          |
          v
Report guardrail
  - require provenance label
  - attach assumptions
  - suppress unsupported profitability claims
```

### Recommended Project Structure

```text
src/tennisprediction/backtesting/
├── __init__.py          # public exports
├── schemas.py           # replay rows, market inputs, decision records, report summaries
├── replay.py            # artifact loading, dataset rematerialization, probability regeneration
├── decisions.py         # side alignment, edge/EV math, thresholds, reason codes
├── metrics.py           # realized pnl, roi, equity curve, drawdown, summary metrics
├── reports.py           # parquet/csv/json output writers and provenance banners
└── provenance.py        # provenance-label enums and claim guardrails

tests/unit/
├── test_backtesting_replay.py
├── test_backtesting_decisions.py
├── test_backtesting_metrics.py
└── test_backtesting_reports.py
```

### Pattern 1: Replay from the Artifact Manifest, Not from Memory
**What:** Load the saved artifact bundle, validate it, then regenerate probabilities on rematerialized frozen rows. [CITED: src/tennisprediction/modeling/registry.py] [CITED: src/tennisprediction/modeling/datasets.py]  
**When to use:** For every Phase 04 replay run and every later shadow-mode or live scoring path that claims to reuse a Phase 03 artifact. [CITED: .planning/ROADMAP.md]  
**Example:**

```python
# Source: official scikit-learn docs + current repo artifact surface
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

# artifact_bundle.raw_estimator comes from the Phase 03 manifest
calibrator = CalibratedClassifierCV(
    estimator=FrozenEstimator(artifact_bundle.raw_estimator),
    method="sigmoid",
)
calibrator.fit(X_validation, y_validation)
```

Source: `CalibratedClassifierCV` with `FrozenEstimator` for already fitted models. [CITED: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html]

### Pattern 2: Keep EV Logic Side-Symmetric and Source-Labeled
**What:** Evaluate both the positive and negative side from one replayed probability row, then persist the chosen side plus the exact market-data source used. [CITED: https://docs.kalshi.com/getting_started/orderbook_responses] [ASSUMED]  
**When to use:** For every accepted or rejected opportunity record. [ASSUMED]  
**Example:**

```python
# Source: project-specific first-principles decision contract
positive = model_probability_positive - market_probability_positive
negative = (1.0 - model_probability_positive) - (1.0 - market_probability_positive)

if positive >= negative:
    selected_side = "positive"
    edge = positive
else:
    selected_side = "negative"
    edge = negative
```

Source: binary contract complement arithmetic over the project label definition. [ASSUMED]

### Anti-Patterns to Avoid

- **Recomputing tennis features during replay:** Backtesting must read persisted Phase 02 rows, not reopen feature state logic. [CITED: src/tennisprediction/features/persistence.py]
- **Treating `test_predictions.parquet` as the replay engine:** It is an audit artifact, not a substitute for artifact loading and scoring. [CITED: src/tennisprediction/modeling/reports.py] [CITED: src/tennisprediction/modeling/registry.py]
- **Baking raw Kalshi payload parsing into EV logic:** Phase 05 owns client/payload normalization; Phase 04 should consume normalized inputs only. [CITED: .planning/ROADMAP.md]
- **Publishing unlabeled profitability claims:** Synthetic/proxy runs must remain explicitly labeled synthetic/proxy in every summary surface. [CITED: .planning/REQUIREMENTS.md] [ASSUMED]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Artifact trust | Ad hoc path concatenation and blind `joblib.load` calls | Reuse Phase 03 manifest validation and repo-local path guards from `load_model_artifact_bundle()` [CITED: src/tennisprediction/modeling/registry.py] | Scikit-learn persistence docs warn that joblib/pickle-style loads can execute arbitrary code from untrusted sources. [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| Replay dataset assembly | A second feature-building pipeline inside backtesting | Reuse `materialize_modeling_dataset()` over persisted Phase 02 rows [CITED: src/tennisprediction/modeling/datasets.py] | Recomputing tennis state in Phase 04 would reintroduce leakage and divergence risk. [CITED: src/tennisprediction/features/persistence.py] |
| Kalshi microstructure interpretation inside the decision engine | Hidden conversions from mixed price fields | Require normalized `market_probability_source`, `market_probability`, and `liquidity` inputs [CITED: https://docs.kalshi.com/api-reference/market/get-market] [ASSUMED] | Phase 04 should remain testable without a network client or raw payload parsing. [CITED: .planning/ROADMAP.md] |

**Key insight:** Hand-rolled code is appropriate only for the project-specific seams libraries do not own: artifact-to-feature replay, side-aligned EV semantics, provenance labeling, and profitability-claim guardrails. Generic persistence and estimator interfaces already exist and should be reused. [CITED: src/tennisprediction/modeling/registry.py] [CITED: https://scikit-learn.org/stable/model_persistence.html] [ASSUMED]

## Common Pitfalls

### Pitfall 1: Cached-Probability “Replay”
**What goes wrong:** The phase appears to backtest successfully, but it only reads saved test predictions rather than proving the artifact bundle still loads and scores correctly. [CITED: src/tennisprediction/modeling/reports.py]  
**Why it happens:** `test_predictions.parquet` is convenient and already exists. [CITED: src/tennisprediction/modeling/reports.py]  
**How to avoid:** Recompute probabilities through the saved estimator and calibrator, then optionally compare them against the saved prediction artifact as a parity check. [CITED: src/tennisprediction/modeling/registry.py] [ASSUMED]  
**Warning signs:** The replay code never calls artifact loading or never rebuilds an input frame from `feature_columns`. [CITED: src/tennisprediction/modeling/registry.py] [CITED: src/tennisprediction/modeling/schemas.py]

### Pitfall 2: Side-Orientation Drift
**What goes wrong:** The model probability for `player_a_win` gets compared against a Kalshi price representing the opposite side, producing inverted edge and EV values. [CITED: src/tennisprediction/modeling/datasets.py] [CITED: https://docs.kalshi.com/getting_started/orderbook_responses]  
**Why it happens:** Phase 03 labels are player-A-oriented, while Kalshi exposes yes/no market sides. [CITED: src/tennisprediction/modeling/datasets.py] [CITED: https://docs.kalshi.com/api-reference/market/get-market]  
**How to avoid:** Make side alignment an explicit normalization step and persist the selected side on every accepted and rejected record. [ASSUMED]  
**Warning signs:** Edge is computed directly from `calibrated_probability` and a raw `yes_*` price without any side-mapping field. [ASSUMED]

### Pitfall 3: Provenance Laundering
**What goes wrong:** Synthetic/proxy price runs are reported with the same tone and surface as actual Kalshi-history runs. [CITED: .planning/REQUIREMENTS.md]  
**Why it happens:** Phase 04 arrives before the repo’s Kalshi snapshot collection and mapping phases, so placeholder market data is tempting. [CITED: .planning/ROADMAP.md]  
**How to avoid:** Require `provenance_label` at run creation, persist it at row level, and banner it in every summary output before metrics. [CITED: .planning/REQUIREMENTS.md] [ASSUMED]  
**Warning signs:** Summary outputs contain ROI/profit figures but no provenance field, no assumption notes, or no sample-size field. [CITED: .planning/REQUIREMENTS.md] [ASSUMED]

## Code Examples

Verified patterns from official sources and current repo contracts:

### Calibrating an Already Fitted Model
```python
# Source: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html
from sklearn.calibration import CalibratedClassifierCV
from sklearn.frozen import FrozenEstimator

calibrator = CalibratedClassifierCV(
    estimator=FrozenEstimator(raw_model),
    method="sigmoid",
)
calibrator.fit(X_validation, y_validation)
```

### Loading a Trusted Artifact Bundle by Expected Provenance
```python
# Source: src/tennisprediction/modeling/registry.py
artifact_bundle = load_model_artifact_bundle(
    artifact_path,
    expected_feature_version=feature_version,
    expected_split_manifest_id=split_manifest_id,
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Recompute features or rebuild holdouts at evaluation time | Replay frozen Phase 02/03 assets with explicit `feature_version` and `split_manifest_id` validation [CITED: src/tennisprediction/modeling/registry.py] [CITED: src/tennisprediction/modeling/datasets.py] | This repo locked the replayable artifact pattern in Phase 03 on 2026-06-19. [CITED: .planning/phases/03-modeling-calibration-and-artifact-registry/03-04-SUMMARY.md] | Makes EV evidence reproducible instead of approximate. [ASSUMED] |
| Treat market data as a single live surface | Route between live and historical tiers using Kalshi cutoff timestamps and provenance labeling [CITED: https://docs.kalshi.com/getting_started/historical_data] [CITED: https://docs.kalshi.com/api-reference/historical/get-historical-cutoff-timestamps] | Kalshi docs currently describe a live/historical partition with explicit cutoff endpoints. [CITED: https://docs.kalshi.com/getting_started/historical_data] | Forces Phase 04/05 planners to model provenance explicitly. [ASSUMED] |
| Blind model-file deserialization | Trusted manifest-first loading with dependency and path validation [CITED: src/tennisprediction/modeling/registry.py] [CITED: https://scikit-learn.org/stable/model_persistence.html] | This repo established trusted loading in Phase 03 on 2026-06-19. [CITED: .planning/phases/03-modeling-calibration-and-artifact-registry/03-04-SUMMARY.md] | Lowers replay risk and prevents artifact/provenance drift. [ASSUMED] |

**Deprecated/outdated:**

- Reading profitability from unlabeled cached predictions alone is outdated for this repo; Phase 04 should require regenerated predictions plus provenance-aware decision records. [CITED: src/tennisprediction/modeling/reports.py] [CITED: .planning/REQUIREMENTS.md] [ASSUMED]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `model_probability_negative` and `market_probability_negative` should be computed as simple complements of the positive side. | `## EV Decision Contract` | Side-selection logic could be wrong for any non-binary or fee-adjusted interpretation. |
| A2 | `expected_value_per_contract = edge` for zero-fee unit-payout binary contracts, with fees/slippage handled as explicit adjustments. | `## EV Decision Contract` | EV ranking could be inconsistent with later executable-pricing semantics. |
| A3 | Phase 04 should evaluate both sides and choose the better EV side before thresholding. | `## EV Decision Contract`, `## Architecture Patterns` | The implementation could overfit to YES-only semantics and understate real opportunities. |
| A4 | Accepted/rejected records should persist as Parquet plus CSV/JSON summaries under a new backtesting report surface. | `## Required Record and Report Outputs` | Planner could choose a different storage surface and need to remap reporting tasks. |

## Open Questions

1. **What exact field should drive `min_liquidity` before Phase 06?**
   - Resolution: Phase 04 uses normalized `available_liquidity_dollars` and records `liquidity_source` separately. Raw orderbook-derived liquidity stays deferred to Phase 06. [CITED: .planning/ROADMAP.md] [ASSUMED]

2. **Should Phase 04 replay only the test window or support arbitrary manifest windows?**
   - Resolution: Test-window replay is the default and only profitability-claimable mode. Validation replay remains available as a clearly labeled diagnostic mode, but it does not produce profitability claims. [CITED: src/tennisprediction/modeling/schemas.py] [CITED: src/tennisprediction/modeling/reports.py] [ASSUMED]

3. **Which market-price source should be canonical once real Kalshi data exists?**
   - Resolution: Phase 04 makes `market_probability_source` explicit on every record and uses it to record the normalized pricing basis. MVP fixtures use `normalized_positive_side`; raw Kalshi field precedence is deferred to Phase 06 executable-pricing work. [CITED: .planning/ROADMAP.md] [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python project runtime (`.venv`) | Replay code, tests, report writers | ✓ [VERIFIED: local env] | `3.12.4` [VERIFIED: local env] | — |
| `uv` | Environment sync and scripted runs | ✓ [VERIFIED: local env] | `0.11.21` [VERIFIED: local env] | — |
| `duckdb` | Feature/dataset reload | ✓ [VERIFIED: local env] | `1.5.3` [VERIFIED: local env] | — |
| `pandas` | Report persistence | ✓ [VERIFIED: local env] | `3.0.3` [VERIFIED: local env] | — |
| `scikit-learn` | Artifact replay interfaces | ✓ [VERIFIED: local env] | `1.9.0` [VERIFIED: local env] | — |
| `joblib` | Artifact load/save compatibility | ✓ [VERIFIED: local env] | `1.5.3` [VERIFIED: local env] | — |
| `pyarrow` | Parquet outputs | ✓ [VERIFIED: local env] | `24.0.0` [VERIFIED: local env] | — |
| `xgboost` | XGBoost artifact replay | ✓ [VERIFIED: local env] | `3.2.0` [VERIFIED: local env] | Skip XGBoost-family replay if future environments lose this dependency. [ASSUMED] |
| Kalshi API access | Real historical or snapshot-backed provenance modes | Not required for Phase 04 core [CITED: .planning/ROADMAP.md] | — | Use synthetic/proxy or manually prepared replay fixtures until Phase 05/06 data surfaces exist. [CITED: .planning/ROADMAP.md] |

**Missing dependencies with no fallback:** none. [VERIFIED: local env]

**Missing dependencies with fallback:**

- Real Kalshi snapshot data is not available from this repo in Phase 04. Fallback is synthetic/proxy or manually prepared historical fixtures with explicit provenance labels. [CITED: .planning/ROADMAP.md] [ASSUMED]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.1.0` [VERIFIED: local env] |
| Config file | `pyproject.toml` [CITED: pyproject.toml] |
| Quick run command | `./.venv/bin/python -m pytest -q tests/unit/test_modeling_registry.py tests/unit/test_modeling_metrics.py -x` [VERIFIED: local env] |
| Full suite command | `./.venv/bin/python -m pytest -q` [VERIFIED: local env] |

**Current baseline:** The existing test suite passes (`56 passed`), and targeted modeling replay/report tests also pass (`13 passed` and `3 passed`) in the project environment. [VERIFIED: local env]

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| BKT-01 | Replay artifact bundle against persisted feature rows and regenerate calibrated probabilities | unit/integration | `./.venv/bin/python -m pytest -q tests/unit/test_backtesting_replay.py -x` | ❌ Wave 0 |
| BKT-02 | Evaluate side-aligned market probability, edge, EV, confidence, liquidity, and thresholds | unit | `./.venv/bin/python -m pytest -q tests/unit/test_backtesting_decisions.py -x` | ❌ Wave 0 |
| BKT-03 | Persist accepted and rejected opportunities with reason codes | unit | `./.venv/bin/python -m pytest -q tests/unit/test_backtesting_decisions.py -x` | ❌ Wave 0 |
| BKT-04 | Compute ROI, profit curve, win rate, average edge, max drawdown, and sample size | unit | `./.venv/bin/python -m pytest -q tests/unit/test_backtesting_metrics.py -x` | ❌ Wave 0 |
| BKT-05 | Enforce provenance labels on every backtest/report run | unit | `./.venv/bin/python -m pytest -q tests/unit/test_backtesting_reports.py -x` | ❌ Wave 0 |
| BKT-06 | Suppress unsupported profitability claims unless sample size and provenance are present | unit | `./.venv/bin/python -m pytest -q tests/unit/test_backtesting_reports.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `./.venv/bin/python -m pytest -q tests/unit/test_backtesting_replay.py tests/unit/test_backtesting_decisions.py -x` once those files exist. [ASSUMED]
- **Per wave merge:** `./.venv/bin/python -m pytest -q` [VERIFIED: local env]
- **Phase gate:** Full suite green before `$gsd-verify-work`. [CITED: .planning/config.json]

### Wave 0 Gaps

- [ ] `tests/unit/test_backtesting_replay.py` — covers `BKT-01`
- [ ] `tests/unit/test_backtesting_decisions.py` — covers `BKT-02` and `BKT-03`
- [ ] `tests/unit/test_backtesting_metrics.py` — covers `BKT-04`
- [ ] `tests/unit/test_backtesting_reports.py` — covers `BKT-05` and `BKT-06`

**Existing non-phase quality drift:** `ruff check .` currently fails on import ordering in [runner.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/runner.py:1), and `mypy src` currently fails on missing annotations in [ids.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/ids.py:26). These are pre-existing and outside Phase 04 scope, but planners should avoid assuming repo-wide lint/type gates are fully green today. [VERIFIED: local env]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 04 is offline replay logic and should not add any auth surfaces. [CITED: .planning/ROADMAP.md] |
| V3 Session Management | no | No session surfaces belong in backtesting/report generation. [CITED: .planning/ROADMAP.md] |
| V4 Access Control | no | Repo-local artifact path guards are needed, but this phase does not add user-role access control. [CITED: src/tennisprediction/modeling/registry.py] |
| V5 Input Validation | yes | Validate repo-local paths, manifest expectations, probability bounds, threshold config, provenance labels, and side alignment in typed contracts. [CITED: src/tennisprediction/config.py] [CITED: src/tennisprediction/modeling/registry.py] [ASSUMED] |
| V6 Cryptography | no | No new cryptographic surfaces are required in this offline phase. [CITED: .planning/ROADMAP.md] |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Untrusted artifact deserialization | Elevation of Privilege | Reuse manifest validation, repo-local path checks, and dependency-version checks before any `joblib.load`. [CITED: src/tennisprediction/modeling/registry.py] [CITED: https://scikit-learn.org/stable/model_persistence.html] |
| Provenance spoofing in profitability reports | Repudiation | Require a closed provenance enum plus run-level and row-level persistence of the label and assumption notes. [CITED: .planning/REQUIREMENTS.md] [ASSUMED] |
| Side-orientation bugs between model labels and market sides | Tampering | Normalize market inputs to the Phase 03 positive label before EV computation, and cover both sides in tests. [CITED: src/tennisprediction/modeling/datasets.py] [CITED: https://docs.kalshi.com/getting_started/orderbook_responses] [ASSUMED] |
| Execution-surface creep | Elevation of Privilege | Keep this phase read-only and do not introduce any order placement, draft order, or execution-prep interfaces. [CITED: .planning/PROJECT.md] |

## Sources

### Primary (HIGH confidence)

- [AGENTS.md](/Users/andrewlay/tennisprediction/AGENTS.md) - project constraints, ATP/Kalshi scope, no automated execution
- [.planning/PROJECT.md](/Users/andrewlay/tennisprediction/.planning/PROJECT.md) - core value and constraints
- [.planning/ROADMAP.md](/Users/andrewlay/tennisprediction/.planning/ROADMAP.md) - Phase 04 goal, success criteria, and dependency order
- [.planning/REQUIREMENTS.md](/Users/andrewlay/tennisprediction/.planning/REQUIREMENTS.md) - `BKT-01` through `BKT-06`
- [.planning/STATE.md](/Users/andrewlay/tennisprediction/.planning/STATE.md) - current milestone and prior phase decisions
- [.planning/phases/03-modeling-calibration-and-artifact-registry/03-04-SUMMARY.md](/Users/andrewlay/tennisprediction/.planning/phases/03-modeling-calibration-and-artifact-registry/03-04-SUMMARY.md) - trusted artifact loading and Phase 04 readiness
- [src/tennisprediction/modeling/registry.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/registry.py) - immutable artifact bundles and trusted load guards
- [src/tennisprediction/modeling/datasets.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/datasets.py) - Phase 03 dataset rematerialization contract
- [src/tennisprediction/modeling/schemas.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/schemas.py) - replayed prediction and artifact manifest fields
- [src/tennisprediction/features/persistence.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/persistence.py) - persisted feature input contract
- https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html - calibration of already fitted models via `FrozenEstimator`
- https://scikit-learn.org/stable/model_persistence.html - persistence constraints and untrusted-load risk
- https://docs.kalshi.com/getting_started/historical_data - live/historical data partition and historical endpoints
- https://docs.kalshi.com/getting_started/orderbook_responses - YES/NO reciprocal orderbook semantics
- https://docs.kalshi.com/api-reference/market/get-market - market fields for prices, volume, liquidity, and rules
- https://docs.kalshi.com/api-reference/historical/get-historical-market-candlesticks - historical candlestick fields and intervals
- https://docs.kalshi.com/api-reference/historical/get-historical-cutoff-timestamps - cutoff semantics for historical routing

### Secondary (MEDIUM confidence)

- Local environment probes on 2026-06-19: `.venv` Python `3.12.4`, `uv 0.11.21`, `duckdb 1.5.3`, `pandas 3.0.3`, `scikit-learn 1.9.0`, `joblib 1.5.3`, `pyarrow 24.0.0`, `xgboost 3.2.0`, `pytest 9.1.0`, and successful targeted/full test runs. [VERIFIED: local env]

### Tertiary (LOW confidence)

- Binary-contract EV formulas, side-selection strategy, and report-file layout recommendations that are derived from repo context and first principles rather than a single authoritative external spec. These are marked `[ASSUMED]` above.

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - the phase reuses installed, verified Phase 03 dependencies and existing repo contracts. [VERIFIED: local env] [CITED: pyproject.toml]
- Architecture: MEDIUM-HIGH - the replay/artifact side is strongly grounded in completed Phase 03 code, but price-source and liquidity semantics remain intentionally unresolved until later Kalshi phases. [CITED: src/tennisprediction/modeling/registry.py] [CITED: .planning/ROADMAP.md]
- Pitfalls: MEDIUM - the highest-risk failure modes are clear from the current code and official docs, but some EV/report semantics are still project-specific and marked `[ASSUMED]`. [CITED: https://scikit-learn.org/stable/model_persistence.html] [CITED: https://docs.kalshi.com/getting_started/orderbook_responses]

**Research date:** 2026-06-19  
**Valid until:** 2026-07-03
