# Architecture Patterns

**Domain:** ATP-only tennis prediction and Kalshi EV detection  
**Researched:** 2026-06-16  
**Overall confidence:** MEDIUM. Core architecture is grounded in current project constraints and official/current docs, but phase-specific implementation details should still validate exact Kalshi sports market naming and historical data edge cases.

## Executive Recommendation

Build the system as a deterministic, append-oriented pipeline with explicit persistence boundaries between raw source data, normalized domain entities, point-in-time feature snapshots, model artifacts, market snapshots, and EV decisions. Leakage prevention should live in the data contracts and pipeline order, not in model-training conventions. The feature store should only expose features through an `as_of_date` interface, and all training, validation, backtesting, and live prediction should call the same feature materialization path.

The recommended shape is a modular Python batch-first system with a small live monitor. Start with historical ingestion and domain normalization from Jeff Sackmann's `tennis_atp` files, then build chronological feature generation and tests, then model training/calibration, then backtesting, and only after that add Kalshi market discovery and EV ranking. This avoids rework because the live monitor can reuse the same match identity, player identity, feature, model, pricing, and decision interfaces validated by backtests.

Preserve these constraints in package names, data schemas, and tests: ATP only, Jeff Sackmann `tennis_atp` as the primary historical source, and Kalshi only for live markets. Do not generalize early for WTA, other tours, sportsbooks, or automated execution.

## Recommended Architecture

```text
Jeff Sackmann tennis_atp CSVs
        |
        v
Raw Data Lake / Raw Tables
  - file manifests
  - raw match rows
  - raw ranking rows
  - raw player rows
        |
        v
Canonical ATP Domain Store
  - players
  - tournaments
  - matches
  - rankings
  - match stats
        |
        v
Chronological State Builders
  - overall Elo
  - surface Elo
  - rolling form
  - rolling serve/return stats
  - head-to-head state
        |
        v
Point-in-Time Feature Store
  - feature snapshots keyed by match_id, player_a_id, player_b_id, as_of_date
  - data availability metadata
  - feature version
        |
        v
Model Training and Calibration
  - chronological train/validation/test split
  - baseline models
  - XGBoost candidate
  - calibrator fit on disjoint chronological validation window
  - model registry
        |
        v
Backtesting Engine
  - historical prediction replay
  - simulated market assumptions or archived market snapshots
  - edge/EV decisions
  - ROI and calibration reports
        |
        v
Kalshi Live Monitor
  - market discovery
  - market-to-match mapper
  - orderbook/pricing snapshots
  - live feature lookup
  - prediction and EV ranking
  - alerts/recommendations only
```

Data direction should be one-way for production workflows. Raw source data can be re-ingested into raw storage; normalized tables can be rebuilt from raw; feature snapshots can be rebuilt from normalized data and versioned feature code; models can be retrained from feature snapshots; predictions and opportunities are append-only observations. The live monitor may read model artifacts and feature state, but it should not mutate historical matches, feature snapshots, or model artifacts.

## Component Boundaries

| Component | Responsibility | Owns Persistence | Reads From | Writes To |
|-----------|----------------|------------------|------------|-----------|
| Source fetcher | Clone or download Jeff Sackmann ATP files and record file versions/checksums. | `source_files`, ingestion manifests | GitHub `tennis_atp` | Raw data lake/tables |
| Raw ingestor | Load CSV rows without business transformations; preserve original columns and source file metadata. | `raw_atp_matches`, `raw_atp_rankings`, `raw_atp_players` | Source files | Raw tables |
| Domain normalizer | Convert raw rows into canonical ATP-only players, tournaments, matches, rankings, and stats. | Canonical ATP domain tables | Raw tables | Normalized domain store |
| Identity resolver | Maintain player IDs, names, aliases, and Kalshi display-name mappings. | `player_aliases`, `market_match_links` | Domain store, Kalshi markets | Mapping tables |
| Chronological state builder | Iterate matches strictly by event date/order and compute pre-match state. | Elo/rating history, rolling stat state | Domain store | Feature snapshots/state tables |
| Feature store | Serve only point-in-time feature vectors with `as_of_date`, `feature_version`, and source availability metadata. | `match_features` | State tables/domain store | Training and prediction datasets |
| Dataset builder | Freeze training/validation/test datasets and labels from feature snapshots. | Dataset manifests | Feature store | Versioned datasets |
| Model trainer | Train baseline and candidate models using chronological splits only. | Model artifacts and metrics | Versioned datasets | Model registry |
| Calibrator | Fit probability calibration on a disjoint chronological validation window. | Calibrator artifacts | Model outputs and validation labels | Model registry |
| Evaluator | Produce accuracy, ROC AUC, log loss, Brier score, calibration curves, and reliability reports. | Evaluation reports | Model registry, datasets | Metrics store/reports |
| Backtester | Replay predictions and EV rules over historical windows before live use. | Backtest runs and decisions | Model registry, feature store, pricing assumptions or market snapshots | Backtest outputs |
| Kalshi adapter | Encapsulate Kalshi authentication, market listing, market details, and orderbook access. | Raw market snapshots | Kalshi API | Market snapshot tables |
| Market mapper | Match Kalshi market titles/tickers/participants to ATP canonical matches. | `market_match_links` | Kalshi snapshots, ATP schedule/domain data | Mapping tables |
| Pricing engine | Convert yes/no bid/ask/orderbook data into conservative implied probability and liquidity metrics. | Pricing snapshots | Kalshi snapshots | `market_prices` |
| EV engine | Join model probability and market probability; compute edge, expected value, and recommendation. | Opportunities | Predictions, pricing, mappings | `opportunities` |
| Alerting/reporting | Rank and surface qualifying positive-EV opportunities. | Alert log | Opportunities | Notifications/reports |

## Persistence Boundaries

Keep these storage boundaries explicit even if v1 uses one local database plus artifact files:

| Boundary | Contents | Mutability | Why It Matters |
|----------|----------|------------|----------------|
| Raw source layer | Original Sackmann CSV rows and file manifests | Append/replace by source version | Enables reproducible rebuilds and schema drift inspection. |
| Canonical ATP layer | Normalized players, tournaments, matches, rankings, stats | Rebuildable from raw | Prevents feature code from depending on raw CSV quirks. |
| Point-in-time state layer | Elo, surface Elo, rolling form, rolling serve/return stats, H2H before each match | Rebuildable, versioned | Makes leakage prevention auditable. |
| Feature snapshot layer | Model-ready differential features keyed by match and `as_of_date` | Immutable per feature version | Ensures training, backtesting, and live prediction share one contract. |
| Artifact registry | Datasets, model binaries, calibrators, metrics, feature/model versions | Immutable per run | Makes predictions traceable to exact data and code versions. |
| Market snapshot layer | Kalshi markets, orderbooks, derived prices, liquidity | Append-only observations | Preserves what the market looked like when a decision was made. |
| Decision layer | Predictions, EV calculations, recommendations, alerts | Append-only observations | Supports audit, backtesting comparison, and post-hoc analysis. |

Avoid a single wide "matches with features and market prices" table. That structure invites accidental rewrites, makes point-in-time semantics ambiguous, and forces live market fields into historical training data.

## Data Flow Details

### Historical Data Flow

1. Fetch `tennis_atp` source files and record source revision, file path, checksum, and ingestion timestamp.
2. Load raw rows exactly as delivered. Do not calculate percentages, Elo, or labels in the raw layer.
3. Normalize to ATP singles tour-level match entities. Exclude doubles, futures, challengers, WTA, and non-scope rows by explicit filters and tests.
4. Build stable internal IDs for players, tournaments, and matches. Prefer Sackmann player IDs where available; keep source names as observed aliases.
5. Order matches chronologically by `tourney_date` plus deterministic tie-breakers. Within a tournament date, use a stable match ordering and record that exact ordering because same-day match order may be imperfect in the source.
6. Before processing each match, emit pre-match features for both players. After emission, update Elo, surface Elo, rolling stats, and H2H state with the match result.
7. Freeze feature snapshots with feature-code version and source-data version.

### Training Data Flow

1. Dataset builder requests feature snapshots over chronological windows.
2. Labels are derived only from the match outcome and player orientation selected by the dataset builder.
3. Split train/validation/test chronologically. Do not use random shuffle for final metrics.
4. Train baseline logistic regression and random forest first to establish sanity checks.
5. Train XGBoost candidate only after feature snapshots and baseline metrics are stable.
6. Fit calibrator on a validation period disjoint from model training. Persist model and calibrator as a versioned pair.
7. Store metrics by model version, feature version, source version, and split boundaries.

### Backtest Flow

1. Select a historical evaluation window after the model training window.
2. Recreate the exact feature vectors that would have existed before each match.
3. Generate probabilities using only the model version available at that simulated time.
4. Apply conservative market-price assumptions or archived Kalshi snapshots when available.
5. Use the same pricing and EV engine as live monitoring.
6. Persist every simulated decision, including no-bet decisions and filter reasons.

### Live Kalshi Flow

1. Poll Kalshi market listing endpoints for relevant open/unopened tennis markets using status, close-time, event, series, or search filters where available.
2. Persist raw market metadata before attempting match mapping.
3. Map market title/subtitle/participants/rules to canonical ATP match candidates through the identity resolver. Ambiguous mappings should be quarantined, not guessed.
4. Fetch market details and orderbook snapshots for mapped markets. Kalshi orderbooks expose yes and no bid sides; ask-equivalent prices must be derived from the opposite side.
5. Build or retrieve the pre-match feature vector for the mapped ATP match with the same feature store API used by training.
6. Generate calibrated probability, derive implied market probability, calculate edge and EV, apply liquidity/confidence thresholds, and rank opportunities.
7. Persist the full decision record: model version, calibrator version, feature version, market ticker, orderbook timestamp, model probability, implied probability, edge, EV, liquidity, recommendation, and filter reason.

## Leakage Prevention as Architecture

Leakage prevention should be enforced by interfaces:

| Risk | Architectural Control |
|------|------------------------|
| Future Elo or rolling stats enter features | State builder emits features before updating state with the current match. Unit tests should assert this order. |
| Random splits inflate metrics | Dataset builder only exposes chronological splits for official metrics. Random split helpers should not exist in production code. |
| Calibration uses training rows or future rows | Calibrator component accepts only disjoint validation windows and persists split boundaries. |
| Rankings from after the match leak into features | Ranking lookup API must require `as_of_date` and choose the latest ranking date not after the match availability cutoff. |
| Same-day or tournament-level ordering ambiguity | Match ordering policy must be deterministic and stored in feature metadata; high-risk same-day features should be limited or lagged. |
| Live predictions use features computed with match result | Live feature API should only allow scheduled/unplayed match IDs or explicit player/date inputs, never completed match rows. |
| Market mapping accidentally creates training labels | Kalshi data remains outside the model training feature layer; market snapshots are for EV/backtesting decisions, not predictive features in v1. |

The core invariant is:

```python
features = feature_store.get_match_features(
    player_a_id=player_a_id,
    player_b_id=player_b_id,
    surface=surface,
    tournament_context=context,
    as_of_date=match_start_cutoff,
    feature_version=feature_version,
)
```

No training, backtest, or live code should calculate its own Elo, rolling form, ranking, H2H, or serve/return aggregates outside this interface.

## Suggested Package Structure

```text
src/tennisprediction/
  config/
    settings.py
  ingestion/
    sackmann_fetcher.py
    raw_loaders.py
    manifests.py
  domain/
    models.py
    normalization.py
    identity.py
  features/
    chronological_runner.py
    elo.py
    rolling_stats.py
    h2h.py
    feature_store.py
    schemas.py
  datasets/
    builder.py
    splits.py
    manifests.py
  modeling/
    baselines.py
    xgboost_model.py
    calibration.py
    registry.py
    evaluation.py
  backtesting/
    replay.py
    stake_policy.py
    reports.py
  kalshi/
    client.py
    market_discovery.py
    orderbook.py
    schemas.py
  live/
    market_mapper.py
    pricing.py
    ev.py
    monitor.py
    alerts.py
  storage/
    db.py
    repositories.py
    migrations/
  cli/
    main.py
```

Keep `kalshi/` dependent on `domain/` only through mapping types and repositories. Keep `modeling/` dependent on frozen datasets, not raw data. Keep `live/` dependent on `feature_store`, `model_registry`, `kalshi`, and `ev`, but not on training internals.

## Build Order

| Phase | Build | Why This Order Avoids Rework |
|-------|-------|-------------------------------|
| 1 | Project skeleton, configuration, logging, typed settings, storage migrations, source manifests | Gives every later component a place to persist versioned outputs. |
| 2 | Sackmann raw ingestion and canonical ATP domain normalization | Establishes IDs and schemas before feature logic depends on them. |
| 3 | Chronological state runner with Elo/surface Elo and minimal differential features | Locks the leakage-safe execution model early. |
| 4 | Feature store API and feature snapshot persistence | Creates the shared contract for training, backtesting, and live prediction. |
| 5 | Dataset builder, chronological splits, baseline models, core metrics | Validates labels, splits, and features before complex models. |
| 6 | XGBoost model candidate and calibration pipeline | Adds production candidate only after baseline sanity checks pass. |
| 7 | Backtesting engine using model probability plus EV rules | Validates betting decision logic before live market monitoring. |
| 8 | Kalshi adapter, raw market snapshots, orderbook pricing | Integrates live market data without contaminating the model pipeline. |
| 9 | Player/market identity mapping and ambiguity quarantine | Solves the highest-risk live integration boundary before alerts. |
| 10 | Live EV monitor, ranking, and alerts | Final assembly using validated model, feature, pricing, and mapping contracts. |

Do not build the live Kalshi monitor before the feature store and backtester. Without those, the monitor will force ad hoc feature generation, player matching, and EV calculations that later need to be rewritten.

## Roadmap Implications

1. **Foundation and Data Contracts** should precede model work. The first roadmap phase should produce storage, raw ingestion, canonical domain tables, source manifests, and ATP-only filters.
2. **Leakage-Safe Feature Engine** should be its own phase. It is the highest-value architectural risk and should include unit tests that prove pre-match emission happens before post-match state updates.
3. **Modeling and Calibration** should follow feature snapshots, not raw ingestion. Roadmap acceptance should require chronological metrics and calibration curves, not just accuracy.
4. **Backtesting Before Live Monitoring** should be explicit. The EV engine belongs in backtesting first so live alerts inherit tested decision logic.
5. **Kalshi Integration Last** should be staged as adapter, mapping, pricing, then alerts. Market mapping ambiguity is likely the riskiest live phase and should get its own validation gate.

## Patterns to Follow

### Pattern 1: Append-Only Observations

**What:** Predictions, market prices, orderbooks, opportunities, alerts, and backtest decisions should be append-only records.  
**When:** Any data captures what was known or decided at a time.  
**Example:**

```python
OpportunityRecord(
    observed_at=clock.now(),
    market_ticker=market.ticker,
    match_id=match.id,
    model_version=model.version,
    feature_version=features.version,
    orderbook_snapshot_id=orderbook.id,
    model_probability=probability,
    implied_probability=price.implied_probability,
    edge=probability - price.implied_probability,
    expected_value=ev,
    recommendation=recommendation,
    filter_reason=filter_reason,
)
```

### Pattern 2: Rebuildable Derived Layers

**What:** Raw and canonical data are the source of truth; state, features, datasets, and model artifacts are derived and versioned.  
**When:** Feature logic, model logic, or source data changes.  
**Why:** Tennis features are iterative and leakage-prone. Being able to rebuild and compare feature versions is more important than mutating existing derived tables.

### Pattern 3: Shared Prediction Path

**What:** Training evaluation, backtesting, and live monitoring use the same feature schema and model prediction service.  
**When:** Any code asks for model probability.  
**Why:** If live prediction has a separate path, it will drift from training semantics and invalidate backtest claims.

### Pattern 4: Ambiguity Quarantine

**What:** Market-to-match mapping should emit `mapped`, `ambiguous`, or `unmatched`; only `mapped` markets proceed to EV decisions.  
**When:** Kalshi titles, participant names, timing, or tournament context do not uniquely identify a canonical ATP match.  
**Why:** A wrong market mapping is worse than a missed opportunity because it creates confident EV on the wrong event.

## Anti-Patterns to Avoid

### Anti-Pattern 1: Feature Engineering Inside Model Training

**What:** Training code computes Elo, recent form, H2H, or ranking joins directly.  
**Why bad:** Backtests and live monitoring will duplicate feature logic, and leakage tests will miss alternate paths.  
**Instead:** Training consumes frozen feature snapshots from the feature store.

### Anti-Pattern 2: Market Data as Model Features in v1

**What:** Including Kalshi prices or liquidity in the model feature set.  
**Why bad:** The model is supposed to estimate match probability independently, then compare against market probability. Market data in the predictive model muddies EV interpretation and creates availability issues for historical training.  
**Instead:** Keep market data in the pricing and EV layer.

### Anti-Pattern 3: Generalized Betting Platform Adapter

**What:** Abstracting for multiple sportsbooks/exchanges before Kalshi works.  
**Why bad:** It expands schema and pricing complexity against explicit project scope.  
**Instead:** Model Kalshi yes/no markets directly and only abstract internal pricing concepts needed for EV.

### Anti-Pattern 4: One Mutable Feature Table

**What:** A table that stores current player stats and is overwritten as new matches arrive.  
**Why bad:** Historical reproduction becomes impossible and training can silently see future state.  
**Instead:** Store pre-match feature snapshots and versioned state history.

## Scalability Considerations

| Concern | At Local/MVP Scale | At Daily Operation Scale | At Larger Scale |
|---------|--------------------|--------------------------|-----------------|
| Historical ingestion | Local files plus SQLite/Postgres | Scheduled source refresh with manifests | Object storage plus warehouse tables |
| Feature generation | Single chronological batch process | Incremental rebuild from latest processed match | Partitioned rebuilds by season with full replay checks |
| Model training | Local scikit-learn/XGBoost jobs | Versioned training runs and artifact registry | Experiment tracker and distributed training only if needed |
| Live monitoring | Poll Kalshi REST endpoints | REST polling plus orderbook snapshot persistence | WebSocket orderbook maintenance for mapped markets |
| Market mapping | Deterministic name/date rules with manual review table | Alias curation workflow | Human-in-the-loop queue for ambiguous mappings |
| Backtesting | Replay over held-out historical windows | Recurring reports after model retraining | Separate simulation service if strategy complexity grows |

## Sources

- Jeff Sackmann `tennis_atp` README: confirms ATP player, ranking, result, and match-stat files; ranking columns; ranking completeness caveats; match-stat availability and missing-stat caveats; source license constraints. https://github.com/JeffSackmann/tennis_atp
- Kalshi Get Markets API: confirms market listing pagination, status filters, event/series filters, close/settle/update filters. https://docs.kalshi.com/api-reference/market/get-markets
- Kalshi Get Market API: confirms binary market metadata, yes/no prices, volume, liquidity, rules, participant fields, and market ticker lookup. https://docs.kalshi.com/api-reference/market/get-market
- Kalshi Get Market Orderbook API: confirms authenticated orderbook endpoint, yes/no bid structure, depth parameter, and binary ask-equivalence behavior. https://docs.kalshi.com/api-reference/market/get-market-orderbook
- Kalshi WebSocket Orderbook Updates: confirms snapshot-then-delta model for real-time orderbooks, useful after polling MVP. https://docs.kalshi.com/websockets/orderbook-updates
- scikit-learn probability calibration docs: confirms probability calibration semantics, calibration curves, and disjoint-data requirement when calibrating an already fitted classifier. https://scikit-learn.org/stable/modules/calibration.html
- scikit-learn `TimeSeriesSplit` docs: confirms chronological train/test behavior and warns that ordinary CV is inappropriate for time-ordered data because it can train on future data and evaluate on past data. https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html

## Research Notes

- The `gsd-tools` executable was not on PATH, so confidence checks were run through `/Users/andrewlay/.codex/gsd-core/bin/gsd-tools.cjs`. `classify-confidence --provider websearch --verified` returned `MEDIUM`; `webfetch --verified` returned `LOW`. Because the core claims are cross-checked against official/current docs and project constraints, this file uses MEDIUM overall confidence rather than treating any single fetched page as authoritative.
- Exact Kalshi tennis series/event naming was not verified here. The architecture therefore keeps market discovery and market mapping separate so a later phase can adapt to the actual available market taxonomy without changing model or feature-store boundaries.
