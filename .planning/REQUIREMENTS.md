# Requirements: ATP Tennis Prediction and Kalshi EV Detection System

**Defined:** 2026-06-16
**Core Value:** Produce trustworthy, leakage-free ATP match win probabilities and convert them into actionable Kalshi-only positive expected value signals.

## v1 Requirements

Requirements for the initial release. Each maps to a roadmap phase.

### Foundation

- [ ] **FND-01**: Developer can run a Python project with pinned dependencies, typed source layout, linting, formatting, tests, logging, and configuration.
- [ ] **FND-02**: Developer can fetch or load Jeff Sackmann `tennis_atp` ATP source files with source commit, checksum, and license/attribution metadata recorded.
- [ ] **FND-03**: System validates expected Sackmann match, ranking, player, tournament, and match-stat schemas before deriving data.
- [ ] **FND-04**: System creates canonical ATP-only player, tournament, match, ranking, and match-stat tables with stable IDs and source lineage.
- [ ] **FND-05**: System rejects, ignores, or quarantines out-of-scope tours and match types according to documented ATP-only v1 rules.
- [ ] **FND-06**: System documents v1 handling of retirements, walkovers, missing stats, qualifiers, and incomplete matches.

### Feature Engine

- [x] **FEAT-01**: System builds features by iterating matches chronologically and emitting pre-match snapshots before updating post-match state.
- [x] **FEAT-02**: System maintains overall Elo and hard/clay/grass surface Elo ratings for ATP players.
- [x] **FEAT-03**: System computes ranking, ranking-points, and ranking-change features using only rankings available before match date.
- [x] **FEAT-04**: System computes recent-form features for last 5, 10, and 20 prior matches.
- [x] **FEAT-05**: System computes serve and return aggregates from prior matches where Sackmann match stats are available.
- [x] **FEAT-06**: System computes prior-only head-to-head features for two players.
- [x] **FEAT-07**: System computes match-context features including surface, tournament level, round, best-of, and days rest.
- [x] **FEAT-08**: System creates player A versus player B differential features for ranking, Elo, surface Elo, form, serve, return, H2H, and rest.
- [x] **FEAT-09**: Unit tests prove Elo, ranking, recent form, H2H, and aggregate features exclude the current and future matches.

### Modeling

- [x] **MOD-01**: System creates frozen chronological train, validation, and test datasets without random shuffling.
- [x] **MOD-02**: System trains a logistic regression benchmark model.
- [x] **MOD-03**: System trains a random forest benchmark model.
- [x] **MOD-04**: System trains an XGBoost production-candidate model.
- [x] **MOD-05**: System calibrates model probabilities using a disjoint chronological validation period.
- [x] **MOD-06**: System evaluates models with accuracy, ROC AUC, log loss, Brier score, calibration curve, and expected calibration error.
- [x] **MOD-07**: System reports segment diagnostics by surface, tournament level, time period, ranking band, and confidence bucket.
- [x] **MOD-08**: System persists model artifacts with source version, feature version, split boundaries, model parameters, calibrator, and metrics.

### Backtesting

- [ ] **BKT-01**: System replays historical predictions using frozen chronological model artifacts and feature snapshots.
- [ ] **BKT-02**: System implements market probability, edge, expected value, confidence, liquidity, and threshold filtering as reusable decision logic.
- [ ] **BKT-03**: System records accepted and rejected opportunities with reason codes.
- [ ] **BKT-04**: System calculates ROI, profit curve, win rate, average edge, max drawdown, sample size, and backtest provenance.
- [ ] **BKT-05**: System labels every market/EV backtest as actual Kalshi historical data, collected snapshot replay, or synthetic/proxy assumptions.
- [ ] **BKT-06**: System prevents profitability claims unless sample size, uncertainty, and data provenance are included in the report.

### Kalshi

- [ ] **KAL-01**: System provides a Kalshi-only read client with authenticated market listing, market detail, and orderbook retrieval.
- [ ] **KAL-02**: System persists raw Kalshi market, market-detail, and orderbook snapshots with timestamps and request metadata.
- [ ] **KAL-03**: System handles Kalshi pagination, retries, rate-limit/backoff behavior, and closed/settled market states.
- [ ] **KAL-04**: System keeps Kalshi SDK/API payloads behind project-owned interfaces so business logic consumes normalized DTOs.
- [ ] **KAL-05**: System can run a read-only snapshot collection job without placing or preparing orders.

### Market Mapping and EV

- [ ] **MKT-01**: System normalizes player names from Sackmann and Kalshi into deterministic candidate identities.
- [ ] **MKT-02**: System supports manual player alias overrides with auditable source and timestamp metadata.
- [ ] **MKT-03**: System maps Kalshi ATP markets to canonical ATP matches and player sides with matched, ambiguous, unmatched, and excluded states.
- [ ] **MKT-04**: System refuses to score ambiguous or unmatched Kalshi markets.
- [ ] **MKT-05**: System converts Kalshi yes/no prices and orderbook depth into a recorded market probability source.
- [ ] **MKT-06**: System calculates executable edge and expected value with price source, liquidity, freshness, and fee/slippage assumptions recorded.
- [ ] **MKT-07**: System generates live or shadow-mode predictions by reusing the same feature and model interfaces used in training/backtesting.
- [ ] **MKT-08**: System ranks opportunities by expected value, edge, liquidity, confidence, and configured thresholds.

### Alerts and Operations

- [ ] **OPS-01**: System emits terminal and persisted opportunity reports containing match, market ticker, model probability, market probability, edge, expected value, liquidity, mapping confidence, and recommendation.
- [ ] **OPS-02**: System supports configurable polling interval, thresholds, model artifact selection, storage paths, and alert channel settings.
- [ ] **OPS-03**: System logs ingestion, feature generation, training, backtesting, Kalshi polling, mapping, EV filtering, and alert decisions with enough context for audit.
- [ ] **OPS-04**: System provides CLI commands for ingestion, feature build, training, evaluation, backtesting, Kalshi snapshot collection, live scan, and opportunity reporting.
- [ ] **OPS-05**: System includes CI or local quality gates for tests, linting, formatting, typing, and critical leakage/EV logic.
- [ ] **OPS-06**: System documentation explains setup, data sources, Kalshi configuration, pipeline commands, output files, backtest limitations, and v1 scope boundaries.

## v2 Requirements

Deferred to future releases. Tracked but not in current roadmap.

### Product Surface

- **PROD-01**: User can review opportunities and model diagnostics in a web dashboard.
- **PROD-02**: User can manage manual player alias review through a UI instead of flat files or CLI.
- **PROD-03**: User can compare model performance across saved experiment runs interactively.

### Data Expansion

- **DATA-01**: System can evaluate whether lower-tier ATP-adjacent data improves predictions without contaminating v1 product scope.
- **DATA-02**: System can incorporate additional official or licensed pre-match signals after leakage and licensing review.

### Alerts

- **ALRT-01**: System can support additional external alert channels after terminal/persisted reports prove useful.
- **ALRT-02**: System can add alert throttling, escalation, and digest modes.

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| WTA, doubles, Challenger, ITF, Futures, exhibitions, and team events | User scope is ATP only and v1 data/model assumptions are ATP singles-specific. |
| Betting platforms other than Kalshi | User scope is Kalshi only; other venues add market and account abstractions that dilute v1. |
| Automated trade execution in v1 | v1 must stop at EV detection, ranking, recommendation, alerts, and evidence. |
| Portfolio management, bankroll automation, and sizing recommendations in v1 | These depend on validated edge persistence and execution policy outside the initial system. |
| In-play or point-by-point prediction | The project is based on pre-match historical ATP data and Kalshi market monitoring. |
| LLM-first player matching | Market mapping must be deterministic, auditable, and reject ambiguity. |
| Random shuffled validation | Temporal leakage would invalidate prediction and EV metrics. |
| Positive ROI claims without sample size and provenance | The spec requires statistical significance and backtest evidence. |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FND-01 | Phase 1 | Pending |
| FND-02 | Phase 1 | Pending |
| FND-03 | Phase 1 | Pending |
| FND-04 | Phase 1 | Pending |
| FND-05 | Phase 1 | Pending |
| FND-06 | Phase 1 | Pending |
| FEAT-01 | Phase 2 | Complete |
| FEAT-02 | Phase 2 | Complete |
| FEAT-03 | Phase 2 | Complete |
| FEAT-04 | Phase 2 | Complete |
| FEAT-05 | Phase 2 | Complete |
| FEAT-06 | Phase 2 | Complete |
| FEAT-07 | Phase 2 | Complete |
| FEAT-08 | Phase 2 | Complete |
| FEAT-09 | Phase 2 | Complete |
| MOD-01 | Phase 3 | Complete |
| MOD-02 | Phase 3 | Complete |
| MOD-03 | Phase 3 | Complete |
| MOD-04 | Phase 3 | Complete |
| MOD-05 | Phase 3 | Complete |
| MOD-06 | Phase 3 | Complete |
| MOD-07 | Phase 3 | Complete |
| MOD-08 | Phase 3 | Complete |
| BKT-01 | Phase 4 | Pending |
| BKT-02 | Phase 4 | Pending |
| BKT-03 | Phase 4 | Pending |
| BKT-04 | Phase 4 | Pending |
| BKT-05 | Phase 4 | Pending |
| BKT-06 | Phase 4 | Pending |
| KAL-01 | Phase 5 | Pending |
| KAL-02 | Phase 5 | Pending |
| KAL-03 | Phase 5 | Pending |
| KAL-04 | Phase 5 | Pending |
| KAL-05 | Phase 5 | Pending |
| MKT-01 | Phase 6 | Pending |
| MKT-02 | Phase 6 | Pending |
| MKT-03 | Phase 6 | Pending |
| MKT-04 | Phase 6 | Pending |
| MKT-05 | Phase 6 | Pending |
| MKT-06 | Phase 6 | Pending |
| MKT-07 | Phase 6 | Pending |
| MKT-08 | Phase 6 | Pending |
| OPS-01 | Phase 7 | Pending |
| OPS-02 | Phase 7 | Pending |
| OPS-03 | Phase 7 | Pending |
| OPS-04 | Phase 7 | Pending |
| OPS-05 | Phase 7 | Pending |
| OPS-06 | Phase 7 | Pending |

**Coverage:**

- v1 requirements: 48 total
- Mapped to phases: 48
- Unmapped: 0

---
*Requirements defined: 2026-06-16*
*Last updated: 2026-06-16 after initial definition*
