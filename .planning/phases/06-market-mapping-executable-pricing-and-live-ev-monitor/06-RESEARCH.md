# Phase 06: Market Mapping, Executable Pricing, and Live EV Monitor - Research

**Researched:** 2026-06-20
**Domain:** Kalshi ATP market-to-match mapping, bid-only orderbook to executable-side pricing, and read-only live/shadow EV monitoring [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] [CITED: .planning/REQUIREMENTS.md]
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Player identity normalization and alias governance
- **D-01:** Cross-source player matching must start from a deterministic normalized-name key: lowercase, ASCII/diacritic-folded text with punctuation stripped and internal whitespace collapsed, while preserving the given-name/surname token order from the source string.
- **D-02:** Automatic player resolution is allowed only when normalization produces one unique canonical ATP player match or one explicit manual alias override. Fuzzy/token heuristics may rank review candidates, but they must never auto-accept ambiguous names.
- **D-03:** Manual alias overrides are additive mapping artifacts, not canonical-ID rewrites. Each override must record at least the raw market name, normalized market name, canonical player ID, canonical player name, source note, and created/updated timestamps so alias use is auditable.
- **D-04:** Phase 06 must not introduce player-merge logic or mutate Phase 01 canonical identities. If multiple canonical players remain plausible after normalization and alias review, the market stays unresolved.

### Market-to-match mapping evidence and rejection policy
- **D-05:** Eligible markets are limited to ATP head-to-head winner-style contracts that clearly refer to exactly two players and one match outcome. Futures, outrights, props, non-ATP events, and other contract shapes must be marked `excluded` rather than forced through the mapper.
- **D-06:** A market reaches `matched` status only when exactly one canonical ATP match satisfies all required evidence together: both market-side player names resolve uniquely, the player pair aligns to one canonical match, the market timing aligns to the match date window, and the title/subtitle semantics are consistent with player-side winner labeling.
- **D-07:** Mapping must fail closed into explicit states: `matched`, `ambiguous`, `unmatched`, or `excluded`. `ambiguous` means more than one plausible canonical match or unresolved side orientation; `unmatched` means the player pair or timing produced no valid canonical match; `excluded` means the contract is out of scope before matching.
- **D-08:** Every mapping attempt must persist its evidence payload: raw market strings, normalized player strings, alias hits, candidate canonical match IDs, final state, and rejection reason codes. The scorer must refuse to evaluate anything not in `matched`.

### Executable pricing and scoring input contract
- **D-09:** Phase 06 upgrades the Phase 04 normalized market-input contract from a single probability scalar to side-specific executable inputs. Buy-YES and buy-NO entry prices must come from executable orderbook asks for their respective sides; the negative side must not be derived from `1 - positive_side_price` once live Kalshi orderbooks are in scope.
- **D-10:** Midpoint, last-trade, and bid fields may be recorded as diagnostics, but executable EV scoring must use side-specific executable entry prices and sizes. If a side has no executable ask or no usable size, that side is unscorable.
- **D-11:** Liquidity for scoring must mean executable notional available at the chosen entry price level, with a clearly labeled source. If the implementation later aggregates multiple immediately executable levels, that aggregation must remain explicit in the source label and evidence payload.
- **D-12:** Freshness is defined from the persisted orderbook snapshot timestamp, not from market metadata alone. Phase 06 should treat snapshots older than 120 seconds as stale by default and therefore unscorable, while leaving the threshold configurable in the later operational-hardening phase.
- **D-13:** Phase 04's accepted/rejected audit pattern remains canonical. Any new executable-pricing adapter must preserve explicit price source, liquidity source, freshness age, fee/slippage assumptions, threshold snapshot, and reason-coded rejection output.
- **D-14:** Fee and slippage assumptions stay explicit contract fields, not hidden spread adjustments. The initial MVP scoring path should use the chosen executable entry price plus configurable per-contract fee/slippage inputs.

### Live/shadow scan behavior and ranked monitor output
- **D-15:** Phase 06 is shadow-first and read-only. The default operator flow should score the latest persisted Kalshi snapshot batch and existing trusted model artifacts without any order-preparation surfaces. A live-readonly path may collect fresh snapshots and immediately score them, but still remains strictly non-execution.
- **D-16:** A market is scorable only when mapping, feature/model versioning, and canonical match identity all align. Missing prediction rows, stale orderbooks, or unresolved mappings must emit explicit rejected/unscorable records instead of being silently skipped.
- **D-17:** Ranked opportunities must sort by expected value first, then edge, executable liquidity, confidence, and freshness. Operator-facing output must include ticker, canonical match ID, player pairing, selected side, model probability, executable entry price, price source, expected value, edge, executable liquidity, freshness age, mapping state/confidence, and any rejection reason summary.
- **D-18:** Phase 06 should persist both accepted and rejected scan outputs for auditability. Human-readable CLI output can default to the ranked accepted table plus summary counts for rejected or excluded records, while the full machine-readable record set remains available for later reporting and alerts.

### the agent's Discretion
- Choose the exact storage format and module split for alias overrides, mapping evidence tables, and executable-pricing adapters as long as the audit fields above remain explicit and version-controlled.
- Choose the exact candidate-ranking heuristic used to propose ambiguous-name review candidates, provided the heuristic never auto-accepts a non-unique match.
- Choose whether executable liquidity should use only the top ask level or a clearly labeled sum across immediately executable levels, provided the source label and evidence payload make the choice inspectable.

### Deferred Ideas (OUT OF SCOPE)
- UI-driven alias review and manual match-resolution tooling remain future work; this phase should stay CLI/file-based and auditable.
- Alert-channel delivery, polling hardening, and operator configuration depth belong to Phase 07.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MKT-01 | System normalizes player names from Sackmann and Kalshi into deterministic candidate identities. [CITED: .planning/REQUIREMENTS.md] | Reuse the repo’s canonical normalization style and make Phase 06 normalization a deterministic first-pass key, with RapidFuzz limited to review-only candidate ranking. [CITED: src/tennisprediction/domain/normalization.py] [CITED: https://rapidfuzz.github.io/RapidFuzz/Usage/utils.html] [CITED: https://rapidfuzz.github.io/RapidFuzz/Usage/process.html] |
| MKT-02 | System supports manual player alias overrides with auditable source and timestamp metadata. [CITED: .planning/REQUIREMENTS.md] | Store alias overrides as a versioned project artifact with raw name, normalized name, canonical player ID, canonical player name, note, and timestamps; do not mutate canonical player identities. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |
| MKT-03 | System maps Kalshi ATP markets to canonical ATP matches and player sides with matched, ambiguous, unmatched, and excluded states. [CITED: .planning/REQUIREMENTS.md] | Build a fail-closed resolver around canonical player IDs, canonical match IDs, title/subtitle semantics, and time-window evidence, with persisted evidence rows for every mapping attempt. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] [CITED: src/tennisprediction/modeling/datasets.py] |
| MKT-04 | System refuses to score ambiguous or unmatched Kalshi markets. [CITED: .planning/REQUIREMENTS.md] | Make the scorer accept only `matched` records and persist rejected/unscorable rows for `ambiguous`, `unmatched`, `excluded`, stale, or missing-prediction cases. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] [CITED: src/tennisprediction/ev/opportunity.py] |
| MKT-05 | System converts Kalshi yes/no prices and orderbook depth into a recorded market probability source. [CITED: .planning/REQUIREMENTS.md] | Phase 06 must replace the Phase 04 scalar-only assumption with an adapter that derives side-specific executable asks from Kalshi’s bid-only orderbook and records source labels explicitly. [CITED: src/tennisprediction/backtesting/schemas.py] [CITED: https://docs.kalshi.com/api-reference/market/get-market-orderbook] [CITED: https://docs.kalshi.com/getting_started/orderbook_responses] |
| MKT-06 | System calculates executable edge and expected value with price source, liquidity, freshness, and fee/slippage assumptions recorded. [CITED: .planning/REQUIREMENTS.md] | Extend the Phase 04 decision contract rather than bypassing it: preserve threshold snapshots, accepted/rejected record symmetry, and explicit freshness/liquidity evidence. [CITED: src/tennisprediction/ev/pricing.py] [CITED: src/tennisprediction/ev/opportunity.py] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |
| MKT-07 | System generates live or shadow-mode predictions by reusing the same feature and model interfaces used in training/backtesting. [CITED: .planning/REQUIREMENTS.md] | Reuse `load_model_artifact_bundle`, `materialize_modeling_dataset`, and the replay-style artifact/feature contracts rather than inventing a second model-serving path. [CITED: src/tennisprediction/modeling/registry.py] [CITED: src/tennisprediction/modeling/datasets.py] [CITED: src/tennisprediction/backtesting/replay.py] |
| MKT-08 | System ranks opportunities by expected value, edge, liquidity, confidence, and configured thresholds. [CITED: .planning/REQUIREMENTS.md] | Keep ranking downstream of mapping and executable-pricing normalization, then present accepted opportunities through the existing CLI surface with persisted accepted/rejected batches. [CITED: src/tennisprediction/cli.py] [CITED: src/tennisprediction/ev/opportunity.py] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- Scope remains ATP only; Phase 06 must reject or exclude WTA, Challenger, ITF, doubles, futures, and other non-ATP market shapes. [CITED: AGENTS.md] [CITED: .planning/REQUIREMENTS.md]
- Scope remains Kalshi only; do not introduce venue-generic abstractions or execution surfaces. [CITED: AGENTS.md]
- Chronological leakage prevention remains locked; live or shadow scoring must reuse existing feature/model contracts rather than recomputing tennis state ad hoc. [CITED: AGENTS.md] [CITED: src/tennisprediction/features/persistence.py] [CITED: src/tennisprediction/backtesting/replay.py]
- Calibrated probabilities remain mandatory; Phase 06 must consume trusted model artifacts, not raw classifier scores only. [CITED: AGENTS.md] [CITED: src/tennisprediction/modeling/registry.py]
- Backtesting evidence remains a phase gate; Phase 06 can rank read-only opportunities, but it must preserve the audit surfaces needed for later replay validation and reporting. [CITED: AGENTS.md] [CITED: src/tennisprediction/ev/opportunity.py]
- Engineering quality remains mandatory: modular, typed, logged, configurable, reproducible code with focused unit tests for critical mapping, pricing, and rejection logic. [CITED: AGENTS.md]
- Repo-local path discipline remains part of the existing implementation pattern; new alias artifacts, evidence files, and reports should stay inside repository-managed paths. [CITED: src/tennisprediction/config.py]

## Summary

Phase 06 should be planned as a strict bridge between Phase 05’s read-only Kalshi snapshot surface and Phase 04’s EV decision engine. The current repository already has typed Kalshi DTOs, persisted orderbook snapshots, a trusted artifact loader, and accepted/rejected EV records; what is missing is the deterministic mapping layer plus the adapter that turns Kalshi’s bid-only binary orderbook into side-specific executable pricing inputs. [CITED: src/tennisprediction/kalshi/schemas.py] [CITED: src/tennisprediction/kalshi/snapshots.py] [CITED: src/tennisprediction/modeling/registry.py] [CITED: src/tennisprediction/ev/opportunity.py]

The highest-risk planning mistake is carrying Phase 04’s normalized scalar `market_probability` contract forward unchanged. Kalshi’s orderbook returns bids only, with executable asks implied by reciprocal yes/no relationships, so Phase 06 must explicitly model buy-YES and buy-NO entry prices, entry sizes, freshness age, and source labels before any EV ranking is trusted. [CITED: src/tennisprediction/backtesting/schemas.py] [CITED: https://docs.kalshi.com/api-reference/market/get-market-orderbook] [CITED: https://docs.kalshi.com/getting_started/orderbook_responses] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]

The safest delivery order is `mapping contracts and evidence -> executable pricing adapter -> read-only shadow/live scan orchestration`. That sequence matches the locked decision set: ambiguous or unmatched markets must fail closed, executable pricing must preserve evidence, and the final operator view must rank only fully matched and scorable opportunities while still persisting all rejected or excluded rows. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]

**Primary recommendation:** Plan Phase 06 as three vertical slices: deterministic player and market mapping, bid-only orderbook to executable-side pricing, and a read-only ranked monitor that reuses Phase 03/04 artifact and EV interfaces end to end. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] [CITED: src/tennisprediction/backtesting/replay.py] [CITED: src/tennisprediction/ev/opportunity.py]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Deterministic player normalization and alias lookup | API / Backend | Database / Storage | The resolver logic belongs in backend code, but alias artifacts and evidence must persist for audit. [CITED: src/tennisprediction/domain/normalization.py] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |
| Market-to-canonical-match resolution | API / Backend | Database / Storage | Matching requires project rules, canonical IDs, and persisted rejection evidence, not UI logic. [CITED: src/tennisprediction/modeling/datasets.py] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |
| Executable ask/liquidity derivation from orderbook snapshots | API / Backend | Database / Storage | The adapter is domain logic over persisted Kalshi orderbook rows, and it must emit evidence-rich normalized inputs. [CITED: src/tennisprediction/kalshi/snapshots.py] [CITED: https://docs.kalshi.com/getting_started/orderbook_responses] |
| Trusted artifact replay and prediction reuse | API / Backend | Database / Storage | The live/shadow path should load the same artifact bundle and use the same canonical match contracts as replay. [CITED: src/tennisprediction/backtesting/replay.py] [CITED: src/tennisprediction/modeling/registry.py] |
| Ranked operator monitor output | API / Backend | — | The current surface is Typer CLI plus persisted reports, not a browser tier. [CITED: src/tennisprediction/cli.py] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `tennisprediction.kalshi.*` | repo-local | Source of truth for Kalshi DTOs, request metadata, snapshot rows, and persisted orderbook inputs. [CITED: src/tennisprediction/kalshi/schemas.py] [CITED: src/tennisprediction/kalshi/snapshots.py] | Phase 05 already established the project-owned transport boundary; Phase 06 should extend it instead of bypassing it. [CITED: src/tennisprediction/kalshi/client.py] [CITED: src/tennisprediction/kalshi/storage.py] |
| `tennisprediction.backtesting.replay` + `tennisprediction.modeling.registry` | repo-local | Trusted artifact loading and replay-style prediction reuse. [CITED: src/tennisprediction/backtesting/replay.py] [CITED: src/tennisprediction/modeling/registry.py] | This is the existing validated model-serving seam in the repo; Phase 06 should not create a second one. [CITED: tests/unit/test_backtesting_replay.py] |
| `tennisprediction.ev.pricing` + `tennisprediction.ev.opportunity` | repo-local | Canonical EV math, threshold snapshots, and accepted/rejected audit records. [CITED: src/tennisprediction/ev/pricing.py] [CITED: src/tennisprediction/ev/opportunity.py] | Phase 06 needs to upgrade inputs, not replace the EV record surface that Phase 04 already established. [CITED: src/tennisprediction/backtesting/schemas.py] |
| `RapidFuzz` [WARNING: flagged as suspicious — verify before using.] | `3.14.5` [CITED: https://pypi.org/project/RapidFuzz/] | Review-only candidate scoring for ambiguous player-name matching after deterministic normalization. [CITED: https://rapidfuzz.github.io/RapidFuzz/Usage/process.html] | Official docs support configurable scorers and preprocessing, which fits the locked rule that fuzzy logic may rank candidates but must never auto-accept ambiguity. [CITED: https://rapidfuzz.github.io/RapidFuzz/Usage/process.html] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `httpx` | `0.28.1` current on PyPI. [CITED: local `python3 -m pip index versions httpx` probe on 2026-06-20] [CITED: pyproject.toml] | Reuse the existing Kalshi read client when the operator wants fresh live-readonly snapshots before scoring. [CITED: src/tennisprediction/kalshi/client.py] | Use for immediate fresh collection; skip it for pure shadow-mode scoring from the latest persisted batch. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |
| `pydantic` | `2.13.4` current on PyPI. [CITED: local `python3 -m pip index versions pydantic` probe on 2026-06-20] [CITED: pyproject.toml] | Validate alias override rows, mapping evidence DTOs, executable-pricing inputs, and scan settings. [CITED: pyproject.toml] | Use anywhere Phase 06 introduces new persisted or operator-facing contracts. [CITED: AGENTS.md] |
| `DuckDB` | `1.5.x` project target; `1.5.4` current on PyPI. [CITED: pyproject.toml] [CITED: local `python3 -m pip index versions duckdb` probe on 2026-06-20] | Query canonical matches, feature rows, Kalshi snapshots, and persisted mapping evidence in one local store. [CITED: src/tennisprediction/modeling/datasets.py] [CITED: src/tennisprediction/kalshi/storage.py] | Use for evidence tables and scan outputs; do not introduce a second storage engine for this phase. [CITED: AGENTS.md] |
| `Typer` | `0.26.7` current on PyPI. [CITED: local `python3 -m pip index versions typer` probe on 2026-06-20] [CITED: pyproject.toml] | Extend the project CLI with mapping review, scan, and ranked monitor commands. [CITED: src/tennisprediction/cli.py] | Use for operator entrypoints rather than one-off scripts. [CITED: AGENTS.md] |
| `Rich` | `15.0.0` current on PyPI. [CITED: local `python3 -m pip index versions rich` probe on 2026-06-20] [CITED: pyproject.toml] | Render ranked opportunity tables and rejected/excluded summary counts. [CITED: pyproject.toml] | Use for the human-readable monitor surface; keep the full machine-readable record set persisted separately. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `RapidFuzz` review-only candidate scoring | Python `difflib` [ASSUMED] | `difflib` avoids a new dependency, but RapidFuzz gives maintained scoring APIs and preprocessing hooks that better fit auditable candidate review. [CITED: https://rapidfuzz.github.io/RapidFuzz/Usage/process.html] [ASSUMED] |
| REST snapshot reuse plus optional immediate fresh collection | WebSocket-first live monitor | WebSockets are supported by Kalshi, but Phase 06 is shadow-first and read-only; Phase 05 already built REST snapshot persistence, while Phase 07 owns polling and operational hardening. [CITED: https://docs.kalshi.com/websockets/websocket-connection] [CITED: .planning/phases/05-kalshi-read-only-market-integration/05-03-SUMMARY.md] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |
| Project-owned executable-pricing adapter in front of the existing EV engine | Embedding orderbook parsing directly inside `evaluate_opportunities()` | Direct embedding would blur transport, pricing, and decision responsibilities and make Phase 04’s audit surface harder to preserve. [CITED: src/tennisprediction/ev/opportunity.py] [CITED: src/tennisprediction/kalshi/snapshots.py] |

**Installation:**
```bash
# after checkpoint:human-verify for RapidFuzz
uv add RapidFuzz
```

**Version verification:**
```bash
python3 -m pip index versions RapidFuzz
python3 -m pip index versions duckdb
python3 -m pip index versions httpx
python3 -m pip index versions typer
python3 -m pip index versions rich
python3 -m pip index versions pydantic
```

## Package Legitimacy Audit

> **Required** whenever this phase installs external packages. Run the Package Legitimacy Gate protocol before completing this section.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `RapidFuzz` | PyPI [CITED: https://pypi.org/project/RapidFuzz/] | ~10 weeks; released 2026-04-07. [CITED: https://pypi.org/project/RapidFuzz/] | unknown from seam. [CITED: `gsd-tools query package-legitimacy check --ecosystem pypi RapidFuzz` on 2026-06-20] | `github.com/maxbachmann/RapidFuzz`. [CITED: https://pypi.org/project/RapidFuzz/] | `SUS`. [CITED: `gsd-tools query package-legitimacy check --ecosystem pypi RapidFuzz` on 2026-06-20] | Flagged — planner must add `checkpoint:human-verify` before install. [CITED: `gsd-tools query package-legitimacy check --ecosystem pypi RapidFuzz` on 2026-06-20] |

**Packages removed due to [SLOP] verdict:** none. [CITED: `gsd-tools query package-legitimacy check --ecosystem pypi RapidFuzz` on 2026-06-20]
**Packages flagged as suspicious [SUS]:** `RapidFuzz` — planner inserts `checkpoint:human-verify` before install. [CITED: `gsd-tools query package-legitimacy check --ecosystem pypi RapidFuzz` on 2026-06-20]

*Packages discovered via WebSearch or training data that have not been verified against an authoritative source are tagged `[ASSUMED]` and the planner must gate each install behind a `checkpoint:human-verify` task.* [CITED: https://pypi.org/project/RapidFuzz/] [CITED: https://rapidfuzz.github.io/RapidFuzz/Usage/process.html]

## Architecture Patterns

### System Architecture Diagram

```text
DuckDB canonical tennis data
  canonical_matches
  feature_differential_rows
          |
          v
Trusted model artifact bundle
  manifest.json
  raw estimator
  calibrator
          |
          v
Kalshi snapshot storage
  market rows
  detail rows
  orderbook rows
          |
          v
Player normalization + alias lookup
  deterministic key
  manual override check
  review-only fuzzy candidates
          |
          v
Market mapper
  matched / ambiguous / unmatched / excluded
  persisted evidence + rejection codes
          |
          v
Executable pricing adapter
  derive YES ask from NO best bid
  derive NO ask from YES best bid
  attach size, freshness, fee/slippage, source labels
          |
          v
EV decision engine
  accepted + rejected records
  threshold snapshot
          |
          v
Ranked CLI monitor + persisted scan outputs
```

### Recommended Project Structure
```text
src/tennisprediction/
├── market_mapping/
│   ├── schemas.py        # alias rows, mapping evidence, mapping state enums
│   ├── aliases.py        # load/save auditable override artifacts
│   ├── normalization.py  # Kalshi-name normalization built to mirror repo style
│   └── resolver.py       # player + canonical-match resolution
├── kalshi/
│   └── executable.py     # bid-only orderbook -> side-specific executable inputs
├── monitoring/
│   ├── scan.py           # shadow/live-readonly orchestration
│   └── reports.py        # ranked tables and persisted scan outputs
└── cli.py                # new operator commands
```

### Pattern 1: Deterministic First, Fuzzy Only for Review
**What:** Normalize names deterministically, check explicit alias overrides, then use fuzzy scoring only to rank unresolved candidates for audit or CLI review. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] [CITED: src/tennisprediction/domain/normalization.py]  
**When to use:** For every Kalshi-side player string before match resolution. [CITED: .planning/REQUIREMENTS.md]  
**Example:**
```python
# Source: RapidFuzz docs + Phase 06 locked decisions
from rapidfuzz import fuzz, process, utils

def rank_candidates(raw_name: str, canonical_names: dict[str, str]) -> tuple[str, float, str] | None:
    match = process.extractOne(
        raw_name,
        canonical_names,
        scorer=fuzz.token_ratio,
        processor=utils.default_process,
        score_cutoff=85,
    )
    if match is None:
        return None
    resolved_name, score, canonical_player_id = match
    return resolved_name, float(score), canonical_player_id
```

### Pattern 2: Derive Executable Asks from the Reciprocal Bid Ladder
**What:** Convert Kalshi’s bid-only orderbook into side-specific executable buy prices and sizes without hiding which reciprocal rule produced the value. [CITED: https://docs.kalshi.com/api-reference/market/get-market-orderbook] [CITED: https://docs.kalshi.com/getting_started/orderbook_responses]  
**When to use:** For every `matched` market before it is passed into EV scoring. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]  
**Example:**
```python
# Source: Kalshi orderbook docs + repo DTO orderbook contract
from decimal import Decimal

ONE_DOLLAR = Decimal("1.00")

def best_yes_ask_from_orderbook(orderbook):
    if not orderbook.no_levels:
        return None
    best_no_bid = orderbook.no_levels[-1]  # docs: highest bid is last element
    return {
        "entry_price": ONE_DOLLAR - best_no_bid.price_dollars,
        "entry_size": best_no_bid.quantity_fp,
        "price_source": "implied_yes_ask_from_no_best_bid",
    }

def best_no_ask_from_orderbook(orderbook):
    if not orderbook.yes_levels:
        return None
    best_yes_bid = orderbook.yes_levels[-1]
    return {
        "entry_price": ONE_DOLLAR - best_yes_bid.price_dollars,
        "entry_size": best_yes_bid.quantity_fp,
        "price_source": "implied_no_ask_from_yes_best_bid",
    }
```

### Pattern 3: Reuse Replay-Style Prediction Interfaces for Live/Shadow Scans
**What:** Keep Phase 06 scoring on the same artifact and EV interfaces already used in replay. [CITED: src/tennisprediction/backtesting/replay.py] [CITED: src/tennisprediction/ev/opportunity.py]  
**When to use:** For both latest-snapshot shadow scans and immediate fresh live-readonly scans. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]  
**Example:**
```python
# Source: current repo replay + opportunity contracts
replay = replay_model_predictions(
    artifact_dir=artifact_dir,
    database_path=database_path,
    expected_feature_version=feature_version,
    expected_split_manifest_id=split_manifest_id,
)

decision_batch = evaluate_opportunities(
    replay.rows,
    normalized_market_inputs,
    thresholds,
    run_id="shadow-scan",
)
```

### Anti-Patterns to Avoid
- **Auto-accepting fuzzy matches:** Fuzzy scoring may rank candidates, but it must never auto-resolve ambiguous players. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]
- **Scoring from `updated_time` alone:** Freshness is locked to persisted snapshot age, not market metadata. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] [CITED: src/tennisprediction/kalshi/snapshots.py]
- **Treating Kalshi orderbooks as if asks are explicit:** The API returns bids only; executable asks must be derived and source-labeled. [CITED: https://docs.kalshi.com/api-reference/market/get-market-orderbook] [CITED: https://docs.kalshi.com/getting_started/orderbook_responses]
- **Bypassing accepted/rejected record symmetry:** Unscorable markets must persist as rejected or excluded rows, not disappear from outputs. [CITED: src/tennisprediction/ev/opportunity.py] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]
- **Mutating canonical player identities:** Manual aliasing is additive only and must not rewrite Phase 01 canonical IDs. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Review-only fuzzy candidate scoring | Custom edit-distance or token-overlap code [ASSUMED] | `RapidFuzz` with explicit processor and scorer configuration. [CITED: https://rapidfuzz.github.io/RapidFuzz/Usage/process.html] | String matching edge cases accumulate quickly; a maintained scorer lets Phase 06 focus on audit policy rather than distance algorithms. [CITED: https://rapidfuzz.github.io/RapidFuzz/Usage/process.html] [ASSUMED] |
| Artifact-serving path for live scoring | A second model-serving interface | Existing replay/model bundle loaders and Phase 04 EV contracts. [CITED: src/tennisprediction/backtesting/replay.py] [CITED: src/tennisprediction/modeling/registry.py] [CITED: src/tennisprediction/ev/opportunity.py] | A second path would break parity between training, backtesting, and live/shadow scans. [CITED: src/tennisprediction/backtesting/replay.py] |
| Kalshi-side transport parsing in EV code | Raw payload handling inside the scoring engine | Phase 05 DTO and snapshot layers plus a separate executable-pricing adapter. [CITED: src/tennisprediction/kalshi/client.py] [CITED: src/tennisprediction/kalshi/snapshots.py] | Keeping transport, pricing, and decision logic separate preserves testability and clearer rejection evidence. [CITED: src/tennisprediction/ev/opportunity.py] |

**Key insight:** the complexity in this phase is not the EV arithmetic; it is preserving auditable identity, orientation, and executable-price evidence all the way into the existing accepted/rejected record surface. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] [CITED: src/tennisprediction/ev/opportunity.py]

## Common Pitfalls

### Pitfall 1: Side-Orientation Inversion
**What goes wrong:** The model probability for `player_a_win` gets compared to the wrong Kalshi side, inverting edge and EV. [CITED: src/tennisprediction/modeling/datasets.py] [CITED: https://docs.kalshi.com/getting_started/orderbook_responses]  
**Why it happens:** Phase 04 uses a normalized positive-side scalar, while Kalshi market labels and executable entry prices are side-specific. [CITED: src/tennisprediction/backtesting/schemas.py] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]  
**How to avoid:** Persist both mapping-side evidence and executable-side source labels before calling EV code. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]  
**Warning signs:** Negative-side opportunities disappear unexpectedly or accepted records cluster on one side only. [ASSUMED]

### Pitfall 2: Auto-Resolving Duplicate or Ambiguous Names
**What goes wrong:** Markets with duplicate surnames, noisy initials, or rematches map to the wrong canonical player or match. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]  
**Why it happens:** Deterministic normalization and audit overrides are skipped in favor of fuzzy-first matching. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]  
**How to avoid:** Require a unique deterministic or override-backed resolution before any market reaches `matched`. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]  
**Warning signs:** Alias files start behaving like canonical-ID rewrites or many markets map without persisted evidence. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]

### Pitfall 3: Treating Bid-Only Orderbooks as Executable Asks
**What goes wrong:** The scanner uses `yes_bid` or `no_bid` as a buy price, overstating executable EV. [CITED: https://docs.kalshi.com/api-reference/market/get-market-orderbook]  
**Why it happens:** Kalshi exposes bid ladders only, and the reciprocal side has to be reconstructed deliberately. [CITED: https://docs.kalshi.com/getting_started/orderbook_responses]  
**How to avoid:** Derive buy-YES from the best NO bid and buy-NO from the best YES bid, then record the exact source label. [CITED: https://docs.kalshi.com/getting_started/orderbook_responses] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]  
**Warning signs:** The same market appears to have profitable YES and NO buys at the same time. [ASSUMED]

### Pitfall 4: Silent Skips Instead of Rejected Records
**What goes wrong:** Missing predictions, stale orderbooks, or unresolved mappings disappear from the monitor, making operator trust worse. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]  
**Why it happens:** The scan path behaves like an ad hoc filter instead of using the established accepted/rejected record model. [CITED: src/tennisprediction/ev/opportunity.py]  
**How to avoid:** Persist rejected/unscorable rows with explicit reason codes and summary counts. [CITED: src/tennisprediction/ev/opportunity.py] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]  
**Warning signs:** Operator totals fail to reconcile with the number of open Kalshi ATP markets. [ASSUMED]

## Code Examples

Verified patterns from official and repo sources:

### RapidFuzz Preprocessing Hook
```python
# Source: https://rapidfuzz.github.io/RapidFuzz/Usage/process.html
from rapidfuzz import fuzz, process, utils

process.extractOne(
    "N. Djokovic",
    ["Novak Djokovic", "Djokovic Novak"],
    scorer=fuzz.token_ratio,
    processor=utils.default_process,
)
```

### Bid-Only Orderbook Interpretation
```python
# Source: https://docs.kalshi.com/getting_started/orderbook_responses
def implied_no_ask_from_yes_bid(best_yes_bid: float) -> float:
    return 1.0 - best_yes_bid

def implied_yes_ask_from_no_bid(best_no_bid: float) -> float:
    return 1.0 - best_no_bid
```

### Trusted Artifact Replay Entry Point
```python
# Source: src/tennisprediction/backtesting/replay.py
result = replay_model_predictions(
    artifact_dir=artifact_dir,
    database_path=database_path,
    expected_feature_version=feature_version,
    expected_split_manifest_id=split_manifest_id,
)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| One normalized positive-side `market_probability` scalar | Side-specific executable buy inputs with price source, size, freshness, and liquidity evidence. [CITED: src/tennisprediction/backtesting/schemas.py] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] | Phase 06 scope lock on 2026-06-20. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] | The planner must treat executable pricing as a first-class adapter, not a small schema tweak. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |
| Fuzzy-first market matching [ASSUMED] | Deterministic normalization, auditable alias overrides, and review-only candidate ranking. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] | Phase 06 locked decisions D-01 to D-04. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] | Duplicate names and ambiguous titles now fail closed instead of leaking silent scoring errors. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |
| Separate ad hoc live scoring path [ASSUMED] | Same artifact and EV interfaces reused across backtesting and read-only live/shadow scans. [CITED: src/tennisprediction/backtesting/replay.py] [CITED: src/tennisprediction/ev/opportunity.py] | Phase 06 recommendation based on existing repo seams. [CITED: src/tennisprediction/backtesting/replay.py] | Planner can preserve parity and shrink future debugging scope. [CITED: src/tennisprediction/backtesting/replay.py] |

**Deprecated/outdated:**
- Treating Kalshi `updated_time` or midpoint diagnostics as sufficient for executable pricing is outdated for this phase; executable side-specific entry evidence is now required. [CITED: https://docs.kalshi.com/api-reference/market/get-market] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `difflib` is the only realistic stdlib alternative worth mentioning to RapidFuzz for review-only candidate ranking. [ASSUMED] | Standard Stack / Alternatives Considered | Low — it only affects the alternatives discussion, not the recommended plan. |
| A2 | Warning signs such as “both sides profitable at once” and “totals do not reconcile” are useful early indicators for scoring bugs. [ASSUMED] | Common Pitfalls | Low — they are operational heuristics, not implementation contracts. |
| A3 | Phase 06 should not add a separate ad hoc live scoring path. [ASSUMED] | State of the Art | Medium — if later constraints require online-only features, the planner may need an extra abstraction layer. |

## Open Questions (RESOLVED)

1. **Executable liquidity default**
   - Resolution: MVP executable liquidity should default to top-of-book only. This preserves D-11's explicit-source requirement, minimizes hidden slippage assumptions, and still leaves room for later multi-level aggregation under a different `liquidity_source` label. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] [ASSUMED]

2. **Market-to-match timing alignment window**
   - Resolution: MVP timing alignment should start with same-date canonical-match matching only, with fail-closed reason-coded misses instead of automatically widening the window. A configurable fallback can be introduced later only if real Kalshi ATP winner titles prove same-date matching insufficient. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python virtualenv | Repo code, tests, CLI | ✓ [CITED: local `.venv/bin/python --version` probe on 2026-06-20] | `3.12.4`. [CITED: local `.venv/bin/python --version` probe on 2026-06-20] | — |
| `uv` CLI | Preferred dependency sync workflow from project stack | ✗ on `PATH`. [CITED: local `command -v uv` probe on 2026-06-20] | — | No equivalent repo-standard fallback is documented; planner should add an environment bootstrap step if validation requires dependency changes. [CITED: AGENTS.md] [CITED: pyproject.toml] |
| Phase 03/04 ML runtime (`joblib`, `pandas`, `scikit-learn`, `xgboost`) | Trusted artifact replay and live/shadow prediction reuse | ✗ in current `.venv`. [CITED: local `.venv` import probe on 2026-06-20] | — | Install the `ml` dependency group before Phase 06 verification. [CITED: pyproject.toml] |
| `RapidFuzz` | Candidate ranking for unresolved player names | ✗ in current `.venv`. [CITED: local `.venv` import probe on 2026-06-20] | — | Add only after `checkpoint:human-verify`. [CITED: `gsd-tools query package-legitimacy check --ecosystem pypi RapidFuzz` on 2026-06-20] |
| Kalshi access key + RSA private key | Immediate fresh live-readonly snapshot collection | ✗ not provided in repo defaults. [CITED: src/tennisprediction/cli.py] [CITED: .env.example] | — | Shadow-mode can still score the latest persisted Kalshi snapshot batch without collecting fresh data. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |
| `pytest` | Validation and focused unit tests | ✓. [CITED: local `.venv/bin/python -m pytest --version` probe on 2026-06-20] | `9.1.0`. [CITED: local `.venv/bin/python -m pytest --version` probe on 2026-06-20] | — |

**Missing dependencies with no fallback:**
- `uv` CLI if the planner expects repo-standard dependency synchronization. [CITED: local `command -v uv` probe on 2026-06-20] [CITED: AGENTS.md]
- Phase 03/04 ML runtime in the current `.venv` if the planner expects immediate artifact replay verification. [CITED: local `.venv` import probe on 2026-06-20]

**Missing dependencies with fallback:**
- Kalshi credentials: latest persisted snapshot batches can still power shadow-mode scoring. [CITED: src/tennisprediction/cli.py] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.1.0`. [CITED: local `.venv/bin/python -m pytest --version` probe on 2026-06-20] |
| Config file | `pyproject.toml`. [CITED: pyproject.toml] |
| Quick run command | `./.venv/bin/python -m pytest -q tests/unit/test_kalshi_storage.py tests/unit/test_backtesting_decisions.py tests/unit/test_cli_smoke.py -x` [CITED: tests/unit/test_kalshi_storage.py] [CITED: tests/unit/test_backtesting_decisions.py] [CITED: tests/unit/test_cli_smoke.py] |
| Full suite command | `./.venv/bin/python -m pytest -q` [CITED: pyproject.toml] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MKT-01 | Deterministic Kalshi/Sackmann name normalization | unit | `./.venv/bin/python -m pytest -q tests/unit/test_market_mapping_normalization.py -x` | ❌ Wave 0 |
| MKT-02 | Auditable manual alias overrides | unit | `./.venv/bin/python -m pytest -q tests/unit/test_market_mapping_aliases.py -x` | ❌ Wave 0 |
| MKT-03 | Matched / ambiguous / unmatched / excluded market resolution | unit | `./.venv/bin/python -m pytest -q tests/unit/test_market_mapping_resolver.py -x` | ❌ Wave 0 |
| MKT-04 | Refuse to score unresolved markets | unit | `./.venv/bin/python -m pytest -q tests/unit/test_live_scan_rejections.py -x` | ❌ Wave 0 |
| MKT-05 | Bid-only orderbook to recorded price source conversion | unit | `./.venv/bin/python -m pytest -q tests/unit/test_kalshi_executable_pricing.py -x` | ❌ Wave 0 |
| MKT-06 | EV record includes price source, liquidity, freshness, fee/slippage assumptions | unit | `./.venv/bin/python -m pytest -q tests/unit/test_live_scan_pricing_contract.py -x` | ❌ Wave 0 |
| MKT-07 | Live/shadow scans reuse trusted artifact and feature interfaces | integration | `./.venv/bin/python -m pytest -q tests/unit/test_live_scan_orchestration.py -x` | ❌ Wave 0 |
| MKT-08 | Ranked opportunities ordered by EV, edge, liquidity, confidence, freshness thresholds | unit | `./.venv/bin/python -m pytest -q tests/unit/test_live_monitor_reports.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `./.venv/bin/python -m pytest -q tests/unit/test_market_mapping_normalization.py tests/unit/test_kalshi_executable_pricing.py -x` [ASSUMED]
- **Per wave merge:** `./.venv/bin/python -m pytest -q tests/unit/test_market_mapping_aliases.py tests/unit/test_market_mapping_resolver.py tests/unit/test_live_scan_orchestration.py -x` [ASSUMED]
- **Phase gate:** `./.venv/bin/python -m pytest -q` after the missing ML runtime is installed. [CITED: local `.venv` import probe on 2026-06-20] [CITED: pyproject.toml]

### Wave 0 Gaps
- [ ] `tests/unit/test_market_mapping_normalization.py` — covers `MKT-01`
- [ ] `tests/unit/test_market_mapping_aliases.py` — covers `MKT-02`
- [ ] `tests/unit/test_market_mapping_resolver.py` — covers `MKT-03`
- [ ] `tests/unit/test_kalshi_executable_pricing.py` — covers `MKT-05` and `MKT-06`
- [ ] `tests/unit/test_live_scan_orchestration.py` — covers `MKT-04` and `MKT-07`
- [ ] `tests/unit/test_live_monitor_reports.py` — covers `MKT-08`
- [ ] Install ML runtime from the `ml` dependency group before running full replay-backed verification. [CITED: pyproject.toml] [CITED: local `.venv` import probe on 2026-06-20]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 06 is an operator CLI and read-only scan flow, not an end-user auth surface. [CITED: src/tennisprediction/cli.py] |
| V3 Session Management | no | No user session layer is introduced in this phase. [CITED: src/tennisprediction/cli.py] |
| V4 Access Control | no | Repo-local CLI commands run under the operator’s local environment; no separate authorization layer exists here. [CITED: src/tennisprediction/cli.py] |
| V5 Input Validation | yes | Use typed DTOs and explicit enums for alias rows, mapping states, executable-pricing records, and scan settings. [CITED: pyproject.toml] [CITED: src/tennisprediction/kalshi/schemas.py] |
| V6 Cryptography | yes | Reuse the existing Kalshi request-signing path via `cryptography`; do not reimplement signing or handshake logic in Phase 06. [CITED: src/tennisprediction/kalshi/client.py] [CITED: https://docs.kalshi.com/getting_started/api_keys] [CITED: https://docs.kalshi.com/websockets/websocket-connection] |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious or mistaken alias override maps a market name to the wrong canonical player | Tampering | Keep overrides additive, schema-validated, version-controlled, and timestamped with operator notes. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] [CITED: pyproject.toml] |
| Stale orderbook snapshot gets scored as if it were fresh | Tampering | Compute freshness from persisted `collected_at_utc` and reject anything beyond the configured threshold. [CITED: src/tennisprediction/kalshi/snapshots.py] [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] |
| Model-side / market-side inversion produces false edge | Tampering | Require explicit side-orientation evidence and unit tests for positive and negative executable entry derivation. [CITED: src/tennisprediction/modeling/datasets.py] [CITED: https://docs.kalshi.com/getting_started/orderbook_responses] |
| Out-of-scope or unmatched markets are silently accepted | Elevation of Privilege | Fail closed to `excluded`, `ambiguous`, or `unmatched`, then persist rejected rows with reason codes. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] [CITED: src/tennisprediction/ev/opportunity.py] |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md` - locked decisions, discretion, and deferred scope for Phase 06.
- `src/tennisprediction/kalshi/schemas.py`, `src/tennisprediction/kalshi/snapshots.py`, `src/tennisprediction/kalshi/storage.py` - current Kalshi DTO and snapshot seams.
- `src/tennisprediction/backtesting/replay.py`, `src/tennisprediction/backtesting/schemas.py`, `src/tennisprediction/ev/opportunity.py`, `src/tennisprediction/ev/pricing.py` - current replay and EV contract seams.
- `src/tennisprediction/modeling/registry.py`, `src/tennisprediction/modeling/datasets.py`, `src/tennisprediction/cli.py` - trusted artifact, canonical match, and CLI integration seams.

### Secondary (MEDIUM confidence)
- `https://docs.kalshi.com/api-reference/market/get-market` - current market object fields and side-label metadata.
- `https://docs.kalshi.com/api-reference/market/get-market-orderbook` - bid-only orderbook endpoint shape and reciprocal-side semantics.
- `https://docs.kalshi.com/getting_started/orderbook_responses` - array ordering, best-bid interpretation, and reciprocal ask rules.
- `https://docs.kalshi.com/getting_started/api_keys` - request signing rules and path-without-query requirement.
- `https://docs.kalshi.com/websockets/websocket-connection` - authenticated WebSocket requirement for future live market subscriptions.
- `https://rapidfuzz.github.io/RapidFuzz/Usage/process.html` and `https://rapidfuzz.github.io/RapidFuzz/Usage/utils.html` - candidate scoring and preprocessing hooks.
- `https://pypi.org/project/RapidFuzz/` - current RapidFuzz release, maintainer links, and release date.

### Tertiary (LOW confidence)
- `gsd-tools query package-legitimacy check --ecosystem pypi RapidFuzz` on 2026-06-20 - legitimacy seam output flagged `RapidFuzz` as `SUS` because metadata signals were unavailable.
- Local environment and registry probes on 2026-06-20 - `.venv` package availability, `uv` on `PATH`, `pytest` version, and `python3 -m pip index versions` checks for `RapidFuzz`, `duckdb`, `httpx`, `typer`, `rich`, `pydantic`, `APScheduler`, and `kalshi-python`.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - repo seams and official docs are clear, but the only new dependency (`RapidFuzz`) is seam-flagged `SUS` and the current workspace is missing parts of the ML runtime. [CITED: `gsd-tools query package-legitimacy check --ecosystem pypi RapidFuzz` on 2026-06-20] [CITED: local `.venv` import probe on 2026-06-20]
- Architecture: HIGH - the phase boundary and integration points are strongly constrained by locked decisions and existing repo contracts. [CITED: .planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md] [CITED: src/tennisprediction/ev/opportunity.py]
- Pitfalls: HIGH - the failure modes follow directly from official Kalshi orderbook semantics plus the current Phase 04 scalar contract. [CITED: https://docs.kalshi.com/getting_started/orderbook_responses] [CITED: src/tennisprediction/backtesting/schemas.py]

**Research date:** 2026-06-20
**Valid until:** 2026-06-27 for Kalshi API/package-currentness checks; 2026-07-20 for repo-architecture findings. [CITED: https://docs.kalshi.com/api-reference/market/get-market] [CITED: https://pypi.org/project/RapidFuzz/]
