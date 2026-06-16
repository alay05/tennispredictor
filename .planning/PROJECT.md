# ATP Tennis Prediction and Kalshi EV Detection System

## What This Is

This project is a production-grade ATP tennis prediction platform that uses historical match data to generate calibrated match win probabilities, then compares those probabilities against live Kalshi market prices to identify positive expected value opportunities. It is for building and operating an end-to-end quantitative workflow: ingest ATP data, engineer leakage-safe features, train and calibrate models, monitor Kalshi markets, rank opportunities, and support decisions with backtesting evidence.

The initial specification is `project-outline.yaml`; it is treated as the source project spec for initialization.

## Core Value

Produce trustworthy, leakage-free ATP match win probabilities and convert them into actionable Kalshi-only positive expected value signals.

## Requirements

### Validated

(None yet - ship to validate)

### Active

- [ ] Ingest ATP historical match and ranking data from Jeff Sackmann's `tennis_atp` repository.
- [ ] Build chronological, leakage-safe match features using only information available before match start.
- [ ] Maintain overall and surface-specific Elo ratings for ATP players.
- [ ] Train baseline and production models that predict ATP match winners and calibrated win probabilities.
- [ ] Evaluate predictive quality with accuracy, ROC AUC, log loss, Brier score, and calibration metrics.
- [ ] Backtest model-driven betting decisions before any live betting use.
- [ ] Integrate with Kalshi APIs for ATP market discovery, market pricing, and orderbook liquidity.
- [ ] Normalize player names and map Kalshi markets to ATP matches.
- [ ] Calculate market implied probability, model edge, expected value, and recommended bet decisions.
- [ ] Rank and alert on positive expected value opportunities using configurable thresholds.
- [ ] Persist historical matches, ratings, predictions, live markets, opportunities, and backtest outputs.
- [ ] Provide a reproducible, typed, logged, configurable training and prediction pipeline with unit tests for critical logic.

### Out of Scope

- WTA, Challenger, ITF, doubles, or non-ATP tours - the project scope is ATP only.
- Betting platforms other than Kalshi - all market integration and EV comparison is Kalshi only.
- Data sources replacing Jeff Sackmann's ATP datasets as the primary historical source - the project depends on `tennis_atp` for v1 history and rankings.
- Automated trade execution - v1 identifies opportunities and recommendations; execution can be considered only after prediction, calibration, market mapping, and backtesting are validated.
- Random shuffled model evaluation - all training, validation, testing, Elo, form, and head-to-head calculations must be chronological.
- Using future match, ranking, or market information in model features - leakage prevention is a hard project constraint.

## Context

The project starts from `project-outline.yaml`, which defines an ATP-only machine learning and market-monitoring system. The primary historical data source is Jeff Sackmann's ATP tennis dataset, including match results, player rankings, tournament metadata, surfaces, scores, and match statistics. The live market source is Kalshi, with required workflows for listing markets, retrieving market details, and reading orderbooks.

The intended model stack includes logistic regression as a benchmark, random forest as a common tennis-prediction baseline, and XGBoost as the production model candidate. Models must output calibrated probabilities, not just winners. Evaluation must include predictive metrics, calibration metrics, and betting metrics.

The feature strategy emphasizes differential features between two players: ranking differences, Elo differences, surface Elo differences, recent form differences, serve/return differences, hold and break differences, head-to-head context, tournament context, round, and days rest. Elo and recent form features must be recalculated chronologically from prior matches only.

The live workflow polls Kalshi markets, normalizes player names, maps markets to matches, generates model predictions, converts yes/no pricing to implied probability, calculates edge and expected value, filters by minimum edge, confidence, and liquidity, then ranks and alerts on opportunities.

## Constraints

- **Scope**: ATP only - avoid expanding requirements, data models, or market matching to WTA or other tours.
- **Market platform**: Kalshi only - all live pricing, orderbook, and opportunity logic targets Kalshi markets.
- **Primary data source**: Jeff Sackmann `tennis_atp` - historical ingestion should be designed around this repository's CSV files and schema drift.
- **Leakage prevention**: Chronological feature computation only - rankings, Elo, recent form, head-to-head, and aggregate stats must exclude future matches.
- **Probability quality**: Calibrated probabilities are required - the system cannot stop at classification accuracy.
- **Backtesting**: Profitability claims require replay or simulation evidence - live alerts should not be treated as validated until backtests support them.
- **Engineering quality**: Code must be modular, typed, logged, configurable, reproducible, and covered by focused unit tests for critical logic.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Scope is ATP only | The user explicitly constrained the project to ATP and the data source is ATP-specific. | - Pending |
| Jeff Sackmann `tennis_atp` is the primary historical source | The YAML identifies it as the primary source for matches, rankings, stats, surfaces, and tournament context. | - Pending |
| Kalshi is the only betting/market integration | The user explicitly constrained market integration to Kalshi only. | - Pending |
| Chronological modeling is mandatory | Tennis prediction features are highly leakage-prone; the spec requires no future information. | - Pending |
| XGBoost is the primary production model candidate | The YAML identifies logistic regression and random forest as baselines and XGBoost as production. | - Pending |
| Live betting starts as EV detection and alerting, not execution | This keeps v1 focused on model quality, market mapping, backtesting, and actionable recommendations before trading automation. | - Pending |
| Workflow mode is YOLO with standard granularity and parallel execution | The user selected these GSD project settings during initialization. | - Pending |
| Planning documents are committed to git | The user selected tracked planning docs. | - Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `$gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `$gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-16 after initialization*
