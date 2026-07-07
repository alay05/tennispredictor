# Run v1.0

This repository ships a complete ATP-only, Kalshi-only workflow for generating calibrated tennis win probabilities, comparing them to Kalshi market prices, and surfacing positive expected value opportunities as read-only reports.

If you have never seen this repo before, the simplest mental model is:

1. put a pinned Jeff Sackmann `tennis_atp` snapshot in the expected raw-data folder
2. ingest it into DuckDB
3. build leakage-safe features
4. train and calibrate a model bundle
5. evaluate and backtest that bundle
6. optionally collect Kalshi snapshots and run the live EV scan
7. inspect the persisted reports and audit logs

This file explains what the system does, how it is implemented at a practical level, and how to run it yourself.

## What v1.0 Is

v1.0 is a one-shot workflow, not a daemon. It is designed around explicit commands you run in order. The shipped CLI is:

```bash
tennisprediction version
tennisprediction health
tennisprediction ingest-snapshot
tennisprediction build-features
tennisprediction train-artifact-bundle
tennisprediction evaluate-artifact
tennisprediction run-backtest
tennisprediction collect-kalshi-snapshots
tennisprediction scan-kalshi-ev
tennisprediction review-monitoring-report
```

The project is ATP only. It does not model WTA, doubles, Challenger, ITF, or exhibitions. It is also Kalshi only for market integration. There is no trade execution surface in v1.0.

## What It Can Do

At a high level, v1.0 can:

- ingest historical ATP source files with provenance and checksum tracking
- normalize those files into canonical ATP entities in DuckDB
- build chronological, leakage-safe feature snapshots
- train logistic regression, random forest, or XGBoost models
- calibrate model probabilities
- write model bundles and evaluation reports
- backtest predictions with reason-coded decisions
- collect Kalshi market snapshots in read-only mode
- map Kalshi markets to canonical ATP matches
- compute executable EV using configured thresholds, fee, slippage, and liquidity assumptions
- write terminal and persisted opportunity reports
- write correlated audit logs for operator runs

What it does not do:

- it does not place trades
- it does not run as a background service
- it does not silently fetch ATP data for you
- it does not support other bookmakers or prediction market venues

## How It Is Implemented

The important implementation pattern is that the CLI is thin. It mainly validates inputs and delegates to project-owned orchestration code in `src/tennisprediction/operations.py`.

That orchestration layer then calls the actual subsystems:

- `ingestion/` for source snapshot loading and raw-data layout
- `domain/` for canonical IDs and normalized ATP entities
- `features/` for chronological feature construction
- `modeling/` for splits, training, calibration, metrics, and artifact persistence
- `backtesting/` for replay, EV decision logic, and guarded reports
- `kalshi/` for read-only market collection and snapshot persistence
- `market_mapping/` for ATP-to-Kalshi mapping and ambiguity rejection
- `monitoring/` for live advisory report rendering
- `logging.py` for correlated audit logging with file fan-out

### Raw ATP Snapshot Handling

The ingestion code expects a local raw snapshot under:

```text
data/raw/tennis_atp/<commit_sha>/
```

The commit SHA must be a lowercase Git SHA string, not a branch name. The code validates that the raw snapshot exists and that the checksum manifest still matches the files on disk.

This means `ingest-snapshot` is not a downloader. It is a validator and normalizer for a snapshot you have already staged locally.

### Canonical Data Model

After ingestion, the data is normalized into canonical ATP tables:

- players
- tournaments
- matches
- rankings
- match stats

Each entity carries source lineage metadata, so the repo can tell you where the row came from and when it was acquired.

### Feature Engineering

Feature creation is chronological. That is the core leakage protection mechanism.

For each match, the feature engine:

- emits the pre-match snapshot first
- computes Elo, surface Elo, ranking features, form features, serve/return aggregates, head-to-head history, rest, and match context from prior information only
- then updates post-match state for future rows

That design is what makes the feature set leakage-safe. The tests explicitly check that current or future matches do not influence the features.

### Modeling and Calibration

The modeling layer uses frozen chronological splits rather than random shuffling. The shipped model families are:

- logistic regression
- random forest
- XGBoost

After fitting, the model probabilities are calibrated on a disjoint validation period. The bundle stores:

- the trained estimator or raw model file
- a preprocessor sidecar for XGBoost
- the calibrator
- feature column definitions
- the frozen split manifest
- metrics and report files

### Backtesting

Backtesting replays the model predictions against a reusable EV decision engine. The backtest is intentionally conservative about claims: it uses a synthetic even-money proxy rather than pretending historical Kalshi orderbook data exists when it does not.

The backtest output includes:

- accepted and rejected opportunities
- reason codes
- a summary
- uncertainty estimates
- provenance metadata

### Kalshi Monitoring

The live monitoring path is read-only.

`collect-kalshi-snapshots` stores market and orderbook snapshots.

`scan-kalshi-ev`:

- loads the latest matching Kalshi snapshots
- resolves market mappings
- loads the replayed model predictions
- derives executable market inputs
- calculates EV and confidence thresholds
- ranks and stores the final opportunity set

If terminal alerts are enabled, it also renders a console report. The same data is persisted under `reports/monitoring/<run_id>/`.

### Audit Logging

Every one-shot command emits correlated audit logs to:

```text
reports/audit/operations.log
```

The logger adds run context fields like `run_id`, `command`, `stage`, and operational decision data. Sensitive values are redacted. This is what makes the workflow reviewable after the fact.

## Install and Sanity Check

From a fresh clone:

```bash
uv sync --locked --dev --group ml
```

Then confirm the command tree is live:

```bash
.venv/bin/tennisprediction health
.venv/bin/tennisprediction --help
```

If you want to validate the repo itself before running the workflow:

```bash
PRE_COMMIT_HOME=.cache/pre-commit .venv/bin/pre-commit run --all-files
```

That checks formatting, linting, typing, and the critical regression surface.

## The Fastest Way To See It Work

If you just want to see the CLI and test surfaces working before doing a full ATP run, use the smoke tests:

```bash
.venv/bin/pytest -q tests/unit/test_cli_smoke.py tests/unit/test_cli_commands.py -x
```

That verifies:

- the packaged `tennisprediction` entrypoint works
- the command tree is wired correctly
- the one-shot orchestration seam is reachable

If you want to verify the whole critical surface:

```bash
.venv/bin/pytest -q \
  tests/unit/test_cli_smoke.py \
  tests/unit/test_cli_commands.py \
  tests/unit/test_operational_logging.py \
  tests/unit/test_live_monitor_reports.py \
  tests/unit/test_live_scan_orchestration.py \
  tests/unit/test_feature_leakage.py \
  tests/unit/test_backtesting_decisions.py \
  tests/unit/test_live_scan_pricing_contract.py \
  -x
```

## Full ATP Workflow

To run the actual ATP pipeline, you need a raw Sackmann snapshot already staged under `data/raw/tennis_atp/<commit_sha>/`.

The rough flow is:

### 1. Ingest ATP

```bash
.venv/bin/tennisprediction ingest-snapshot --source-commit-sha <commit_sha>
```

This reads the local raw snapshot, verifies checksums, normalizes the data, and persists canonical ATP tables in DuckDB.

### 2. Build Features

```bash
.venv/bin/tennisprediction build-features
```

This builds the leakage-safe feature rows from the canonical tables.

### 3. Train a Model Bundle

```bash
.venv/bin/tennisprediction train-artifact-bundle \
  --run-id demo \
  --train-end-date 20240115 \
  --validation-end-date 20240215 \
  --test-end-date 20240315
```

This creates a bundle under `models/runs/demo/` with the trained model, calibrator, split manifest, feature columns, and manifest metadata.

You can optionally override the model family or calibration method:

- `--model-family logistic_regression`
- `--model-family random_forest`
- `--model-family xgboost`
- `--calibration-method sigmoid`
- `--calibration-method isotonic`

### 4. Evaluate the Bundle

```bash
.venv/bin/tennisprediction evaluate-artifact \
  --artifact-dir models/runs/demo \
  --expected-feature-version 02-04 \
  --expected-split-manifest-id <split_id>
```

This replays the artifact and writes evaluation output under `reports/modeling/demo/`.

### 5. Run a Backtest

```bash
.venv/bin/tennisprediction run-backtest \
  --artifact-dir models/runs/demo \
  --expected-feature-version 02-04 \
  --expected-split-manifest-id <split_id> \
  --run-id demo
```

This writes backtest output under `reports/backtesting/demo/`.

## Live Kalshi Workflow

If you want live market monitoring, you need Kalshi API credentials and a private key file.

### 1. Collect Kalshi Snapshots

```bash
.venv/bin/tennisprediction collect-kalshi-snapshots \
  --access-key <kalshi_access_key> \
  --private-key <path_to_rsa_private_key>
```

This collects read-only market and orderbook snapshots into the repo-local snapshot database.

### 2. Scan for EV

```bash
.venv/bin/tennisprediction scan-kalshi-ev \
  --artifact-dir models/runs/demo \
  --expected-feature-version 02-04 \
  --expected-split-manifest-id <split_id>
```

This uses the newest matching snapshot data and writes the monitoring report under `reports/monitoring/live-monitor/` by default.

You can change the scan thresholds with:

- `--min-edge`
- `--min-confidence`
- `--min-liquidity`
- `--fee-per-contract`
- `--slippage-per-contract`

You can also collect fresh snapshots during the scan with `--collect-fresh`, but that still remains read-only.

### 3. Review the Persisted Monitoring Report

```bash
.venv/bin/tennisprediction review-monitoring-report --run-id live-monitor
```

This re-renders the persisted monitoring report from disk. It does not rescan the market.

## Important File Locations

After you run the pipeline, expect to inspect:

- `data/duckdb/tennisprediction.duckdb`
- `models/runs/<run_id>/`
- `reports/modeling/<run_id>/`
- `reports/backtesting/<run_id>/`
- `reports/monitoring/<run_id>/`
- `reports/audit/operations.log`

## What To Trust, and What Not To Trust

Trust:

- the artifact manifests
- the split ids
- the audit log
- the persisted report files
- the unit tests and critical quality gates

Do not over-trust:

- a single run with a tiny sample
- any profitability claim from the synthetic even-money backtest
- any live EV scan without checking mapping state, liquidity, and freshness
- any market that is ambiguous or unmatched

## Practical Advice

If you are brand new to the repo, do this in order:

1. run `tennisprediction health`
2. run `pre-commit run --all-files`
3. run the CLI smoke tests
4. stage a raw ATP snapshot
5. ingest it
6. build features
7. train a small demo bundle
8. evaluate it
9. backtest it
10. inspect the reports

If you have Kalshi credentials, add the live snapshot collection and live EV scan after that.

## One-Sentence Summary

v1.0 is a reproducible ATP-to-Kalshi workflow that turns historical ATP matches into calibrated probabilities, compares them to read-only Kalshi pricing, and writes auditable opportunity reports.
