# Phase 07 Operations Runbook

This repo ships a one-shot, ATP-only, Kalshi-only workflow. It is read-only for live monitoring and reporting: the system can ingest historical ATP data, build features, train and evaluate artifacts, replay backtests, collect Kalshi snapshots, scan for EV, and re-render persisted monitoring reports. It does not ship daemonized polling controls or trade execution.

## Setup

Use the repo-standard `uv` workflow:

```bash
uv sync --locked --dev --group ml
```

Recommended local quality gate:

```bash
pre-commit install --install-hooks
pre-commit run --all-files
```

The CLI loads repo-local settings through the `TENNISPREDICTION_` prefix. Paths stay inside the repository by default.

## Inputs

Historical training and feature work use the Jeff Sackmann `tennis_atp` snapshot pinned by commit SHA. Live market collection uses Kalshi credentials only when `collect-kalshi-snapshots` or `scan-kalshi-ev --collect-fresh` needs a live read-only snapshot pull.

## One-Shot CLI

Run the shipped command tree with `tennisprediction`:

```bash
tennisprediction version
tennisprediction health
tennisprediction ingest-snapshot --source-commit-sha <sha>
tennisprediction build-features
tennisprediction train-artifact-bundle --run-id <run_id> --train-end-date YYYYMMDD --validation-end-date YYYYMMDD --test-end-date YYYYMMDD
tennisprediction evaluate-artifact --artifact-dir models/runs/<run_id> --expected-feature-version 02-04 --expected-split-manifest-id <split_id>
tennisprediction run-backtest --artifact-dir models/runs/<run_id> --expected-feature-version 02-04 --expected-split-manifest-id <split_id> --run-id <run_id>
tennisprediction collect-kalshi-snapshots --access-key <key> --private-key <path>
tennisprediction scan-kalshi-ev --artifact-dir models/runs/<run_id> --expected-feature-version 02-04 --expected-split-manifest-id <split_id>
tennisprediction review-monitoring-report --run-id live-monitor
```

Command intent:

- `ingest-snapshot` persists a normalized ATP snapshot into DuckDB.
- `build-features` materializes leakage-safe features from the persisted canonical tables.
- `train-artifact-bundle` writes a model bundle under `models/runs/<run_id>`.
- `evaluate-artifact` replays a trained bundle and writes evaluation output under `reports/modeling/<run_id>`.
- `run-backtest` replays predictions through the synthetic even-money proxy and writes `reports/backtesting/<run_id>`.
- `collect-kalshi-snapshots` stores read-only market snapshots.
- `scan-kalshi-ev` scores Kalshi markets and writes the live advisory monitoring report.
- `review-monitoring-report` re-renders an existing monitoring run from persisted parquet files.

## Output Locations

Default repo-local outputs:

- DuckDB snapshot and feature storage: `data/duckdb/tennisprediction.duckdb`
- Model artifacts: `models/runs/<run_id>/`
- Model reports: `reports/modeling/<run_id>/`
- Backtest reports: `reports/backtesting/<run_id>/`
- Monitoring reports: `reports/monitoring/<run_id>/`
- Audit log: `reports/audit/operations.log`

Model bundle contents:

- `manifest.json`
- `feature_columns.json`
- `split_manifest.json`
- `raw_model.joblib` or `raw_model.ubj` plus `preprocessor.joblib` for XGBoost
- `calibrator.joblib`
- model report files under `reports/modeling/<run_id>/`

Monitoring report contents:

- `summary.json`
- `accepted_opportunities.parquet`
- `rejected_opportunities.parquet`
- `ranked_opportunities.csv`
- `operator_report.txt`

Backtest report contents:

- `summary.json`
- `uncertainty.json`
- `provenance.json`
- `accepted_opportunities.parquet`
- `rejected_opportunities.parquet`
- `decision_reason_counts.csv`
- `equity_curve.csv`

## OPS-02 Settings Surface

The shipped one-shot settings surface is intentionally narrow:

- `data_dir`, `models_dir`, `reports_dir`, and `duckdb_path` keep storage repo-local.
- `alert_channels` accepts `terminal` and `file` only.
- `default_feature_version` selects the default feature build.
- `default_model_family` selects the default model family.
- `default_calibration_method` selects the default calibration path.
- `default_monitoring_run_id` and `default_monitoring_report_run_id` select the monitoring report namespace.
- `default_min_edge`, `default_min_confidence`, and `default_min_liquidity` set the advisory thresholds.

The doc does not define any polling scheduler, loop interval, or daemon mode. Those controls are deferred by design under D-06 and D-07.

## Trust Boundaries

- ATP only: the project does not ingest or model WTA, Challenger, ITF, or doubles data in v1.
- Kalshi only: live pricing, orderbook, and opportunity logic target Kalshi markets only.
- Read-only live monitoring: `scan-kalshi-ev` is advisory and does not place orders.
- Backtesting is a proxy replay: `run-backtest` uses a synthetic even-money backtest assumption, not a historical Kalshi orderbook replay.
- Monitoring reports are persisted evidence: `review-monitoring-report` re-renders existing monitoring files and does not rescan markets.
- Audit logs are repo-local: `reports/audit/operations.log` captures the shared one-shot run context.

## Operator Checklist

1. Sync the environment with `uv sync --locked --dev --group ml`.
2. Confirm the CLI is available with `tennisprediction health`.
3. Ingest the pinned ATP source snapshot.
4. Build features and train an artifact bundle.
5. Evaluate the artifact bundle before trusting downstream outputs.
6. Run the backtest and inspect the report under `reports/backtesting/<run_id>/`.
7. Collect or reuse Kalshi snapshots, then run `scan-kalshi-ev`.
8. Review the persisted monitoring report with `review-monitoring-report`.
9. Check `reports/audit/operations.log` for correlated run context and redaction markers.

If a result looks too good to be true, trust the artifact manifests, split ids, report files, and audit log before trusting the advisory signal itself.
