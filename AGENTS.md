<!-- GSD:project-start source:PROJECT.md -->

## Project

**ATP Tennis Prediction and Kalshi EV Detection System**

This project is a production-grade ATP tennis prediction platform that uses historical match data to generate calibrated match win probabilities, then compares those probabilities against live Kalshi market prices to identify positive expected value opportunities. It is for building and operating an end-to-end quantitative workflow: ingest ATP data, engineer leakage-safe features, train and calibrate models, monitor Kalshi markets, rank opportunities, and support decisions with backtesting evidence.

The initial specification is `project-outline.yaml`; it is treated as the source project spec for initialization.

**Core Value:** Produce trustworthy, leakage-free ATP match win probabilities and convert them into actionable Kalshi-only positive expected value signals.

### Constraints

- **Scope**: ATP only - avoid expanding requirements, data models, or market matching to WTA or other tours.
- **Market platform**: Kalshi only - all live pricing, orderbook, and opportunity logic targets Kalshi markets.
- **Primary data source**: Jeff Sackmann `tennis_atp` - historical ingestion should be designed around this repository's CSV files and schema drift.
- **Leakage prevention**: Chronological feature computation only - rankings, Elo, recent form, head-to-head, and aggregate stats must exclude future matches.
- **Probability quality**: Calibrated probabilities are required - the system cannot stop at classification accuracy.
- **Backtesting**: Profitability claims require replay or simulation evidence - live alerts should not be treated as validated until backtests support them.
- **Engineering quality**: Code must be modular, typed, logged, configurable, reproducible, and covered by focused unit tests for critical logic.

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Stack Recommendation

## Recommended Stack

### Runtime and Packaging

| Technology | Version target | Purpose | Confidence | Why |
|------------|----------------|---------|------------|-----|
| Python | 3.12.x | Main runtime | HIGH | Current pandas and scikit-learn require Python 3.11+, and Python 3.12 is the conservative 2026 default: modern typing/performance without making the project depend on newer 3.13/3.14 ecosystem edges. |
| uv | 0.11.x | Package manager, lockfile, Python version management, command runner | HIGH | Replaces pip/venv/pip-tools/pyenv for this project with one reproducible workflow and a universal lockfile. Use `uv.lock` as the canonical environment artifact. |
| pyproject.toml | PEP 621 | Project metadata and tool config | HIGH | Keeps dependencies, linting, test config, and scripts in one standard Python project file. |

### Data Ingestion and Storage

| Technology | Version target | Purpose | Confidence | Why |
|------------|----------------|---------|------------|-----|
| Jeff Sackmann `tennis_atp` | Git source pinned by commit SHA | Primary ATP historical source | HIGH | The repository includes ATP players, rankings, results, and match stats. Pin a commit SHA for reproducibility and store attribution/licensing metadata with ingested snapshots. |
| polars | 1.41.x | CSV ingestion, schema enforcement, feature transforms | HIGH | Faster and more memory-efficient than pandas for multi-season CSV processing; lazy scans and strict schemas fit the need to rebuild chronological features repeatedly. |
| pyarrow | 24.x | Parquet interoperability | HIGH | Parquet should be the canonical intermediate format for raw snapshots, cleaned matches, features, predictions, and backtest outputs. |
| DuckDB | 1.5.x | Local analytical database and SQL query engine | HIGH | Embedded OLAP database with direct Python/Pandas integration and no server to operate. Good fit for local backtests, feature audits, and opportunity history before any production database is needed. |
| pandas | 3.0.x | Compatibility bridge | HIGH | Keep pandas at the edges for scikit-learn/XGBoost compatibility, reporting, and notebooks. Do not make pandas the primary transform engine. |

### Modeling and Calibration

| Technology | Version target | Purpose | Confidence | Why |
|------------|----------------|---------|------------|-----|
| scikit-learn | 1.9.x | Baselines, preprocessing, metrics, temporal CV, calibration | HIGH | Provides logistic regression, random forest, metrics, `TimeSeriesSplit`, calibration curves, and `CalibratedClassifierCV`; this covers the required benchmark and probability-quality work. |
| XGBoost | 3.2.x | Production candidate tabular model | HIGH | Strong default for structured tabular data and available through a scikit-learn-compatible estimator interface. Use it after leakage-safe features and chronological validation are in place. |
| Optuna | 4.9.x | Hyperparameter optimization | HIGH | Use for bounded, reproducible tuning of XGBoost and baseline models after the initial baseline is stable. |
| joblib | 1.5.x | Model serialization for sklearn-compatible artifacts | HIGH | Adequate for local model artifacts in v1. Also log artifacts to MLflow. |
| MLflow | 3.13.x | Experiment tracking and model registry-lite | MEDIUM-HIGH | Useful for tracking metrics, feature sets, calibration method, data snapshot, and model artifact. Avoid running a heavyweight remote tracking service until needed; file-backed/local tracking is enough initially. |
| SHAP | 0.52.x | Model diagnostics | MEDIUM | Useful after model selection to understand feature behavior. Not required for the MVP and should not distract from calibration/backtesting. |

### Kalshi Integration

| Technology | Version target | Purpose | Confidence | Why |
|------------|----------------|---------|------------|-----|
| Kalshi Predictions REST API | Trade API v2 / OpenAPI 3.21.0 | Market discovery, market details, orderbooks, historical endpoints | HIGH | Official docs expose markets, market details, orderbooks, events, historical data, demo/prod hosts, and raw OpenAPI/AsyncAPI specs. |
| kalshi-python | 2.1.4 | Generated typed REST client | MEDIUM | PyPI package is maintained by Kalshi and generated from OpenAPI. Use it for straightforward REST calls, but wrap it behind a project-owned interface so SDK churn does not leak into business logic. |
| httpx | 0.28.x | Direct REST fallback and custom client implementation | HIGH | Needed for signing, retry instrumentation, and endpoints where the generated SDK is cumbersome or behind current docs. |
| websockets | latest stable compatible with Python 3.12 | Live market/orderbook subscriptions | HIGH | Kalshi WebSocket docs require authenticated handshake and support orderbook/ticker/event lifecycle channels. Use this for live monitoring once REST polling is correct. |
| cryptography | latest stable compatible with Python 3.12 | RSA-PSS request signing | HIGH | Kalshi API key auth requires RSA private-key signing of timestamp + method + path without query parameters. |
| tenacity | 9.1.x | Retry/backoff | HIGH | Wrap rate-limited, transient, and network-failure calls; keep retries explicit and bounded. |
| APScheduler | 3.11.x | Simple polling scheduler | MEDIUM-HIGH | Good enough for v1 market polling and periodic ingestion. Defer distributed orchestration. |

### Matching, EV, and Backtesting

| Technology | Version target | Purpose | Confidence | Why |
|------------|----------------|---------|------------|-----|
| RapidFuzz | 3.14.x | Player and market-title fuzzy matching | HIGH | Fast, maintained fuzzy matching for Kalshi market titles to ATP players. Use it with deterministic normalization and manual override tables. |
| pydantic | 2.13.x | Typed config and DTO validation | HIGH | Validates external API payloads, model outputs, opportunity records, and config boundaries. |
| pydantic-settings | 2.14.x | Environment/config loading | HIGH | Clean separation of secrets, Kalshi endpoints, thresholds, paths, and model settings. |
| Custom event replay | Project code | Backtesting | HIGH | Build a domain-specific replay around ATP matches, model predictions, market prices, liquidity, and fees. Generic backtesting packages are built for continuous financial bars and will obscure prediction-market mechanics. |

### CLI, Reporting, and Alerts

| Technology | Version target | Purpose | Confidence | Why |
|------------|----------------|---------|------------|-----|
| Typer | 0.26.x | CLI commands | HIGH | Good fit for typed commands like `ingest`, `build-features`, `train`, `calibrate`, `backtest`, `scan-kalshi`, and `rank-opportunities`. |
| Rich | 15.x | Terminal tables/log output | HIGH | Useful for local EV dashboards and backtest summaries without building a UI too early. |
| matplotlib | 3.11.x | Calibration, ROC, profit curve plots | HIGH | Standard static plots for model diagnostics and reports. |
| plotly | 6.8.x | Optional interactive reports | MEDIUM | Useful for exploratory backtest review, but not required for core pipeline correctness. |
| email/SMS provider | Defer selection | Alerts | MEDIUM | Start with terminal/file alerts. Choose SendGrid/Twilio only once opportunity quality is validated. |

### Quality, Testing, and CI

| Technology | Version target | Purpose | Confidence | Why |
|------------|----------------|---------|------------|-----|
| pytest | 9.1.x | Unit and integration tests | HIGH | Required for leakage-sensitive logic: chronological feature windows, Elo updates, player matching, probability conversion, EV, and backtest replay. |
| Ruff | 0.15.x | Linting and formatting | HIGH | Replaces Black/isort/flake8-style tooling with one fast tool and `pyproject.toml` config. |
| mypy | 2.1.x | Static typing | HIGH | Useful for API boundaries, DTOs, model config, and deterministic backtest interfaces. Use strict settings for project code. |
| pre-commit | latest stable | Local quality gate | HIGH | Run Ruff, mypy, and fast tests before commits. |
| GitHub Actions | hosted CI | CI | HIGH | Run `uv sync`, `ruff check`, `ruff format --check`, `mypy`, and `pytest` on push/PR. |

## Initial Installation

## Dependency Groups

| Group | Packages |
|-------|----------|
| default | `polars`, `pyarrow`, `duckdb`, `pandas`, `pydantic`, `pydantic-settings`, `typer`, `rich` |
| ml | `scikit-learn`, `xgboost`, `optuna`, `mlflow`, `joblib`, `shap`, `matplotlib`, `plotly` |
| kalshi | `kalshi-python`, `httpx`, `websockets`, `cryptography`, `tenacity`, `apscheduler` |
| dev | `pytest`, `ruff`, `mypy`, `pre-commit` |

## Recommended Project Layout

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| DataFrame engine | Polars primary, pandas compatibility | pandas-only | Works, but slower and easier to make ad hoc stateful transforms as feature rebuilds grow. |
| Analytical database | DuckDB | PostgreSQL from day one | PostgreSQL is unnecessary operational load for local research/backtests; add it only if a deployed multi-user service appears. |
| Distributed processing | None | Spark/Dask/Ray | Jeff Sackmann ATP data and Kalshi market monitoring do not justify distributed complexity in v1. |
| Modeling | scikit-learn + XGBoost | PyTorch/TensorFlow | This is structured tabular binary classification with calibration; deep learning adds complexity without clear v1 value. |
| Calibration | scikit-learn calibration | Hand-rolled calibration | Official implementations reduce risk; custom calibration can be added only if diagnostics prove a gap. |
| Backtesting | Custom deterministic replay | Backtrader/vectorbt/Zipline | Prediction-market binary contracts, settlement, fees, liquidity, and yes/no orderbooks differ from equity/crypto bar backtests. |
| Orchestration | Typer + APScheduler | Airflow/Dagster/Prefect immediately | The first milestone needs reproducible scripts and tests, not a scheduler platform. Reassess after live monitoring has stable jobs. |
| Kalshi client | `kalshi-python` wrapped by project interface + `httpx` fallback | Direct generated SDK everywhere | Generated SDK object models can churn and leak into business logic. A wrapper preserves control. |
| Market scope | Kalshi only | Polymarket/bookmaker adapters | Explicitly out of scope and would dilute matching, compliance, and EV logic. |
| Tennis scope | ATP singles/tour-level main draw for v1 | WTA/Challenger/ITF/doubles | Explicitly out of scope; Jeff Sackmann also includes doubles/lower-level files, but this project should filter them out by design. |

## Confidence by Recommendation

| Area | Confidence | Notes |
|------|------------|-------|
| Python 3.12 + uv | HIGH | Verified current package requirements and uv project-management support. |
| Polars + Parquet + DuckDB | HIGH | Fits CSV ingestion, immutable snapshots, local analytical queries, and reproducible backtests. |
| scikit-learn + XGBoost | HIGH | Matches required baselines, metrics, temporal CV, and production tabular model candidate. |
| Calibration approach | HIGH | Official scikit-learn calibration and calibration metrics support the project requirement for probability quality. |
| Kalshi REST/WebSocket API | HIGH | Official docs expose REST, WebSocket, authentication, OpenAPI, and AsyncAPI surfaces. |
| `kalshi-python` package | MEDIUM | Package is maintained under the Kalshi identity on PyPI and generated from OpenAPI, but latest release is 2025-09-06 while docs show API spec version 3.21.0; wrap and verify. |
| Custom backtesting | HIGH | Required because EV depends on prediction-market-specific prices, liquidity, fees, and settlement assumptions. |
| APScheduler for v1 polling | MEDIUM-HIGH | Adequate for one-process polling; replace only when deployment requirements demand durable orchestration. |

## Hard Constraints to Encode Early

- Reject non-ATP source files during ingestion unless a future roadmap phase explicitly expands scope.
- Pin the Jeff Sackmann repository by commit SHA, not branch name.
- Store Jeff Sackmann attribution and note the CC BY-NC-SA 4.0 non-commercial license constraint in project docs and metadata.
- Maintain chronological feature builders that accept an `as_of_date` or process matches sorted by event date.
- Require tests that fail if Elo, recent form, H2H, rankings, or aggregate stats include the current/future match.
- Keep Kalshi market mapping specific to Kalshi market/event payloads and tennis title conventions.
- Keep market monitoring read-only for v1; no live order placement interfaces in core services.

## Sources

- Jeff Sackmann `tennis_atp` repository: https://github.com/JeffSackmann/tennis_atp
- Kalshi API docs welcome/specs: https://docs.kalshi.com/welcome
- Kalshi OpenAPI spec: https://docs.kalshi.com/openapi.yaml
- Kalshi API keys/auth signing: https://docs.kalshi.com/getting_started/api_keys
- Kalshi WebSocket connection docs: https://docs.kalshi.com/websockets/websocket-connection
- Kalshi `kalshi-python` PyPI package: https://pypi.org/project/kalshi-python/
- scikit-learn `CalibratedClassifierCV`: https://scikit-learn.org/stable/modules/generated/sklearn.calibration.CalibratedClassifierCV.html
- scikit-learn `TimeSeriesSplit`: https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- scikit-learn probability calibration guide: https://scikit-learn.org/stable/modules/calibration.html
- XGBoost docs and release notes: https://xgboost.readthedocs.io/en/stable/
- Polars user guide: https://docs.pola.rs/
- DuckDB rationale/docs: https://duckdb.org/why_duckdb
- Apache Arrow Parquet docs: https://arrow.apache.org/docs/python/parquet.html
- uv docs: https://docs.astral.sh/uv/
- Ruff docs: https://docs.astral.sh/ruff/
- mypy docs: https://mypy.readthedocs.io/en/stable/
- pytest docs: https://docs.pytest.org/en/stable/
- Pydantic docs: https://docs.pydantic.dev/latest/

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.claude/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
