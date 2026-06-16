# Feature Landscape

**Domain:** ATP-only tennis match prediction and Kalshi-only expected value detection
**Project:** ATP Tennis Prediction and Kalshi EV Detection System
**Researched:** 2026-06-16
**Overall confidence:** HIGH for source-spec requirements; MEDIUM for external ecosystem expectations

## Scope Guardrails

V1 should build a disciplined research-to-alerting workflow, not a broad betting product. Preserve these constraints throughout requirements:

- **Tour:** ATP singles only. Exclude WTA, doubles, Challenger, ITF, junior, exhibition, and team-tennis expansion from v1 product scope.
- **Historical source:** Jeff Sackmann `tennis_atp` remains the primary historical source for matches, rankings, player biographical fields, tournament metadata, and match statistics.
- **Market source:** Kalshi only. Do not add sportsbooks, exchanges, odds aggregators, or non-Kalshi market abstractions in v1.
- **Action boundary:** Detect, rank, and alert on opportunities. Do not execute trades in v1.
- **Model boundary:** Chronological, leakage-safe features and calibrated win probabilities are required before any EV signal is considered trustworthy.

## Table Stakes

Features users expect. Missing = product feels incomplete or produces untrusted signals.

| Feature | Why Expected | Complexity | Dependencies | Notes |
|---------|--------------|------------|--------------|-------|
| Jeff Sackmann ATP data ingestion | The source spec defines `tennis_atp` as the primary historical dataset; prediction quality starts with clean historical matches and rankings. | Med | None | Ingest annual ATP singles match CSVs, rankings, player metadata, and data dictionary assumptions. Treat doubles, qualifiers, futures, and challengers as excluded unless explicitly used for research outside v1 product scope. |
| Dataset validation and schema drift checks | The Sackmann repo includes many annual CSV files and known missingness; silent column or data-quality drift can corrupt features. | Med | Data ingestion | Validate expected columns, date parsing, surfaces, tourney levels, player ids, rankings, and missing stat rates. Fail loudly on incompatible changes. |
| ATP-only canonical match store | Downstream features, training, backtests, predictions, and market mapping need stable match ids and normalized player identities. | Med | Data ingestion, validation | Persist matches, players, rankings, and tournament context with source lineage. Store winner/loser source rows and a neutral player A/player B training view. |
| Chronological train/validation/test split | Random shuffled evaluation is explicitly out of scope and would overstate performance in a time-dependent sports model. | Low | Canonical match store | Use chronological 70/15/15 split from the source spec. Ensure feature state is built only from prior matches. |
| Leakage-safe feature generation | The core system value depends on probabilities using only information available before match start. | High | Canonical match store, chronological split | Every feature builder must accept an as-of date/match boundary. Include tests for rankings, Elo, recent form, head-to-head, and aggregate stats. |
| Overall Elo ratings | Elo is required by the source spec and is a standard baseline for tennis prediction. | Med | Chronological match order | Maintain pre-match and post-match ratings. Persist rating snapshots for reproducibility and debugging. |
| Surface-specific Elo ratings | Tennis performance varies by hard, clay, and grass; the spec calls out surface Elo as a core feature. | Med | Overall Elo, surface normalization | Generate hard/clay/grass ratings and pre-match deltas. Handle missing/unknown surfaces explicitly. |
| Ranking and ranking-points features | Rankings and ranking points are available in the primary dataset and are core predictive inputs. | Low | Canonical match store | Use current rank, ranking points, 30-day change where data allows, and pairwise differences. Respect ranking availability dates. |
| Recent form features | The spec requires last 5/10/20 win percentage and similar short-horizon form signals. | Med | Chronological feature store | Compute only from previous matches. Use minimum-sample handling and missing indicators where needed. |
| Serve and return performance features | Sackmann stats include integer totals that support serve/return rates for many tour-level matches. | Med | Match stats validation, chronological aggregation | Convert totals into ace rate, double-fault rate, first-serve percentage, service points won, return points won, hold proxy, break proxy where data supports it. Track missing stats by era and match type. |
| Head-to-head features | The source spec includes h2h wins/losses/win percentage. | Low | Chronological match store | Compute prior-only h2h and surface-specific variants only if easy; avoid overweighting sparse h2h samples. |
| Match context features | Tournament level, round, surface, best-of, and days rest affect match difficulty and player state. | Med | Canonical match store, player schedule history | Include tournament level, round, surface, best-of, days rest, and optionally tournament week context. |
| Differential feature builder | The spec emphasizes pairwise deltas as the most important modeling representation. | Med | Player-level feature builders | Create rank, points, Elo, surface Elo, recent form, serve, return, break, and rest differences for player A vs player B. |
| Baseline logistic regression model | A simple calibrated benchmark is needed to prove that advanced models add value. | Low | Training dataset | Use as a sanity check and monitoring baseline. |
| Random forest baseline | The source spec requests random forest as a common tennis-prediction baseline. | Low | Training dataset | Useful as a nonlinear benchmark, but should not be the only production candidate. |
| XGBoost production candidate | The source spec names XGBoost as the primary production model candidate. | Med | Training dataset, baselines | Tune conservatively against validation log loss/Brier score, not just accuracy. |
| Probability calibration | EV detection needs calibrated probabilities, not just classification accuracy. | Med | Model training, validation predictions | Include calibration curve, expected calibration error, Brier score, and calibrators such as Platt/isotonic only if validation data supports them. |
| Model evaluation dashboard/output | Users need evidence before trusting predictions or EV signals. | Med | Trained models, calibration | Report accuracy, ROC AUC, log loss, Brier score, calibration metrics, and segment breakdowns by surface/tournament level/time period. |
| Reproducible model artifact registry | Live prediction and backtesting must know exactly which data, features, model, and calibration were used. | Med | Training pipeline | Persist model metadata, training window, feature version, calibration method, metrics, and artifact path. |
| Kalshi market discovery | The spec requires list-markets style polling for live ATP markets. | Med | Kalshi client credentials/config | Use Kalshi market endpoints with status/time filters and pagination. Store raw market snapshots for auditability. |
| Kalshi market detail ingestion | Opportunity scoring needs current yes/no prices, volume/open interest, close times, rules, and settlement context. | Med | Market discovery | Pull market details by ticker. Prefer current fields such as yes/no bid/ask dollars and fixed-point volume/count fields. |
| Kalshi orderbook ingestion | Liquidity-aware EV detection needs current depth, not only top-line prices. | Med | Market detail ingestion | Kalshi orderbook returns yes and no bid sides; derive executable proxies carefully from binary-market equivalence. |
| Player-name normalization | Kalshi market text must be mapped to Sackmann player identities. | High | Canonical player store, market ingestion | Build deterministic normalization plus manual override table. Store match confidence and unresolved cases. |
| Market-to-match mapping | EV is meaningless unless a Kalshi market maps to the correct ATP match and player side. | High | Name normalization, ATP schedule/match candidates, market detail ingestion | Require auditable mapping status: matched, ambiguous, unmatched, excluded. Do not score ambiguous markets. |
| Live prediction service/job | Once a market maps to a match, the system must generate the current model probability. | Med | Model artifact registry, feature generation, market-to-match mapping | Reuse the same feature code as training with an as-of boundary. Store prediction timestamp and model version. |
| Market implied probability conversion | EV comparison requires converting Kalshi prices into probability-like market estimates. | Low | Market detail/orderbook ingestion | Start with yes price / 100 where appropriate, but record which price source was used: yes ask, yes bid, midpoint, last trade, or orderbook-derived executable price. |
| Edge and EV calculation | The core output is model probability minus market probability, plus expected value. | Low | Prediction, market probability conversion | Implement `edge = model_probability - market_probability`; include fee/slippage placeholders even if v1 begins with a simplified formula. |
| Opportunity filtering | The spec defines minimum edge, model confidence, and liquidity thresholds. | Low | Edge/EV calculation, orderbook ingestion | Use configurable defaults: minimum edge 0.05, minimum model confidence 0.60, minimum liquidity 1000. |
| Opportunity ranking | Users need a prioritized list rather than raw signals. | Low | Opportunity filtering | Rank by expected value, then edge, then liquidity/confidence. Persist rejected opportunities with rejection reason for diagnostics. |
| Alerts for positive EV opportunities | The source spec calls for terminal, email, and SMS outputs. | Med | Opportunity ranking, config/secrets | V1 should include terminal plus one external channel first; email/SMS can be phased depending on setup cost. Alerts must include model probability, market probability, edge, EV, liquidity, market ticker, and match mapping confidence. |
| Backtesting framework | Profitability claims require replay/simulation evidence before live betting use. | High | Historical predictions, model artifacts, opportunity rules | Backtest prediction quality first, then simulated betting. When historical Kalshi market data is unavailable, label market-price backtests as limited or synthetic. |
| Betting performance metrics | Users need ROI evidence, not only model metrics. | Med | Backtesting framework | Report ROI, profit curve, win rate, average edge, max drawdown, sample size, and confidence intervals where feasible. |
| Persistent opportunity and prediction history | Debugging and validation need historical records of every signal and model output. | Med | Prediction job, opportunity engine | Persist matches, ratings, model_predictions, live_markets, opportunities, and backtest outputs as specified. |
| Configuration, logging, and typed pipeline | The spec requires production-grade reproducibility and observability. | Med | All pipeline modules | Centralize thresholds, paths, polling interval, model version, Kalshi credentials, and alert channels. Add structured logs around data snapshots, mapping, prediction, filtering, and alerts. |
| Critical unit tests | Leakage and EV logic failures would invalidate the platform. | Med | Core modules | Test chronological feature exclusion, Elo update order, name mapping, market probability conversion, EV calculation, threshold filtering, and ambiguous-market rejection. |

## Differentiators

Features that set the product apart. Not always expected in a basic tennis model, but valuable for this project.

| Feature | Value Proposition | Complexity | Dependencies | Notes |
|---------|-------------------|------------|--------------|-------|
| Leakage audit report | Makes trust explicit by proving features are generated from prior information only. | Med | Feature generation, tests | Emit per-feature as-of validation and examples of excluded future rows. This is especially valuable before using EV alerts. |
| Calibration-first model selection | Aligns model choice with betting usefulness rather than raw accuracy. | Med | Baselines, XGBoost, calibration metrics | Select production model by log loss/Brier/calibration plus stable segment performance, not just headline accuracy. |
| Market mapping confidence and review queue | The hardest operational risk is wrong player/market mapping; a queue makes uncertainty visible. | Med | Name normalization, market-to-match mapping | Include manual override workflow for player aliases and unresolved market titles. |
| Liquidity-aware executable EV | Avoids false positives from stale, thin, or non-executable prices. | High | Orderbook ingestion, EV calculation | Use orderbook depth and side-aware price assumptions to estimate whether a minimum stake can actually enter at the shown EV. |
| Opportunity rejection reasons | Helps tune thresholds and diagnose why markets are not alerting. | Low | Opportunity filtering | Persist reasons such as low edge, low confidence, low liquidity, ambiguous mapping, no current prediction, market closed, unsupported market type. |
| Surface/segment performance diagnostics | Detects whether a model is useful only on specific conditions. | Med | Evaluation pipeline | Break out performance by surface, tournament level, best-of, ranking bands, data era, and model confidence bucket. |
| Shadow-mode live monitoring before alerts | Builds evidence from live Kalshi markets without immediately spamming or encouraging action. | Low | Kalshi ingestion, live prediction, opportunity persistence | Run in observe-only mode to collect predictions, prices, and eventual outcomes before enabling external alerts. |
| Backtest limitation labeling | Prevents overstating ROI when historical market prices are incomplete or synthetic. | Low | Backtesting framework | Every backtest result should state whether it used actual historical Kalshi prices, reconstructed snapshots, or synthetic market probabilities. |

## Anti-Features

Features to explicitly NOT build in v1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| WTA support | The project scope and source constraints are ATP only; adding WTA doubles identity, tournament, and ranking complexity. | Keep schemas and config explicit about `tour = ATP`; reject WTA markets during discovery/mapping. |
| Doubles support | Doubles match data uses different player/team columns and different modeling assumptions. | Exclude doubles files and markets; document as non-v1. |
| Challenger/ITF/Futures product support | Lower-tier data exists in the Sackmann repository but changes market availability, player coverage, and stats completeness. | Use only ATP tour-level singles for v1 product predictions unless a later research phase validates lower-tier inclusion. |
| Betting platforms beyond Kalshi | The value proposition is Kalshi-only EV detection; abstractions for sportsbooks would add odds-format, account, and market-type complexity. | Implement a focused Kalshi client and data model. |
| Automated trade execution | The spec excludes execution; trading adds account risk, compliance, order lifecycle, failure handling, and financial controls. | Stop at ranked recommendations and alerts. |
| Portfolio management and bankroll automation | These require execution assumptions and risk policy not validated by v1 model/backtests. | Include informational EV, confidence, and liquidity; leave sizing as out of scope. |
| In-play/live point-by-point prediction | The primary dataset is pre-match historical data, not point-by-point live feeds; Kalshi live data docs do not list tennis as a supported sports stats type. | Focus on pre-match market monitoring and close-time awareness. |
| Scraping unofficial odds or tennis websites | It introduces brittle dependencies and violates the primary-source constraint. | Use Sackmann for history and Kalshi APIs for live market data. |
| LLM-based player matching as the primary mapper | Non-deterministic matching is dangerous for financial recommendations. | Use deterministic normalization, aliases, ids, confidence scoring, and manual overrides. |
| Accuracy-only success claims | Accuracy can hide poor calibration and unprofitable betting behavior. | Require log loss, Brier, calibration, EV, ROI, sample size, and drawdown reporting. |
| Random shuffled cross-validation | It leaks temporal structure and conflicts with the spec. | Use chronological splits, walk-forward validation, or time-based backtests. |
| "Positive ROI" marketing without sample size | The spec requires statistically significant sample size; premature ROI claims are misleading. | Report sample size, uncertainty, and backtest limitations. |
| User-facing web dashboard as a v1 prerequisite | It is not necessary to prove the ML/EV workflow and could distract from core correctness. | Start with CLI outputs, persisted CSV/DB tables, and alerts; consider dashboard after signal quality is validated. |

## Feature Dependencies

```text
Jeff Sackmann ATP data ingestion -> Dataset validation -> ATP-only canonical match store
ATP-only canonical match store -> Chronological train/validation/test split
ATP-only canonical match store -> Overall Elo ratings -> Surface-specific Elo ratings
ATP-only canonical match store -> Ranking/recent-form/serve-return/h2h/context features
Feature builders -> Differential feature builder -> Training dataset
Training dataset -> Logistic regression baseline -> Calibration/evaluation
Training dataset -> Random forest baseline -> Calibration/evaluation
Training dataset -> XGBoost production candidate -> Calibration/evaluation
Calibration/evaluation -> Model artifact registry -> Live prediction job
Kalshi market discovery -> Market detail ingestion -> Orderbook ingestion
Canonical player store + Kalshi market detail ingestion -> Player-name normalization -> Market-to-match mapping
Market-to-match mapping + Model artifact registry -> Live prediction job
Live prediction job + Market implied probability conversion -> Edge and EV calculation
Edge and EV calculation + Orderbook ingestion -> Opportunity filtering -> Opportunity ranking -> Alerts
Prediction/opportunity history + Backtesting framework -> Betting performance metrics
Critical unit tests -> Confidence to enable live polling and alerting
```

## MVP Recommendation

Prioritize:

1. **Source-of-truth ATP data pipeline**: ingest Sackmann ATP singles data, validate schema, build canonical match/player/ranking tables, and enforce ATP-only constraints.
2. **Leakage-safe prediction core**: chronological split, Elo/surface Elo, rankings, recent form, serve/return aggregates, h2h/context features, baselines, XGBoost, and calibration/evaluation.
3. **Kalshi EV detection loop**: discover Kalshi markets, ingest market/orderbook data, normalize names, map markets to ATP matches, generate predictions, calculate market probability/edge/EV, filter/rank opportunities, and persist outputs.
4. **Backtesting and trust evidence**: replay model predictions, simulate opportunity rules, report predictive and betting metrics, and label backtest limitations.
5. **Alerts after shadow mode**: start with terminal and persisted opportunity outputs; add email/SMS only after mapping and signal quality pass validation.

Defer:

- **Trade execution**: excluded from v1; revisit only after calibrated predictions, market mapping, live shadow logs, and backtests are validated.
- **WTA/doubles/lower-tier tours**: out of v1 scope and materially different modeling/data problems.
- **Other market platforms or sportsbooks**: out of scope; would dilute Kalshi-specific orderbook and market mapping work.
- **Full web dashboard**: useful later, but v1 requirements should focus on correctness, reproducibility, persistence, and alerts.
- **Advanced bankroll optimization**: premature without validated edge persistence and execution data.
- **Point-level or in-play modeling**: requires different data feeds and modeling assumptions.

## V1 Acceptance Signals

Use these signals to decide whether v1 is feature-complete enough for requirements validation:

| Signal | Target |
|--------|--------|
| Data scope | ATP singles historical ingestion works from Sackmann files; WTA/doubles/lower-tier files are rejected or ignored. |
| Leakage safety | Unit tests prove Elo, form, h2h, ranking, and aggregates exclude current/future matches. |
| Prediction quality | Reports include accuracy, ROC AUC, log loss, Brier score, calibration curve, and expected calibration error. |
| Calibration | Selected model emits probabilities suitable for EV comparison; uncalibrated classifiers are not accepted. |
| Kalshi integration | Live market discovery, market detail, and orderbook reads work against Kalshi APIs with persisted snapshots. |
| Mapping safety | Ambiguous Kalshi markets are not scored; every opportunity has a match id, player side, and mapping confidence. |
| EV logic | Opportunities include model probability, market probability source, edge, expected value, liquidity, thresholds, and rejection reasons. |
| Backtesting | Predictive and betting backtests produce ROI, profit curve, win rate, average edge, max drawdown, and sample-size context. |
| Alerts | Alerts are generated only for opportunities passing configured edge, confidence, liquidity, and mapping thresholds. |
| Execution boundary | No order placement, bankroll sizing, or portfolio automation exists in v1. |

## Complexity Hotspots for Requirements Definition

| Area | Complexity | Why It Matters | Requirement Guidance |
|------|------------|----------------|----------------------|
| Leakage-safe features | High | A subtle future-data leak invalidates all metrics and EV signals. | Requirements should include concrete as-of behavior and unit-test acceptance criteria. |
| Player/market mapping | High | Wrong mapping can invert or misassign financial recommendations. | Requirements should include confidence states, manual overrides, and reject-ambiguous behavior. |
| Orderbook-derived market probability | Med/High | Best bid, ask, midpoint, last price, and executable depth can imply different EV. | Requirements should specify the v1 price source and persist it with every opportunity. |
| Historical betting backtests | High | Historical Kalshi tennis prices may be sparse or unavailable for complete replay. | Requirements should distinguish actual historical market data from synthetic or snapshot-based tests. |
| Stats missingness | Med | Sackmann match stats are not complete for all eras/events. | Requirements should define minimum data windows, missing-value handling, and feature availability reports. |
| Alert channels | Med | SMS/email adds secrets, delivery failures, and noise controls. | Requirements should start with terminal/persisted outputs and one external channel only if needed. |

## Sources

- Project spec: `.planning/PROJECT.md` (HIGH confidence)
- Source outline: `project-outline.yaml` (HIGH confidence)
- Jeff Sackmann `tennis_atp` README and data dictionary: https://github.com/JeffSackmann/tennis_atp, https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/README.md, https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/matches_data_dictionary.txt (HIGH confidence for dataset structure; MEDIUM for future data completeness)
- Kalshi API documentation index and market endpoints: https://docs.kalshi.com/llms.txt, https://docs.kalshi.com/api-reference/market/get-markets.md, https://docs.kalshi.com/api-reference/market/get-market.md, https://docs.kalshi.com/api-reference/market/get-market-orderbook.md (HIGH confidence for current API shape as of 2026-06-16)

