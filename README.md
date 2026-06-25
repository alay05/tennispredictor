# ATP Tennis Prediction and Kalshi EV Detection System

This repository contains an ATP-only, Kalshi-only prediction workflow for:

- ingesting pinned Jeff Sackmann `tennis_atp` snapshots
- normalizing them into canonical DuckDB tables
- building leakage-safe pre-match features
- training calibrated match-win models
- replaying model predictions for evaluation and backtesting
- collecting read-only Kalshi market snapshots
- mapping Kalshi tennis markets onto canonical ATP matches
- ranking positive expected value opportunities with persisted evidence

The current codebase is not a sketch or scaffold. The v1.0 milestone is complete, the roadmap is archived, and the repository already ships a working one-shot CLI, typed persistence layers, model artifact bundles, live monitoring reports, and a broad unit test suite.

## Status

- Scope: ATP only
- Market integration: Kalshi only
- Live behavior: read-only monitoring only, no order placement
- Milestone state: `v1.0` shipped and archived on `2026-06-25`
- Planning audit: `.planning/v1.0-MILESTONE-AUDIT.md` passed with `48/48` requirements satisfied

## What Is Implemented

The repository currently includes:

- historical ingestion and validation for Jeff Sackmann ATP data
- canonical player, tournament, match, ranking, and match-stat normalization
- leakage-safe feature state with chronological cohort ordering
- ranking, Elo, recent-form, head-to-head, and match-stat features
- persisted feature audit tables for pre/post state inspection
- modeling dataset materialization from persisted feature rows
- logistic regression and random forest baselines
- XGBoost candidate training
- probability calibration and calibration diagnostics
- model artifact bundle writing and loading with checksum validation
- replay-based artifact evaluation
- synthetic proxy backtesting over replayed predictions
- Kalshi REST client with RSA-PSS request signing
- market snapshot and orderbook snapshot persistence
- ATP-specific Kalshi market mapping and alias override support
- executable entry-price derivation from latest orderbook state
- EV decision logic and monitoring report generation
- shared audit logging for operator workflows

## Repository Layout

```text
src/tennisprediction/
  cli.py                 Typer CLI entrypoint
  operations.py          End-to-end command orchestration
  config.py              Repo-local settings and env parsing
  logging.py             Structured/audit logging
  domain/                Canonical IDs, models, normalization
  ingestion/             Sackmann fetch, manifests, validation, quarantine
  features/              Leakage-safe state, snapshots, differential rows
  modeling/              Datasets, splits, baselines, XGBoost, calibration
  backtesting/           Replay, decisions, metrics, report writers
  kalshi/                Read-only API client, snapshot jobs, storage
  market_mapping/        Kalshi tennis title normalization and matching
  ev/                    Pricing and opportunity scoring
  monitoring/            Live scan orchestration and operator reports
  storage/               DuckDB persistence helpers

tests/unit/              37 unit-test modules covering 94 test cases
docs/operations.md       Operator runbook for the shipped CLI workflow
.planning/               Archived planning, phase summaries, milestone audit
reports/                 Runtime outputs and audit logs
```

## Core Workflow

The intended workflow is a one-shot CLI pipeline:

1. Ingest a pinned Jeff Sackmann snapshot into DuckDB.
2. Build chronological pre-match feature rows.
3. Train a model artifact bundle for a specific split definition.
4. Replay the artifact for evaluation.
5. Run a synthetic-proxy backtest over replayed predictions.
6. Collect or reuse Kalshi snapshots.
7. Score matched Kalshi markets for live EV and persist an operator report.

The CLI deliberately does not expose daemon mode, polling loops, or auto-trading flags. Tests explicitly assert that options like `--watch`, `--poll-interval`, and `--daemon` are not part of the shipped interface.

## Data and Artifact Flow

### 1. Historical ingestion

`ingest-snapshot` loads a Jeff Sackmann snapshot pinned by commit SHA, validates it, normalizes it, and persists canonical tables to DuckDB.

Persisted canonical tables:

- `canonical_players`
- `canonical_tournaments`
- `canonical_matches`
- `canonical_rankings`
- `canonical_match_stats`

Each row carries source lineage fields so downstream features and reports remain traceable back to the original source file and row number.

### 2. Feature building

`build-features` reads canonical tables from DuckDB and constructs pre-match snapshots in strict chronological order. Features are built before a cohort is applied to state, which is how the repository guards against leakage.

Persisted feature tables:

- `feature_player_snapshots`
- `feature_differential_rows`
- `feature_state_audit`

Feature families currently present in code:

- prior ranking and ranking points
- ranking change and ranking age
- overall Elo and surface Elo
- rest days
- form windows for last 5, 10, and 20 matches
- serve and return rate features from match stats
- ace rate
- head-to-head counts and win rate
- A-vs-B differential features for model training

### 3. Modeling

`train-artifact-bundle` materializes a modeling dataset from `feature_differential_rows`, freezes chronological train/validation/test boundaries, fits a selected model family, calibrates probabilities, computes diagnostics, and writes a versioned artifact bundle.

Supported model families:

- `logistic_regression`
- `random_forest`
- `xgboost`

Supported calibration methods:

- `sigmoid`
- `isotonic`

Artifact bundles are written under `models/runs/<run_id>/` and include:

- `manifest.json`
- `feature_columns.json`
- `split_manifest.json`
- `raw_model.joblib` or `raw_model.ubj`
- `preprocessor.joblib` for XGBoost bundles
- `calibrator.joblib`

The manifest records:

- source commit SHA
- feature version
- split manifest ID
- model family and params
- dependency versions
- report file paths
- artifact checksums

### 4. Evaluation

`evaluate-artifact` replays a trained artifact against persisted feature data and writes `reports/modeling/<run_id>/evaluation.json`.

Modeling reports also include:

- `metrics.json`
- `calibration_curve.csv`
- `calibration_bins.csv`
- `segment_diagnostics.csv`
- `test_predictions.parquet`

### 5. Backtesting

`run-backtest` replays predictions through the EV engine using a synthetic even-money proxy market assumption. This is an important limitation: the current backtest is evidence-bearing, but it is not a historical Kalshi orderbook replay.

Backtest outputs are written under `reports/backtesting/<run_id>/`:

- `summary.json`
- `uncertainty.json`
- `provenance.json`
- `accepted_opportunities.parquet`
- `rejected_opportunities.parquet`
- `decision_reason_counts.csv`
- `equity_curve.csv`

### 6. Kalshi monitoring

`collect-kalshi-snapshots` uses the read-only Kalshi client to persist market and orderbook snapshots. `scan-kalshi-ev` can either reuse existing snapshots or collect fresh ones before scoring.

The live scan flow:

1. Resolve ATP-specific market mappings from the latest Kalshi market rows.
2. Reject excluded, ambiguous, or manual-review-required mappings.
3. Load the latest orderbook snapshot per matched ticker.
4. Replay model predictions for matched canonical match IDs.
5. Derive executable entry prices and liquidity from the orderbook.
6. Score both sides and keep the better accepted or rejected decision record.
7. Persist operator-facing reports.

Monitoring reports are written under `reports/monitoring/<run_id>/`:

- `summary.json`
- `accepted_opportunities.parquet`
- `rejected_opportunities.parquet`
- `ranked_opportunities.csv`
- `operator_report.txt`

## Installation

This project is pinned to Python `3.12` and uses `uv`.

```bash
uv sync --locked --dev --group ml
```

Optional local quality gate:

```bash
pre-commit install --install-hooks
pre-commit run --all-files
```

The package exposes a console script named `tennisprediction`.

## Configuration

Runtime settings are loaded from environment variables with the `TENNISPREDICTION_` prefix.

Example:

```bash
cp .env.example .env
```

Current `.env.example` values:

```dotenv
TENNISPREDICTION_ENVIRONMENT=dev
TENNISPREDICTION_LOG_LEVEL=INFO
TENNISPREDICTION_DATA_DIR=data
TENNISPREDICTION_MODELS_DIR=models
TENNISPREDICTION_REPORTS_DIR=reports
TENNISPREDICTION_DUCKDB_PATH=data/duckdb/tennisprediction.duckdb
```

Important config behavior:

- repository paths are forced to stay inside the repo root
- alert channels are constrained to `terminal` and `file`
- the default feature version is `02-04`
- the default model family is `logistic_regression`
- the default calibration method is `sigmoid`
- default monitoring thresholds are edge `0.05`, confidence `0.35`, liquidity `5.0`

## CLI Reference

Basic commands:

```bash
tennisprediction version
tennisprediction health
```

Pipeline commands:

```bash
tennisprediction ingest-snapshot --source-commit-sha <sha>
tennisprediction build-features --feature-version 02-04
tennisprediction train-artifact-bundle \
  --run-id run-001 \
  --feature-version 02-04 \
  --train-end-date 2023-12-31 \
  --validation-end-date 2024-06-30 \
  --test-end-date 2024-12-31

tennisprediction evaluate-artifact \
  --artifact-dir models/runs/run-001 \
  --expected-feature-version 02-04 \
  --expected-split-manifest-id <split_id>

tennisprediction run-backtest \
  --artifact-dir models/runs/run-001 \
  --expected-feature-version 02-04 \
  --expected-split-manifest-id <split_id> \
  --run-id backtest-001

tennisprediction collect-kalshi-snapshots \
  --access-key <kalshi_key> \
  --private-key <path/to/private_key.pem>

tennisprediction scan-kalshi-ev \
  --artifact-dir models/runs/run-001 \
  --expected-feature-version 02-04 \
  --expected-split-manifest-id <split_id>

tennisprediction review-monitoring-report --run-id live-monitor
```

For command details, also see [docs/operations.md](/Users/andrewlay/tennisprediction/docs/operations.md:1).

## Quality and Testing

The repository currently contains:

- 62 Python source files under `src/tennisprediction`
- 37 unit test modules under `tests/unit`
- 94 discovered test functions

Coverage is concentrated around:

- ingestion manifests, validation, and quarantine
- canonical normalization
- feature ordering, state, persistence, and leakage guards
- modeling datasets, splits, metrics, calibration, registry, and XGBoost
- backtesting replay, decisions, reports, and metrics
- Kalshi client, storage, jobs, executable pricing, and scan orchestration
- market mapping normalization, aliases, and resolver behavior
- CLI surface and operational logging

## Guardrails and Scope Boundaries

These are not aspirational notes; they are reflected in the current implementation and tests:

- ATP only: no WTA, Challenger, ITF, or doubles support is part of v1
- Kalshi only: no bookmaker or alternative prediction-market adapters
- read-only monitoring only: no trade execution path
- chronological feature generation only
- calibrated probabilities are first-class outputs
- artifact replay and backtest evidence are required downstream inputs
- repository-local storage and settings are enforced by config validation

## Known Limitations

- The historical source is Jeff Sackmann `tennis_atp`, so schema expectations are centered on that source.
- The backtest uses a synthetic even-money market proxy, not historical Kalshi fills or full book replay.
- The live monitoring flow is one-shot CLI execution, not a daemonized service.
- Alerting is terminal/file oriented; there is no built-in email, SMS, or trade-routing integration.
- There is no active v1 roadmap work left; future expansion should begin as a new milestone.

## Additional Documentation

- [docs/operations.md](/Users/andrewlay/tennisprediction/docs/operations.md:1)
- [.planning/ROADMAP.md](/Users/andrewlay/tennisprediction/.planning/ROADMAP.md:1)
- [.planning/STATE.md](/Users/andrewlay/tennisprediction/.planning/STATE.md:1)
- [.planning/v1.0-MILESTONE-AUDIT.md](/Users/andrewlay/tennisprediction/.planning/v1.0-MILESTONE-AUDIT.md:1)
