# Roadmap: ATP Tennis Prediction and Kalshi EV Detection System

## Overview

v1 builds an ATP-only, leakage-safe prediction and Kalshi EV detection workflow from the ground up: pin and normalize Jeff Sackmann `tennis_atp` data, create chronological pre-match features, train calibrated models, validate EV logic with backtests, ingest Kalshi markets read-only, map markets to ATP matches, rank executable opportunities, and emit auditable alerts. v1 stops at EV detection, ranking, recommendation, evidence, and alerts; it does not include WTA, other betting platforms, or automated trade execution.

## Current Milestone

**v1.0 MVP** - Phases 1-7 deliver the first complete ATP-only prediction and Kalshi-only EV detection workflow, from source ingestion through audited opportunity reports.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation and ATP Data Contracts** - Establish the typed project, Sackmann source lineage, ATP-only scope rules, and canonical data tables.
- [x] **Phase 2: Leakage-Safe Feature Engine** - Produce chronological pre-match feature snapshots with leakage tests as a phase gate. (completed 2026-06-18)
- [ ] **Phase 3: Modeling, Calibration, and Artifact Registry** - Train benchmark and production-candidate models with calibrated probabilities and reproducible artifacts.
- [ ] **Phase 4: Backtesting and EV Decision Core** - Replay predictions and EV decisions with provenance-aware betting evidence.
- [ ] **Phase 5: Kalshi Read-Only Market Integration** - Collect and persist Kalshi-only market, detail, and orderbook snapshots without execution surfaces.
- [ ] **Phase 6: Market Mapping, Executable Pricing, and Live EV Monitor** - Map ATP markets, compute executable EV, and rank live or shadow-mode opportunities.
- [ ] **Phase 7: Alerts and Operational Hardening** - Deliver auditable opportunity reports, CLI operations, quality gates, and v1 documentation.

## Phase Details

### Phase 1: Foundation and ATP Data Contracts

**Goal:** Developer can run a reproducible ATP-only data foundation with pinned Sackmann sources, validated schemas, canonical tables, and documented v1 data rules.
**Depends on:** Nothing (first phase)
**Requirements:** FND-01, FND-02, FND-03, FND-04, FND-05, FND-06
**Success Criteria** (what must be TRUE):

  1. Developer can install dependencies, run linting, formatting, typing, tests, and load configuration from the project command line.
  2. Developer can fetch or load Jeff Sackmann `tennis_atp` files and inspect recorded commit, checksum, license, attribution, and source lineage metadata.
  3. System validates expected ATP match, ranking, player, tournament, and match-stat schemas before derived data is created.
  4. System produces canonical ATP-only player, tournament, match, ranking, and match-stat tables with stable IDs while excluding or quarantining out-of-scope data.
  5. Developer can inspect documented v1 rules for retirements, walkovers, missing stats, qualifiers, incomplete matches, and ATP-only scope boundaries.

**Plans:** 4 plans

Plans:

- [x] 01-01-PLAN.md — Python project skeleton, dependency gate, configuration, logging, and quality tooling
- [x] 01-02-PLAN.md — Sackmann source acquisition, immutable snapshot manifest, checksums, and attribution
- [x] 01-03-PLAN.md — Schema validation and ATP-only quarantine rules
- [x] 01-04-PLAN.md — Canonical domain tables, deterministic IDs, and v1 data-handling rules

### Phase 2: Leakage-Safe Feature Engine

**Goal:** System can create point-in-time ATP pre-match feature snapshots by processing matches chronologically and proving future data cannot affect historical features.
**Mode:** mvp
**Depends on:** Phase 1
**Requirements:** FEAT-01, FEAT-02, FEAT-03, FEAT-04, FEAT-05, FEAT-06, FEAT-07, FEAT-08, FEAT-09
**Success Criteria** (what must be TRUE):

  1. Developer can build features through a chronological runner that emits each pre-match snapshot before updating post-match state.
  2. System exposes overall Elo, hard/clay/grass surface Elo, ranking, ranking-points, ranking-change, recent-form, serve/return, H2H, match-context, and rest features using only prior data.
  3. System creates player A versus player B differential feature rows for model training and prediction.
  4. Leakage tests fail if Elo, ranking, recent form, H2H, or aggregate features include the current match or future matches.
  5. Developer can inspect persisted feature snapshots with feature version, match identity, player sides, and as-of context.

**Plans:** 5/5 plans complete
Plans:
**Wave 1**

- [x] 02-01-PLAN.md — Chronological runner with ranking-as-of, cohort ordering, and minimal differential rows

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 02-02-PLAN.md — Elo, surface Elo, recent-form, rest, and audit-ready state transitions

**Wave 3** *(blocked on Wave 2 completion)*

- [x] 02-03-PLAN.md — Serve/return aggregates, head-to-head state, sparse-data metadata, and expanded differentials

**Wave 4** *(blocked on Wave 3 completion)*

- [x] 02-04-PLAN.md — Feature persistence tables and invariant leakage gate

### Phase 3: Modeling, Calibration, and Artifact Registry

**Goal:** Developer can train, calibrate, evaluate, and persist ATP match models that produce trustworthy chronological win probabilities.
**Mode:** mvp
**Depends on:** Phase 2
**Requirements:** MOD-01, MOD-02, MOD-03, MOD-04, MOD-05, MOD-06, MOD-07, MOD-08
**Success Criteria** (what must be TRUE):

  1. Developer can create frozen chronological train, validation, and test datasets without random shuffling.
  2. Developer can train logistic regression and random forest baselines plus an XGBoost production-candidate model on the same feature contracts.
  3. System calibrates model probabilities on a disjoint chronological validation period and reports calibrated test-set probabilities.
  4. Developer can inspect accuracy, ROC AUC, log loss, Brier score, calibration curve, expected calibration error, and segment diagnostics.
  5. System persists model artifacts with source version, feature version, split boundaries, model parameters, calibrator, and metrics.

**Plans:** 3/4 plans executed

Plans:

- [x] 03-01-PLAN.md — Frozen modeling dataset materialization and chronological split manifests
- [x] 03-02-PLAN.md — Approved ML dependency bootstrap and baseline model training
- [x] 03-03-PLAN.md — Calibrated XGBoost candidate and probability metric surface
- [ ] 03-04-PLAN.md — Filesystem-first artifact registry and segment diagnostics

### Phase 4: Backtesting and EV Decision Core

**Goal:** System can replay predictions and EV decisions with reusable decision logic and evidence that prevents unsupported profitability claims.
**Mode:** mvp
**Depends on:** Phase 3
**Requirements:** BKT-01, BKT-02, BKT-03, BKT-04, BKT-05, BKT-06
**Success Criteria** (what must be TRUE):

  1. Developer can replay historical model predictions using frozen chronological artifacts and persisted feature snapshots.
  2. System applies reusable market probability, edge, expected value, confidence, liquidity, and threshold filtering logic to accepted and rejected opportunities.
  3. Developer can inspect reason-coded accepted and rejected opportunity records.
  4. Backtest reports show ROI, profit curve, win rate, average edge, max drawdown, sample size, and provenance.
  5. System labels every EV backtest as actual Kalshi historical data, collected snapshot replay, or synthetic/proxy assumptions before any profitability statement is shown.

**Plans:** 3 plans

Plans:

- [ ] 04-01: Prediction replay and frozen-artifact backtest harness
- [ ] 04-02: EV decision logic, filters, and reason-coded records
- [ ] 04-03: Betting metrics, provenance labels, and profitability claim guardrails

### Phase 5: Kalshi Read-Only Market Integration

**Goal:** System can collect Kalshi-only market data through project-owned read interfaces and persist raw snapshots without placing or preparing orders.
**Mode:** mvp
**Depends on:** Phase 4
**Requirements:** KAL-01, KAL-02, KAL-03, KAL-04, KAL-05
**Success Criteria** (what must be TRUE):

  1. Operator can configure authenticated Kalshi read access for market listing, market detail, and orderbook retrieval.
  2. System persists raw Kalshi market, market-detail, and orderbook snapshots with timestamps and request metadata.
  3. System handles Kalshi pagination, retries, rate-limit/backoff behavior, and closed or settled market states.
  4. Business logic consumes normalized project DTOs instead of Kalshi SDK or API payloads directly.
  5. Operator can run a read-only snapshot collection job that cannot place, stage, or prepare orders.

**Plans:** 3 plans

Plans:

- [ ] 05-01: Kalshi read client, authentication, and normalized DTO interfaces
- [ ] 05-02: Snapshot persistence for markets, details, orderbooks, and request metadata
- [ ] 05-03: Pagination, retry, rate-limit, market-state handling, and read-only job guardrails

### Phase 6: Market Mapping, Executable Pricing, and Live EV Monitor

**Goal:** Operator can map Kalshi ATP markets to canonical matches, compute executable EV from fresh price sources, and rank live or shadow-mode opportunities.
**Mode:** mvp
**Depends on:** Phase 5
**Requirements:** MKT-01, MKT-02, MKT-03, MKT-04, MKT-05, MKT-06, MKT-07, MKT-08
**Success Criteria** (what must be TRUE):

  1. Operator can normalize Sackmann and Kalshi player names, apply auditable alias overrides, and see matched, ambiguous, unmatched, or excluded market states.
  2. System refuses to score ambiguous or unmatched Kalshi markets.
  3. System records Kalshi yes/no price source, orderbook depth, freshness, liquidity, fee, and slippage assumptions used for market probability and executable EV.
  4. Live or shadow-mode predictions reuse the same feature and model interfaces used for training and backtesting.
  5. Operator can view ranked opportunities ordered by expected value, edge, liquidity, confidence, and configured thresholds.

**Plans:** 4 plans

Plans:

- [ ] 06-01: Deterministic player normalization and auditable alias overrides
- [ ] 06-02: Kalshi market-to-ATP match mapping states and ambiguity rejection
- [ ] 06-03: Executable price, implied probability, edge, EV, liquidity, and freshness calculations
- [ ] 06-04: Live or shadow-mode scan and ranked opportunity monitor

### Phase 7: Alerts and Operational Hardening

**Goal:** Operator can run the full ATP-to-Kalshi EV workflow through audited CLI commands, quality gates, persisted reports, and documented v1 boundaries.
**Mode:** mvp
**Depends on:** Phase 6
**Requirements:** OPS-01, OPS-02, OPS-03, OPS-04, OPS-05, OPS-06
**Success Criteria** (what must be TRUE):

  1. Operator can receive terminal and persisted opportunity reports with match, ticker, model probability, market probability, edge, expected value, liquidity, mapping confidence, and recommendation.
  2. Operator can configure polling interval, thresholds, model artifact selection, storage paths, and alert channel settings.
  3. System logs ingestion, feature generation, training, backtesting, Kalshi polling, mapping, EV filtering, and alert decisions with audit context.
  4. Operator can run CLI commands for ingestion, feature build, training, evaluation, backtesting, Kalshi snapshot collection, live scan, and opportunity reporting.
  5. Developer can run CI or local quality gates for tests, linting, formatting, typing, critical leakage logic, and EV logic, and can read documentation for setup, data sources, Kalshi configuration, pipeline commands, output files, backtest limitations, and v1 scope boundaries.

**Plans:** 4 plans

Plans:

- [ ] 07-01: Opportunity reports and configurable alert settings
- [ ] 07-02: Audit logging across pipeline, market, mapping, EV, and alert decisions
- [ ] 07-03: End-to-end CLI commands and operational configuration
- [ ] 07-04: Quality gates and v1 documentation

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation and ATP Data Contracts | 4/4 | Complete | 2026-06-16 |
| 2. Leakage-Safe Feature Engine | 5/5 | Complete    | 2026-06-18 |
| 3. Modeling, Calibration, and Artifact Registry | 3/4 | In Progress|  |
| 4. Backtesting and EV Decision Core | 0/3 | Not started | - |
| 5. Kalshi Read-Only Market Integration | 0/3 | Not started | - |
| 6. Market Mapping, Executable Pricing, and Live EV Monitor | 0/4 | Not started | - |
| 7. Alerts and Operational Hardening | 0/4 | Not started | - |
