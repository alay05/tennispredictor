# Project Research Summary

**Project:** ATP Tennis Prediction and Kalshi EV Detection System
**Domain:** ATP-only tennis match prediction, calibrated probability modeling, and Kalshi-only EV detection
**Researched:** 2026-06-16
**Confidence:** MEDIUM-HIGH

## Executive Summary

This is a quantitative sports prediction and market-monitoring system, not a general betting app. Experts should build it as a deterministic, reproducible pipeline: ingest ATP history from Jeff Sackmann's `tennis_atp`, normalize it into canonical ATP entities, compute point-in-time features chronologically, train and calibrate models, backtest decisions, then compare calibrated probabilities against live Kalshi prices. The core product value is trust: probabilities and EV signals must be explainable, reproducible, and free of future-data leakage.

The recommended approach is a Python 3.12 batch-first application with `uv`, Polars/Parquet/DuckDB for data, scikit-learn/XGBoost for modeling, MLflow or local artifact manifests for experiment tracking, and a thin project-owned Kalshi client wrapping `kalshi-python` plus `httpx`/WebSocket adapters. Keep v1 narrow: ATP singles only, Jeff Sackmann as the primary historical source, Kalshi as the only market source, and no automated trade execution.

The largest risks are chronological leakage, poor probability calibration, incorrect Kalshi market-to-match mapping, non-executable price assumptions, and overclaimed backtests. Treat these as phase gates. Do not progress to live alerts until leakage tests pass, model probabilities are calibrated on chronological splits, Kalshi mappings are auditable and ambiguity-safe, orderbook pricing is side-aware, and backtests clearly distinguish actual historical market snapshots from synthetic assumptions.

## Key Findings

### Recommended Stack

Use a Python data/ML stack optimized for reproducibility and point-in-time tabular modeling. Avoid Spark, Airflow, deep learning, generic sportsbook abstractions, and auto-trading frameworks in v1; they add operational load before the core probability and EV pipeline is validated.

**Core technologies:**
- Python 3.12 + `uv`: reproducible runtime, lockfile, and command workflow.
- Polars + PyArrow + Parquet: fast CSV ingestion, schema enforcement, and immutable intermediate datasets.
- DuckDB: local analytical persistence for feature audits, backtests, predictions, and opportunity history.
- scikit-learn: logistic regression, random forest baseline, chronological validation tools, metrics, and calibration.
- XGBoost: production tabular model candidate after baselines and feature contracts are stable.
- MLflow or local artifact manifests: track source snapshot, feature version, model version, calibrator, and metrics.
- `kalshi-python` wrapped by project interfaces, plus `httpx`, `websockets`, and `cryptography`: Kalshi REST/WebSocket access without leaking SDK objects into business logic.
- RapidFuzz + manual alias tables: deterministic player and market-title matching with reviewable overrides.
- Typer + Rich: CLI-first operation for ingestion, feature builds, training, backtests, scans, and reports.
- pytest + Ruff + mypy: quality gates for leakage-sensitive logic, Kalshi parsing, EV math, and typed interfaces.

**Critical version/usage requirements:**
- Pin the Jeff Sackmann `tennis_atp` source by commit SHA and store attribution/license metadata.
- Store raw source snapshots under immutable paths and write normalized/features/predictions/backtests as versioned derived outputs.
- Use chronological train/validation/test splits only. No random shuffled evaluation for official metrics.
- Fit probability calibration on a disjoint chronological validation period.
- Use decimal/fixed-point arithmetic for Kalshi prices, fees, counts, and EV calculations.

### Expected Features

**Must have (table stakes):**
- Sackmann ATP ingestion with source manifests, checksums, schema validation, and ATP-only filters.
- Canonical ATP match, player, ranking, tournament, and match-stat store with stable IDs.
- Chronological feature engine that emits pre-match feature snapshots before updating Elo, form, H2H, ranking, or rolling stats.
- Overall Elo and surface Elo, ranking/ranking-points deltas, recent form, serve/return aggregates, head-to-head, match context, and pairwise differential features.
- Logistic regression and random forest baselines, plus XGBoost production candidate.
- Calibration and model evaluation using accuracy, ROC AUC, log loss, Brier score, calibration curves, ECE, and segment diagnostics.
- Model/artifact registry capturing source version, feature version, split boundaries, model version, calibration method, and metrics.
- Kalshi market discovery, market detail ingestion, and orderbook ingestion with raw snapshot persistence.
- Deterministic player-name normalization and Kalshi market-to-ATP-match mapping with matched/ambiguous/unmatched states.
- Market implied probability, executable price, edge, EV, liquidity, threshold filtering, opportunity ranking, and rejection reasons.
- Backtesting framework for predictive performance and market/EV decision replay before live reliance.
- Persistent prediction, market, opportunity, alert, and backtest history.
- Focused unit tests for chronological exclusion, Elo update order, ranking as-of lookup, name mapping, side orientation, orderbook pricing, EV calculation, filtering, and ambiguous-market rejection.

**Should have (differentiators):**
- Leakage audit reports showing feature as-of behavior and excluded future rows.
- Calibration-first model selection that promotes models by probability quality, not headline accuracy.
- Mapping confidence and manual review queue for ambiguous Kalshi markets.
- Liquidity-aware executable EV based on orderbook depth, spread, fees, and fill assumptions.
- Shadow-mode live monitoring that records live markets and predictions before external alerts are trusted.
- Backtest limitation labeling for actual Kalshi snapshots vs synthetic/reconstructed market prices.
- Segment diagnostics by surface, tournament level, rank band, data era, and confidence bucket.

**Defer or keep out of scope:**
- WTA, doubles, Challenger, ITF, Futures, exhibitions, team events, and lower-tier tours.
- Betting platforms other than Kalshi.
- Automated trade execution, order lifecycle management, portfolio management, bankroll automation, and sizing recommendations.
- In-play/point-by-point models.
- LLM-first player matching.
- Scraping unofficial odds or tennis sites.
- Web dashboard as a v1 prerequisite.
- Positive-ROI claims without sample size, uncertainty, drawdown, and backtest provenance.

### Architecture Approach

Build an append-oriented, batch-first architecture with explicit persistence boundaries: raw source snapshots, canonical ATP domain tables, chronological state, point-in-time feature snapshots, versioned datasets, model/calibrator artifacts, Kalshi market snapshots, pricing observations, predictions, opportunities, alerts, and backtests. Training, backtesting, and live monitoring must call the same feature-store and prediction interfaces; no separate live-only feature logic.

**Major components:**
1. Source fetcher and raw ingestor: pin/fetch Sackmann files, preserve raw rows, checksums, schemas, and source metadata.
2. Domain normalizer: produce ATP-only canonical players, tournaments, matches, rankings, and stats from raw rows.
3. Chronological state builder: iterate matches in deterministic time order, emit pre-match snapshots, then update Elo/form/H2H/stats.
4. Feature store: serve point-in-time differential features by player IDs, context, `as_of_date`, and feature version.
5. Dataset builder: freeze chronological train/validation/test datasets and labels from feature snapshots.
6. Model trainer, calibrator, evaluator, and registry: train baselines/XGBoost, calibrate on disjoint windows, persist artifacts and reports.
7. Backtester: replay predictions and EV rules with timestamped prices or clearly labeled synthetic assumptions.
8. Kalshi adapter: encapsulate authentication, market listing, market details, orderbooks, WebSocket support, retries, and raw snapshots.
9. Market mapper and identity resolver: map Kalshi market payloads to canonical ATP matches and sides, quarantining ambiguity.
10. Pricing/EV engine: derive executable implied probabilities from orderbooks, compute net edge/EV, apply gates, and rank opportunities.
11. Alerting/reporting: surface only audited, threshold-passing opportunities and persist all accepted/rejected decisions.

### Critical Pitfalls

1. **Chronological leakage:** Prevent with one walk-forward feature builder, pre-match snapshots, `as_of_date` APIs, chronological splits, and tests proving future rows do not change historical features.
2. **Accuracy-first modeling:** Prevent by selecting models on log loss, Brier score, ECE, reliability curves, segment stability, and calibrated EV sensitivity, not just accuracy or ROC AUC.
3. **Wrong Kalshi market mapping:** Prevent with canonical player IDs, deterministic candidate matching, side-orientation tests, raw payload storage, confidence states, manual overrides, and `NO_ALERT` for ambiguity.
4. **Non-executable market prices:** Prevent with side-aware orderbook parsing, reciprocal bid/ask mechanics, Decimal math, depth-limited fill assumptions, fees, rounding, freshness checks, and stored snapshots.
5. **Untradable backtests:** Prevent by separating model backtests from market replay backtests, using only observable timestamped prices where available, freezing thresholds before final tests, and labeling synthetic assumptions.

## Implications for Roadmap

Based on research, suggested phase structure:

### Phase 1: Foundation and ATP Data Contracts

**Rationale:** Every later component depends on stable source manifests, schemas, IDs, and scope filters.
**Delivers:** Python project skeleton, config/logging, storage layout, Sackmann source pinning, raw ingestion, schema validation, canonical ATP singles domain tables, source metadata, and quarantine/exclusion rules.
**Addresses:** Sackmann ingestion, dataset validation, ATP-only canonical store, persistence groundwork.
**Avoids:** Scope creep, schema drift, stat/ranking as-of confusion, non-ATP contamination.

### Phase 2: Leakage-Safe Feature Engine

**Rationale:** Feature semantics are the highest-risk architectural dependency and must be locked before modeling.
**Delivers:** Chronological runner, pre-match Elo/surface Elo, rankings, recent form, serve/return aggregates, H2H, match context, differential features, feature snapshots, and leakage tests.
**Uses:** Polars, DuckDB, Parquet, pytest, typed feature schemas.
**Avoids:** Future-data leakage, current-match H2H/stats inclusion, overwritten feature state, sparse-rate overfitting without exposure counts.

### Phase 3: Modeling, Calibration, and Artifact Registry

**Rationale:** Models should consume frozen point-in-time features; calibration must be proven before any EV comparison.
**Delivers:** Chronological datasets, logistic regression and random forest baselines, XGBoost candidate, calibration pipeline, metrics reports, segment diagnostics, model/calibrator registry.
**Addresses:** Calibrated win probabilities, evaluation dashboard/output, reproducible model artifacts.
**Avoids:** Accuracy-only model promotion, random splits, calibration overlap with training/test data.

### Phase 4: Backtesting and EV Decision Core

**Rationale:** The EV engine should be validated in replay before live market monitoring becomes operationally meaningful.
**Delivers:** Prediction replay, simulated decision records, EV formulas, threshold filtering, rejection reasons, ROI/profit/drawdown/sample-size reports, and explicit limitation labels for synthetic market assumptions.
**Addresses:** Backtesting framework, betting metrics, opportunity filtering/ranking logic.
**Avoids:** Untradable backtests, threshold tuning on final test ROI, profitability claims without uncertainty.

### Phase 5: Kalshi Read-Only Market Integration and Snapshot Collection

**Rationale:** Kalshi integration should start after the model/EV contracts exist, but snapshot collection should begin before alerts so future replays have real observations.
**Delivers:** Kalshi REST client wrapper, authentication, market discovery, market detail ingestion, orderbook snapshots, raw payload persistence, retries, API route separation, and read-only credentials/config.
**Addresses:** Kalshi market discovery, market detail/orderbook ingestion, persistent market history.
**Avoids:** SDK churn leakage, live/historical API confusion, missing market audit trail, premature execution surfaces.

### Phase 6: Market Mapping, Executable Pricing, and Live EV Monitor

**Rationale:** Mapping and price execution assumptions are the highest-risk live boundaries; they deserve a separate validation gate before alerts.
**Delivers:** Player alias tables, market-to-match mapping states, confidence scoring, manual review queue, side-orientation tests, side-aware executable pricing, liquidity/freshness checks, live predictions, EV ranking, and shadow-mode monitor.
**Addresses:** Player-name normalization, market-to-match mapping, market probability conversion, liquidity-aware EV.
**Avoids:** Wrong match/player side, fuzzy-only matching, midpoint/last-price EV, stale or thin-market false positives.

### Phase 7: Alerts and Operational Hardening

**Rationale:** Alerts should be the final assembly after model, backtest, Kalshi, mapping, and pricing gates are credible.
**Delivers:** Terminal/persisted alerts first, optional single external channel, alert logs, reason-coded accepted/rejected decisions, monitoring commands, CI/pre-commit quality gates, and documentation of execution boundary.
**Addresses:** Ranked positive-EV opportunity surfacing and operational reproducibility.
**Avoids:** Alert spam, unauditable recommendations, live reliance before shadow evidence, accidental order execution.

### Phase Ordering Rationale

- Data contracts come first because source lineage, ATP scope, and stable IDs underpin features, models, mapping, and backtests.
- Leakage-safe features are separate because they are both central value and the easiest place to invalidate the entire product.
- Modeling follows frozen features; calibration follows model training; EV follows calibrated probabilities.
- Backtesting precedes live reliance so the same decision code can be exercised before alerts.
- Kalshi is staged as read-only ingestion, then mapping/pricing, then monitoring/alerts. This prevents live integration pressure from creating ad hoc feature or EV paths.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1:** Sackmann licensing/commercial-use implications, exact v1 handling of retirements, walkovers, qualifiers, incomplete matches, ranking coverage windows, and modern-era cutoff.
- **Phase 4:** Historical Kalshi ATP market data availability, realistic replay assumptions, fees, no-fill handling, and statistical confidence reporting.
- **Phase 5:** Current Kalshi auth behavior, generated SDK fit, live vs historical endpoint boundaries, rate limits, and tennis market availability.
- **Phase 6:** Kalshi ATP market naming/settlement conventions, side wording, same-day match ambiguity, and executable price calculation from actual payloads.

Phases with standard patterns:
- **Phase 2:** Walk-forward state builders, feature snapshots, and leakage tests are well-understood, though domain tests must be rigorous.
- **Phase 3:** scikit-learn/XGBoost chronological modeling and calibration patterns are well documented.
- **Phase 7:** CLI alerts, persistence, logging, CI, and pre-commit are standard once upstream contracts are stable.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Python/Polars/DuckDB/scikit-learn/XGBoost/pytest choices are well matched to tabular, local, reproducible modeling; Kalshi SDK choice is MEDIUM because the wrapper must be validated against live API behavior. |
| Features | HIGH | V1 capabilities are strongly grounded in PROJECT.md and common tennis modeling needs; external alert channel details can be decided later. |
| Architecture | MEDIUM-HIGH | The persistence boundaries and build order are robust; exact Kalshi tennis taxonomy and historical market data behavior require phase validation. |
| Pitfalls | MEDIUM-HIGH | Leakage, calibration, mapping, executable pricing, and backtest validity are well-supported risks; impact is high enough to encode as gates even where implementation details remain uncertain. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **Kalshi ATP market taxonomy:** Validate live/demo market titles, event/series filters, settlement wording, and side orientation before final mapping requirements.
- **Historical Kalshi market depth:** Confirm whether enough historical ATP market snapshots/depth exist for true replay; otherwise label v1 EV backtests as synthetic or snapshot-limited.
- **Sackmann license and intended use:** Confirm commercial/non-commercial constraints before production or monetized deployment.
- **Incomplete/retired/walkover matches:** Specify inclusion/exclusion rules early because labels, stats, and Kalshi settlement mapping depend on them.
- **Modern modeling window:** Decide whether to restrict training to eras with acceptable ranking and MatchStats coverage.
- **Alert channel:** Choose whether v1 external alerting is email, SMS, or terminal/persisted-only after shadow-mode evidence.

## Sources

### Primary (HIGH confidence)
- `.planning/PROJECT.md` — project constraints, active requirements, out-of-scope items, and core value.
- Jeff Sackmann `tennis_atp` repository — ATP historical data source, rankings, players, match results, stats, and license context: https://github.com/JeffSackmann/tennis_atp
- Kalshi API documentation — market listing, market detail, orderbooks, API keys/auth, WebSocket, historical data, fees, and settlement: https://docs.kalshi.com/
- scikit-learn documentation — chronological split tooling and probability calibration semantics: https://scikit-learn.org/stable/

### Secondary (MEDIUM confidence)
- `STACK.md` — package/version recommendations and alternatives.
- `FEATURES.md` — table-stakes features, differentiators, anti-features, and acceptance signals.
- `ARCHITECTURE.md` — pipeline shape, component boundaries, persistence layers, and build order.
- `PITFALLS.md` — phase gates and domain-specific failure modes.
- Walsh and Joshi, "Machine learning for sports betting: should model selection be based on accuracy or calibration?" — calibration-first betting model selection context: https://arxiv.org/abs/2303.06021

---
*Research completed: 2026-06-16*
*Ready for roadmap: yes*
