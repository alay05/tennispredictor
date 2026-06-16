# Domain Pitfalls

**Domain:** ATP tennis prediction, calibrated probabilities, Kalshi EV detection  
**Project:** ATP Tennis Prediction and Kalshi EV Detection System  
**Researched:** 2026-06-16  
**Overall confidence:** MEDIUM

## Critical Pitfalls

Mistakes in this section can invalidate model performance, EV claims, or live alerts. The roadmap should treat them as phase gates, not cleanup tasks.

### Pitfall 1: Chronological Leakage in Tennis Features

**What goes wrong:** Features accidentally include information that was not available before the match prediction moment. In this project, the highest-risk fields are Elo, surface Elo, recent form, head-to-head, rolling serve/return rates, rankings, ranking points, age, days rest, and tournament progression.

**Why it happens:** Tennis data is event-shaped but the CSV rows are result-shaped. Sackmann match rows include winner/loser outcomes, match stats, ranking fields, and age fields together, which makes it easy to compute aggregates after seeing the result. The repository notes ranking and age fields are as of `tourney_date`, usually the Monday of the tournament week, not necessarily the exact match start time.

**Consequences:** Backtests look excellent, calibration appears stable, and EV opportunities appear frequent, but live results collapse because the model learned future state.

**Warning signs:**
- Random train/test split or shuffled cross-validation appears anywhere in model evaluation.
- Feature engineering runs on the full dataframe before train/validation/test segmentation.
- Rolling stats are computed with `groupby().rolling()` without an explicit prior-match shift.
- Head-to-head counts include the current match.
- Elo is stored only after a match, with no pre-match snapshot for both players.
- Ranking, age, or tournament features are used without recording their as-of date.

**Prevention strategy:**
- Build one walk-forward feature builder that emits pre-match snapshots and then updates state after the match result.
- Add invariant tests for every stateful feature: for a selected match, deleting all future rows must not change its feature vector.
- Store `feature_asof_ts`, `source_match_id`, and `state_version` with every generated training row.
- Use chronological splits only: train on earlier dates, calibrate on later dates, test on final unseen dates.
- Keep ATP singles v1 scope explicit: exclude WTA, doubles, Challenger, Futures, qualifying, exhibitions, and non-ATP rows unless a later phase intentionally expands scope.

**Phase should address:** Phase 1 data contract and Phase 2 Elo/features. This must be blocked before model training.

**Confidence:** MEDIUM

### Pitfall 2: Treating Accuracy as the Main Betting Metric

**What goes wrong:** The roadmap optimizes for match winner accuracy or ROC AUC, then assumes that a 60-65% classifier creates profitable EV signals.

**Why it happens:** Classification metrics are intuitive, but betting decisions depend on probability error at the price boundary. A model can be directionally accurate but overconfident, underconfident, or aligned with market prices in a way that produces no tradable edge.

**Consequences:** The system emits many positive-edge alerts that are calibration artifacts. Thresholds like `minimum_edge: 0.05` become arbitrary because the model probability is not reliable enough to compare with market price.

**Warning signs:**
- Model selection tables rank candidates by accuracy first.
- Calibration is a plot in the report but not a release gate.
- Brier score/log loss improve while reliability curves degrade in the 0.55-0.75 betting zone.
- Production XGBoost probabilities are used directly without chronological calibration.
- Confidence thresholds use the raw predicted probability instead of calibrated uncertainty.

**Prevention strategy:**
- Make log loss, Brier score, expected calibration error, and reliability diagrams first-class model selection criteria.
- Evaluate calibration by probability bucket, surface, tournament level, season/era, and favorite/underdog side.
- Use a disjoint chronological calibration window; do not fit calibrators on the final test set or live outcomes.
- Require an EV sanity report showing how many alerts survive after perturbing model probabilities by calibration error.
- Keep logistic regression and Elo-only baselines; do not promote XGBoost unless it beats baselines on calibrated probability quality, not only accuracy.

**Phase should address:** Phase 3 model training and calibration. It should also be rechecked in Phase 5 backtesting.

**Confidence:** MEDIUM

### Pitfall 3: Mapping the Wrong Kalshi Market to the ATP Match

**What goes wrong:** A Kalshi market is linked to the wrong match, wrong player side, wrong tournament, wrong round, wrong date, or wrong settlement rule. The model probability is then compared to an unrelated or inverted contract.

**Why it happens:** Player names vary across data sources; tennis has retirements, walkovers, time zone shifts, tournament naming differences, rematches, and same-day matches. Kalshi market titles/subtitles and yes/no wording are market-specific, while Sackmann rows are historical result records.

**Consequences:** The EV engine can produce confident false positives. This is worse than a model error because the probability may be good for the intended match but attached to the wrong tradable instrument.

**Warning signs:**
- Matching is based on fuzzy player names only.
- Alerts do not display ticker, event ticker, market title, subtitle, yes/no side, close time, and settlement rule.
- A market can be accepted without both player IDs being resolved to canonical ATP players.
- Side orientation is inferred from player order in a title rather than explicit yes/no contract text.
- Market mapping has no manual review queue for ambiguous matches.

**Prevention strategy:**
- Create a market mapping phase before EV alerting. Require deterministic match candidates from tournament, date/window, players, and round before applying fuzzy matching.
- Canonicalize player names to Sackmann `player_id`; keep aliases as data, not code.
- Store a `MarketMatchMapping` record with confidence, matched fields, unmatched fields, side orientation, and source payload.
- Require explicit tests for inverted YES/NO sides and ambiguous same-player-name cases.
- Default ambiguous mappings to `NO_ALERT`; never emit EV from a low-confidence mapping.

**Phase should address:** Phase 4 Kalshi market discovery/mapping. It must precede Phase 5 EV detection and backtesting.

**Confidence:** MEDIUM

### Pitfall 4: Using Non-Executable Market Prices for EV

**What goes wrong:** EV is calculated from last trade, midpoint, displayed yes price, or stale market field instead of the price actually executable for the required side and size.

**Why it happens:** Kalshi market payloads expose multiple price fields, and the orderbook is not symmetric in the usual sportsbook sense. Kalshi orderbook responses return bids only; asks must be inferred from the opposite side. The best YES ask is `1 - best_no_bid`, and the best NO ask is `1 - best_yes_bid`.

**Consequences:** The system overstates expected value, especially in thin ATP markets where spread and depth dominate small model edges.

**Warning signs:**
- `market_probability = yes_price / 100` is the only conversion logic.
- EV calculations ignore bid/ask spread, orderbook depth, stale timestamps, fees, and rounding.
- Liquidity is checked with total volume instead of executable depth near the target price.
- Alerts rank by edge without expected fill price and expected slippage.

**Prevention strategy:**
- Implement side-aware executable pricing: BUY_YES uses implied YES ask; SELL_YES/BUY_NO use the corresponding side and depth.
- Parse fixed-point price/count strings with decimal arithmetic, not floats.
- Add orderbook tests for both YES and NO sides using Kalshi's reciprocal bid/ask mechanics.
- Require EV to include fees, rounding, expected fill size, and depth-limited average price.
- Store the full orderbook snapshot used for each opportunity.

**Phase should address:** Phase 4 Kalshi pricing and Phase 5 EV engine.

**Confidence:** MEDIUM

### Pitfall 5: Backtests That Could Not Have Been Traded

**What goes wrong:** The backtest simulates bets at prices that were unavailable, uses markets that did not exist at prediction time, ignores spreads/fees/liquidity, or selects thresholds after looking at test ROI.

**Why it happens:** Historical tennis results are available, but historical Kalshi ATP market snapshots may be incomplete or split across live and historical API tiers. Kalshi docs state older markets, candlesticks, trades, fills, and orders move from live endpoints to historical endpoints after cutoffs.

**Consequences:** Positive ROI is a research artifact. The roadmap may ship an alerting system whose edge disappears when execution constraints are included.

**Warning signs:**
- Backtest uses final market settlement price or post-match close price as the pre-match market probability.
- No `observed_at` timestamp for every simulated market price.
- Fill model assumes unlimited size at top-of-book.
- Thresholds are tuned on the same test window used for final ROI reporting.
- ROI is reported without max drawdown, number of bets, confidence interval, and edge bucket breakdown.

**Prevention strategy:**
- Separate model backtest from market replay backtest. First validate predictions against match outcomes; then validate EV only where historical market observations exist.
- Snapshot Kalshi markets/orderbooks going forward as soon as integration exists; do not rely on future availability of all historical ATP market states.
- Simulate only decisions that would have been observable at the alert timestamp.
- Include spread, fees, rounding, depth, latency, rejected ambiguous mappings, and no-fill outcomes.
- Freeze EV thresholds before final test; report sensitivity analysis separately.

**Phase should address:** Phase 5 backtesting. Snapshot collection starts in Phase 4.

**Confidence:** MEDIUM

## Moderate Pitfalls

### Pitfall 6: Misusing Sackmann Match Stats as Ready-Made Percentages

**What goes wrong:** Serve and return features are computed from the wrong columns or with invalid denominators. Sackmann MatchStats are integer totals such as first serves in and first-serve points won, not precomputed percentages.

**Warning signs:**
- Feature names like `winner_first_serve_pct` are mapped directly to columns without deriving from `w_1stIn / w_svpt`.
- Missing stat rows are filled with zeros.
- Retirements, walkovers, and short matches are treated as normal performance samples.

**Prevention strategy:**
- Create a typed stat-derivation module with explicit formulas and denominator checks.
- Represent missing stats as missing, with model-safe imputation learned on training data only.
- Add data quality flags for missing stats, retirements, walkovers, and suspicious durations.

**Phase should address:** Phase 1 ingestion and Phase 2 feature engineering.

**Confidence:** MEDIUM

### Pitfall 7: Ranking Coverage and As-Of Semantics Are Ignored

**What goes wrong:** Ranking points and rank changes are treated as complete daily facts. Sackmann rankings are mostly complete from 1985 onward, 1982 is missing, and 1973-1984 are intermittent; match-row rankings are as of `tourney_date` or most recent ranking before it.

**Warning signs:**
- Ranking features are backfilled across long gaps without a missingness flag.
- Early-era data is mixed with modern data without coverage controls.
- `ranking_change_30_days` is computed by nearest row after the match date.

**Prevention strategy:**
- Start v1 modeling on the modern data window with acceptable ranking and MatchStats coverage.
- Record ranking source date for each player-match feature.
- Add missingness indicators and era filters rather than hiding coverage gaps.

**Phase should address:** Phase 1 data contract and Phase 3 model evaluation.

**Confidence:** MEDIUM

### Pitfall 8: Scope Creep Into Non-ATP or Non-v1 Competitions

**What goes wrong:** The ingestion layer quietly includes Challenger, Futures, qualifying, doubles, Davis Cup, WTA-style level codes, or other non-v1 scopes because those files/codes exist in the source repository.

**Warning signs:**
- Loader glob pattern includes `atp_matches_qual_chall_*.csv`, `atp_matches_futures_*.csv`, or `atp_matches_doubles_*.csv`.
- The model has tournament-level codes outside ATP singles main draw without an explicit scope decision.
- Tests count non-ATP or doubles rows as valid examples.

**Prevention strategy:**
- Define an `ATPSinglesMainDrawScope` filter in ingestion.
- Add row-count tests by file pattern and `tourney_level`.
- Keep excluded scopes in a quarantine table for auditability, not in the training set.

**Phase should address:** Phase 1 ingestion.

**Confidence:** MEDIUM

### Pitfall 9: Overfitting to Sparse Tennis Context Features

**What goes wrong:** Head-to-head, surface form, recent form, and round-specific stats are over-weighted despite tiny samples. Tennis has many player/surface combinations with little history, especially for newer players.

**Warning signs:**
- H2H percentage is used without match count.
- Surface win rate is extreme for players with one or two matches.
- Feature importance is dominated by sparse derived features.
- Calibration is poor for young players, qualifiers, or players returning from inactivity.

**Prevention strategy:**
- Pair every rate with count/exposure and shrink sparse rates toward tour/player priors.
- Add minimum-sample guards for H2H and surface-specific features.
- Compare against Elo-only and rank-only baselines to catch fragile feature lift.

**Phase should address:** Phase 2 feature engineering and Phase 3 model validation.

**Confidence:** MEDIUM

### Pitfall 10: EV Thresholds Hide Model and Market Uncertainty

**What goes wrong:** A fixed `minimum_edge: 0.05` is treated as sufficient even when calibration error, spread, fees, stale data, and mapping ambiguity exceed the edge.

**Warning signs:**
- Alerts trigger near the threshold with wide spreads.
- No uncertainty band around model probability.
- Market mapping confidence and price freshness do not affect eligibility.

**Prevention strategy:**
- Define net edge as `calibrated_model_probability - executable_market_probability - estimated_costs - uncertainty_buffer`.
- Make thresholds configurable but validated in backtests.
- Suppress alerts when mapping confidence, price freshness, or liquidity checks fail.

**Phase should address:** Phase 5 EV engine and Phase 6 alerting.

**Confidence:** MEDIUM

## Minor Pitfalls

### Pitfall 11: Float Math in Money and Probability Conversions

**What goes wrong:** Subpenny prices, fractional counts, and fee rounding are parsed into floats, producing small errors that can flip marginal EV decisions.

**Prevention:** Use decimal/fixed-point arithmetic for Kalshi prices, counts, fees, and EV. Convert to float only for model probability metrics where appropriate.

**Phase should address:** Phase 4 Kalshi client and Phase 5 EV engine.

### Pitfall 12: Live API and Historical API Boundaries Are Treated as One Dataset

**What goes wrong:** Collection jobs miss markets or trades because older data must be pulled from Kalshi historical endpoints, not normal live endpoints.

**Prevention:** Build repository methods that route by cutoff timestamp and pagination cursor. Persist raw responses so future schema/API changes can be replayed.

**Phase should address:** Phase 4 Kalshi integration.

### Pitfall 13: Alerts Without Audit Trail

**What goes wrong:** An alert says "positive EV" but cannot later prove the exact model, features, market mapping, price snapshot, and threshold configuration used.

**Prevention:** Persist every alert decision, including rejected candidates, model version, feature vector hash, calibrated probability, market payload, orderbook snapshot, mapping confidence, and reason codes.

**Phase should address:** Phase 6 alerting/ops, with schema groundwork in Phase 1.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|----------------|------------|
| Phase 1: Data ingestion and schema contract | Pulling non-v1 scopes or treating Sackmann fields as complete daily facts | Explicit ATP singles main-draw scope filter, data dictionary mapping, coverage report, and as-of columns |
| Phase 2: Elo and features | Future match leakage through rolling features, H2H, Elo, and derived stats | Single walk-forward feature builder, pre-match snapshots, invariant tests, and state updates only after result |
| Phase 3: Modeling and calibration | Promoting XGBoost for accuracy while probabilities are poorly calibrated | Chronological validation, calibration window, reliability reports, baseline comparisons, and calibration gates |
| Phase 4: Kalshi integration | Wrong match mapping or wrong YES/NO side | Canonical player IDs, mapping confidence, side-orientation tests, raw market payload storage, and ambiguity quarantine |
| Phase 4: Kalshi pricing | Treating last price or yes field as executable probability | Side-aware orderbook parser using reciprocal bid/ask mechanics and decimal arithmetic |
| Phase 5: Backtesting and EV | Simulated bets at unobservable or unfillable prices | Timestamped replay, top-of-book/depth fill model, fees/rounding, no-fill outcomes, and frozen thresholds |
| Phase 6: Alerts and operations | Alerting before mapping, calibration, and backtest evidence are trustworthy | Reason-coded alert gate requiring model, mapping, liquidity, freshness, and net-edge checks |

## Roadmap Guardrails

- Make "no chronological leakage" a release criterion for every phase that touches features, models, or backtests.
- Do not build Kalshi alerting until market mapping and executable pricing have their own tests.
- Treat calibration as a product requirement, not a modeling enhancement.
- Separate predictive validation from EV validation. A good ATP model is necessary but not sufficient for profitable Kalshi decisions.
- Start collecting Kalshi snapshots early, even before live alerts, because future backtests need observable historical market states.
- Preserve v1 constraints in all schemas and tests: ATP only, Jeff Sackmann `tennis_atp` primary historical source, Kalshi only, no automated execution.

## Sources

- [scikit-learn Common pitfalls and recommended practices](https://scikit-learn.org/stable/common_pitfalls.html) - data leakage and preprocessing leakage guidance. Confidence: MEDIUM.
- [scikit-learn Probability calibration](https://scikit-learn.org/stable/modules/calibration.html) - calibration methods and disjoint calibration data considerations. Confidence: MEDIUM.
- [Walsh and Joshi, "Machine learning for sports betting: should model selection be based on accuracy or calibration?"](https://arxiv.org/abs/2303.06021) - sports betting model selection should emphasize calibration over raw accuracy. Confidence: MEDIUM.
- [Jeff Sackmann tennis_atp README](https://github.com/JeffSackmann/tennis_atp) - dataset coverage, ranking semantics, MatchStats caveats, license, and scope. Confidence: MEDIUM.
- [Jeff Sackmann matches data dictionary](https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/matches_data_dictionary.txt) - field meanings, tournament levels, stats totals, and ranking as-of semantics. Confidence: MEDIUM.
- [Kalshi Get Market API](https://docs.kalshi.com/api-reference/market/get-market) - market fields including ticker, yes/no prices, volume, liquidity, timing, and settlement-related fields. Confidence: MEDIUM.
- [Kalshi Orderbook Responses](https://docs.kalshi.com/getting_started/orderbook_responses) and [Get Market Orderbook](https://docs.kalshi.com/api-reference/market/get-market-orderbook) - bids-only orderbook and reciprocal bid/ask mechanics. Confidence: MEDIUM.
- [Kalshi Fee Rounding](https://docs.kalshi.com/getting_started/fee_rounding) - trade fee, rounding fee, rebate, precision, and accumulator mechanics. Confidence: MEDIUM.
- [Kalshi Historical Data](https://docs.kalshi.com/getting_started/historical_data) - live/historical API partitioning, cutoffs, and endpoint routing. Confidence: MEDIUM.
- [Kalshi Market Settlement](https://docs.kalshi.com/getting_started/market_settlement) - yes/no settlement, timing variability, and settlement fee notes. Confidence: MEDIUM.

## Gaps and Follow-Up Research

- Kalshi ATP-specific market naming conventions and settlement wording should be researched against live/demo markets during Phase 4.
- Historical Kalshi ATP market depth availability is uncertain until API credentials and real endpoint access are tested.
- Tennis retirement, walkover, and incomplete-match handling should be specified during Phase 1 because it affects labels, features, and settlement mapping.
- Commercial use of Sackmann data may be constrained by the non-commercial license; this project should confirm intended use before production or monetization.
