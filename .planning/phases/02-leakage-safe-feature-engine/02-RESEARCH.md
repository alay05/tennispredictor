# Phase 2: Leakage-Safe Feature Engine - Research

**Researched:** 2026-06-16  
**Domain:** Chronological ATP feature generation, point-in-time ranking/state lookup, and leakage verification [CITED: .planning/ROADMAP.md][CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Feature generation must emit each match's pre-match snapshot before any state update from that match is applied.
- **D-02:** Ranking features must use the latest ranking row with `ranking_date <= tourney_date`; never look ahead beyond the match's tournament date boundary.
- **D-03:** Chronological processing order must be deterministic: `tourney_date`, then round precedence, then stable source tie-breakers (`source_file_path`, `source_row_number`).
- **D-04:** Matches that are effectively concurrent within the same round/day must not update each other's pre-match state; same-round cohorts should use a shared pre-round baseline when exact intra-round order is not trustworthy.
- **D-05:** Every persisted feature snapshot must carry `feature_version`, `canonical_match_id`, `player_a_id`, `player_b_id`, `as_of_date`, source snapshot lineage, and side orientation so downstream training/prediction code never reconstructs provenance ad hoc.
- **D-06:** Persist both player-level pre-match state and the final differential feature row shape; later phases should consume stored contracts rather than recomputing differentials independently.
- **D-07:** Feature snapshots must include availability metadata and sample/exposure counts for sparse features, not just the final numeric rates.
- **D-08:** Missing rankings, missing match stats, and sparse H2H/form windows stay in-scope; they should produce null-or-empty feature values plus explicit missingness indicators rather than excluding the match.
- **D-09:** Rate features derived from sparse history should ship with exposure counts and use shrinkage/minimum-sample safeguards in implementation; never treat one-match rates as equally trustworthy to deep histories.
- **D-10:** Match-stat missingness from older eras or incomplete coverage must remain visible in the feature contract so later models can learn or filter on availability instead of silently receiving zeros.
- **D-11:** Phase 2 should persist audit state history, not only final feature snapshots. At minimum, keep pre-match state records that allow Elo, surface Elo, form, H2H, and aggregate calculations to be inspected after the fact.
- **D-12:** The feature engine is the single source of truth for stateful tennis features. Training, backtests, and live prediction must consume persisted snapshots/state instead of recomputing Elo, rankings, H2H, or rolling stats elsewhere.

### the agent's Discretion
- Choose the exact file/module split for the chronological runner, state stores, and feature schemas as long as the single-source-of-truth and auditability rules above are preserved.
- Choose the exact representation of round precedence and shrinkage formulas during planning/research as long as same-round leakage is prevented and sparse-feature confidence remains explicit.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FEAT-01 | System builds features by iterating matches chronologically and emitting pre-match snapshots before updating post-match state. [CITED: .planning/REQUIREMENTS.md] | Use a cohort-aware runner that emits player-side snapshots first, then applies state updates only after the cohort completes. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |
| FEAT-02 | System maintains overall Elo and hard/clay/grass surface Elo ratings for ATP players. [CITED: .planning/REQUIREMENTS.md] | Keep Elo in a dedicated mutable state store keyed by player and surface, and persist pre/post values for audit. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |
| FEAT-03 | System computes ranking, ranking-points, and ranking-change features using only rankings available before match date. [CITED: .planning/REQUIREMENTS.md] | Use a per-player backward `join_asof` on sorted ranking snapshots; never use nearest or forward lookup. Define `ranking_change` as the selected pre-match rank minus the immediately previous available ranking-row rank for that player, and persist the previous ranking date/value inputs for provenance. [CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html][CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |
| FEAT-04 | System computes recent-form features for last 5, 10, and 20 prior matches. [CITED: .planning/REQUIREMENTS.md] | Compute prior-only windows from sorted per-player streams using lagged/grouped operations and persist exposure counts. [CITED: https://docs.pola.rs/api/python/dev/reference/expressions/api/polars.Expr.shift.html][CITED: https://docs.pola.rs/user-guide/expressions/window-functions/] |
| FEAT-05 | System computes serve and return aggregates from prior matches where Sackmann match stats are available. [CITED: .planning/REQUIREMENTS.md] | Derive MVP rates only from directly supported integer totals and preserve missingness plus sample counts because Sackmann stats are totals with incomplete coverage; do not add hold/break-style derived aggregates in this phase. [CITED: https://github.com/jeffsackmann/tennis_atp][CITED: https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/matches_data_dictionary.txt][CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |
| FEAT-06 | System computes prior-only head-to-head features for two players. [CITED: .planning/REQUIREMENTS.md] | Maintain symmetric pair state and snapshot it before current-match updates; include counts to expose sparsity. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |
| FEAT-07 | System computes match-context features including surface, tournament level, round, best-of, and days rest. [CITED: .planning/REQUIREMENTS.md] | Treat surface/level/round/best-of as static context from canonical matches, compute rest from prior played dates only, and centralize one round-precedence map whose unknown tokens fail loudly in tests. [CITED: src/tennisprediction/domain/models.py][CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |
| FEAT-08 | System creates player A versus player B differential features for ranking, Elo, surface Elo, form, serve, return, H2H, and rest. [CITED: .planning/REQUIREMENTS.md] | Persist player-side snapshots first, then derive differential rows from those persisted contracts instead of recomputing raw state; the Phase 2 contract should explicitly expose ranking, ranking-points, `ranking_change`, Elo, surface Elo, recent-form 5/10/20, rest, serve, return, and H2H deltas. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |
| FEAT-09 | Unit tests prove Elo, ranking, recent form, H2H, and aggregate features exclude the current and future matches. [CITED: .planning/REQUIREMENTS.md] | Add invariant tests that compare a match snapshot before and after deleting future rows; historical features must not move. [CITED: https://scikit-learn.org/stable/common_pitfalls.html][CITED: AGENTS.md] |
</phase_requirements>

## Project Constraints (from AGENTS.md)

- ATP-only scope is locked; Phase 2 must not expand the engine to WTA, doubles, Challenger, ITF, or mixed-tour inputs. [CITED: AGENTS.md]
- Kalshi-only scope remains locked even though this phase is offline; feature schemas should avoid venue-agnostic abstractions that anticipate other markets. [CITED: AGENTS.md]
- Jeff Sackmann `tennis_atp` is the primary historical source, so ordering, ranking, and match-stat assumptions must follow that dataset’s semantics. [CITED: AGENTS.md]
- Chronological feature computation is a hard requirement; rankings, Elo, form, H2H, and aggregates must exclude future matches. [CITED: AGENTS.md]
- Calibrated probabilities and backtesting are later phase gates, so Phase 2 must persist enough provenance for those phases to trust the feature contract. [CITED: AGENTS.md]
- Engineering quality is non-negotiable: code should be modular, typed, logged, configurable, reproducible, and covered by focused unit tests for critical logic. [CITED: AGENTS.md]
- The existing project workflow expects GSD entry points for file-changing work; planners should keep Phase 2 tasks aligned with `gsd` workflow artifacts rather than bypassing them. [CITED: AGENTS.md]
- No project-specific runtime skills are defined in `.codex/skills/` or `.agents/skills/`, so planning should follow repository code patterns and GSD artifacts directly. [CITED: AGENTS.md]

## Summary

Phase 2 should be planned as a hybrid feature system: use Polars for sorted, point-in-time table work such as ranking-as-of joins and grouped lag/cumulative transforms, but keep match-result state transitions in an explicit chronological runner so same-round cohorts can share a pre-round baseline and emit pre-match snapshots before any updates. [CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html][CITED: https://docs.pola.rs/user-guide/expressions/window-functions/][CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]

The most important planning decision is not a library choice; it is the contract boundary. Persist player-side snapshots, persisted audit state, and derived differential rows as separate but linked artifacts so later training, backtesting, and live prediction consume one feature truth instead of silently re-implementing Elo, H2H, ranking lookup, or form windows. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]

The phase is ready to plan on top of the current codebase because Phase 1 already provides canonical matches, rankings, tournaments, match stats, lineage-preserving models, DuckDB persistence patterns, and a passing pytest/mypy/ruff scaffold. [CITED: src/tennisprediction/domain/models.py][CITED: src/tennisprediction/domain/normalization.py][CITED: src/tennisprediction/storage/duckdb.py][CITED: pyproject.toml][CITED: local env probe: ./.venv/bin/python -m pytest -q]

**Primary recommendation:** Plan Phase 2 around a deterministic cohort runner plus persisted player-side state/snapshot tables, with Polars handling ranking-as-of joins and grouped prior-only aggregates, and make leakage invariants the phase gate. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md][CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html][CITED: https://scikit-learn.org/stable/common_pitfalls.html]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Deterministic chronological ordering and cohort emission | API / Backend | Database / Storage | Ordering rules and same-round baseline logic are application behavior, but the emitted order and cohort lineage must be persisted for audit. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |
| Ranking as-of lookup | API / Backend | Database / Storage | The feature engine owns the lookup semantics, while sorted ranking tables are the storage boundary it queries against. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md][CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html] |
| Elo, form, serve/return, H2H, and rest state updates | API / Backend | Database / Storage | These are domain state transitions that must occur after snapshot emission; storage only records the before/after state. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |
| Player-side and differential feature persistence | Database / Storage | API / Backend | Phase 2 explicitly locks persistence of both player-side and differential contracts, with the engine producing and reading them. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |
| Leakage verification | API / Backend | — | Leakage tests validate algorithm behavior and invariants, not storage concerns. [CITED: .planning/REQUIREMENTS.md][CITED: https://scikit-learn.org/stable/common_pitfalls.html] |
| Provenance, lineage, and inspection | Database / Storage | API / Backend | The engine must attach lineage, but storage is the durable audit surface later phases inspect. [CITED: src/tennisprediction/domain/models.py][CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | `3.12.x` target; local venv is `3.12.4` [CITED: pyproject.toml][CITED: local env probe: ./.venv/bin/python --version] | Runtime for the feature runner and tests | The repo already pins `==3.12.*`, and the local `.venv` matches that requirement even though host `python3` is `3.14.0`. [CITED: pyproject.toml][CITED: local env probe: python3 --version][CITED: local env probe: ./.venv/bin/python --version] |
| `polars` [WARNING: flagged as suspicious — verify before using.] | `1.41.2` (published `2026-05-29`) [CITED: https://pypi.org/pypi/polars/json] | Sorted joins, grouped lag/window expressions, and static feature transforms | `join_asof` supports backward point-in-time joins on sorted keys, and window expressions preserve row shape for grouped transforms. [CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html][CITED: https://docs.pola.rs/user-guide/expressions/window-functions/] |
| `duckdb` [WARNING: flagged as suspicious — verify before using.] | `1.5.3` (published `2026-05-20`) [CITED: https://pypi.org/pypi/duckdb/json] | Persisted feature snapshots, audit state, and inspectable tables | Phase 1 already uses DuckDB as the local persistence pattern, so Phase 2 should extend that table-first audit surface rather than invent a second store. [CITED: src/tennisprediction/storage/duckdb.py][CITED: pyproject.toml] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pyarrow` [WARNING: flagged as suspicious — verify before using.] | `24.0.0` (published `2026-04-21`) [CITED: https://pypi.org/pypi/pyarrow/json] | Parquet interchange for feature exports and downstream frozen datasets | Use when Phase 2 needs a file-based snapshot or interchange format in addition to DuckDB tables. [CITED: pyproject.toml][CITED: AGENTS.md] |
| `pytest` [WARNING: flagged as suspicious — verify before using.] | `9.1.0` (published `2026-06-13`) [CITED: https://pypi.org/pypi/pytest/json] | Leakage invariants and targeted unit coverage | Use for deterministic fixture-driven tests around ordering, same-round cohorts, ranking lookups, and future-row deletion invariants. [CITED: pyproject.toml][CITED: AGENTS.md] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `polars` + explicit cohort runner | `pandas`-only dataframe transforms | Simpler to prototype, but weaker at enforcing sorted as-of semantics and easier to accidentally write full-data rolling code that leaks. [CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html][ASSUMED] |
| DuckDB snapshot/audit tables | Raw CSV/Parquet files only | Files are fine for interchange, but they are a weaker inspection surface for per-match provenance and player-state audits. [CITED: src/tennisprediction/storage/duckdb.py][ASSUMED] |
| Persisted player-side plus differential contracts | Differential rows only | Differential-only storage hides missingness, exposure counts, and pre/post state that leakage debugging needs. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |

**Installation:**  
Standard project sync command: `uv sync --group dev` [CITED: AGENTS.md]

```bash
uv sync --group dev
```

**Version verification:** Verified package versions against PyPI JSON and `pip index versions`. [CITED: https://pypi.org/pypi/polars/json][CITED: https://pypi.org/pypi/duckdb/json][CITED: https://pypi.org/pypi/pyarrow/json][CITED: https://pypi.org/pypi/pytest/json][CITED: local env probe: python3 -m pip index versions]

```bash
python3 -m pip index versions polars
python3 -m pip index versions duckdb
python3 -m pip index versions pyarrow
python3 -m pip index versions pytest
```

## Package Legitimacy Audit

> Required only if the environment is rebuilt or dependencies are re-installed during planning or execution; Phase 2 itself does not require adding new third-party packages beyond the current Phase 1 environment. [CITED: pyproject.toml][CITED: local env probe: ./.venv/bin/python imports]

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `polars` | PyPI [CITED: https://pypi.org/pypi/polars/json] | 18 days [CITED: gsd-tools package-legitimacy check] | unknown [CITED: gsd-tools package-legitimacy check] | `https://www.pola.rs/` [CITED: gsd-tools package-legitimacy check] | `SUS` [CITED: gsd-tools package-legitimacy check] | Flagged — planner should add `checkpoint:human-verify` before a fresh install. |
| `duckdb` | PyPI [CITED: https://pypi.org/pypi/duckdb/json] | 27 days [CITED: gsd-tools package-legitimacy check] | unknown [CITED: gsd-tools package-legitimacy check] | `https://github.com/duckdb/duckdb-python` [CITED: gsd-tools package-legitimacy check] | `SUS` [CITED: gsd-tools package-legitimacy check] | Flagged — planner should add `checkpoint:human-verify` before a fresh install. |
| `pyarrow` | PyPI [CITED: https://pypi.org/pypi/pyarrow/json] | 56 days [CITED: gsd-tools package-legitimacy check] | unknown [CITED: gsd-tools package-legitimacy check] | `https://arrow.apache.org/` [CITED: gsd-tools package-legitimacy check] | `SUS` [CITED: gsd-tools package-legitimacy check] | Flagged — planner should add `checkpoint:human-verify` before a fresh install. |
| `pytest` | PyPI [CITED: https://pypi.org/pypi/pytest/json] | 3 days [CITED: gsd-tools package-legitimacy check] | unknown [CITED: gsd-tools package-legitimacy check] | `https://github.com/pytest-dev/pytest` [CITED: gsd-tools package-legitimacy check] | `SUS` [CITED: gsd-tools package-legitimacy check] | Flagged — planner should add `checkpoint:human-verify` before a fresh install. |

**Packages removed due to [SLOP] verdict:** none.  
**Packages flagged as suspicious [SUS]:** `polars`, `duckdb`, `pyarrow`, `pytest`. The automated seam flagged them because registry metadata looked too new and/or download signals were unavailable; all four are already installed in the local `.venv`, so the checkpoint only matters if the environment is rebuilt. [CITED: gsd-tools package-legitimacy check][CITED: local env probe: ./.venv/bin/python imports]

## Architecture Patterns

### System Architecture Diagram

```text
Phase 1 canonical tables
  canonical_matches
  canonical_rankings
  canonical_match_stats
          |
          v
Static preprocess
  - parse/sort matches
  - build deterministic round precedence
  - build player-side match rows
  - backward ranking-as-of join
          |
          v
Chronological cohort runner
  group by (tourney_date, round, tournament)
  emit pre-match player snapshots
  block same-cohort cross-updates
          |
          +--> Player-state snapshots
          |     - Elo / surface Elo
          |     - recent form
          |     - serve/return aggregates
          |     - H2H
          |     - rest
          |
          +--> Differential row builder
          |     - A/B orientation
          |     - feature deltas
          |     - missingness + exposure counts
          |
          v
Persistence layer
  DuckDB audit tables
  optional Parquet export
          |
          v
Verification layer
  - future-row deletion invariants
  - same-round leakage tests
  - ranking cutoff tests
  - persisted provenance inspection
```

### Recommended Project Structure

Proposed module split for planning only [ASSUMED]:

```text
src/tennisprediction/features/
├── __init__.py           # feature package exports
├── schemas.py            # snapshot, state, and differential contracts
├── ordering.py           # round precedence and cohort partitioning
├── rankings.py           # ranking as-of lookup helpers
├── state.py              # Elo/form/H2H/stats/rest state stores
├── runner.py             # chronological cohort runner
├── differential.py       # player-side -> A/B row derivation
└── persistence.py        # DuckDB/Parquet write helpers

tests/unit/
├── test_feature_ordering.py
├── test_feature_rankings.py
├── test_feature_state.py
├── test_feature_differential.py
└── test_feature_leakage.py
```

### Pattern 1: Hybrid Static/Dynamic Builder
**What:** Use Polars for immutable table work such as sorted joins and grouped transforms, then run a Python-side chronological state machine for stateful post-match updates. [CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html][CITED: https://docs.pola.rs/user-guide/expressions/window-functions/][CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**When to use:** Whenever a feature depends on pre-match state and same-round cohorts must not update each other. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**Example:**

```python
# Source: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html
ranked_matches = (
    matches.sort(["canonical_player_id", "tourney_date"])
    .join_asof(
        rankings.sort(["canonical_player_id", "ranking_date"]),
        left_on="tourney_date",
        right_on="ranking_date",
        by="canonical_player_id",
        strategy="backward",
    )
)
```

### Pattern 2: Cohort Baseline Then Batch Update
**What:** Partition matches into deterministic cohorts, emit every cohort member’s snapshot from the same baseline, then apply post-match state updates only after the entire cohort has been emitted. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**When to use:** For same-day or same-round matches where exact intra-round sequencing is not trustworthy. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**Example:**

```python
# Source: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md
for cohort in ordered_match_cohorts:
    baseline = state.clone()
    for match in cohort:
        emit_snapshot(match=match, state=baseline)
    for match in cohort:
        state.apply_result(match)
```

### Pattern 3: Persist Player-Side First, Derive Differential Second
**What:** Write player-side snapshots with provenance and availability metadata, then derive A-vs-B rows from those persisted records. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**When to use:** Always; differential-only storage violates locked auditability requirements. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**Example:**

```python
# Source: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md
player_a = load_player_snapshot(match_id, side="A")
player_b = load_player_snapshot(match_id, side="B")
row = build_differential_row(player_a, player_b)
persist_differential_row(row)
```

### Anti-Patterns to Avoid

- **Forward or nearest ranking joins:** They violate D-02; use backward as-of lookup only. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md][CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html]
- **One giant vectorized full-history transform for everything:** It obscures same-round baseline rules and makes pre/post state auditing brittle. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md][ASSUMED]
- **Filling missing stats with zero:** Sackmann stats are incomplete and integer-total based; zeros silently invent performance data. [CITED: https://github.com/jeffsackmann/tennis_atp][CITED: https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/matches_data_dictionary.txt][CITED: docs/data-contracts.md]
- **Persisting only the final differential row:** It makes leakage debugging, sparse-feature inspection, and downstream provenance checks harder than the phase context allows. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Point-in-time ranking lookup | Custom binary-search join logic per player | `polars.DataFrame.join_asof(..., strategy="backward", by="canonical_player_id")` | Official as-of joins already encode the key semantics Phase 2 needs. [CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html] |
| Grouped lag/cumulative feature windows | Manual Python loops over entire history tables | `Expr.shift`, `Expr.over`, and cumulative/window expressions on sorted partitions | These preserve row shape and behave like lag/window functions when the data is sorted first. [CITED: https://docs.pola.rs/api/python/dev/reference/expressions/api/polars.Expr.shift.html][CITED: https://docs.pola.rs/user-guide/expressions/window-functions/][CITED: https://docs.pola.rs/api/python/stable/reference/expressions/api/polars.Expr.cum_sum.html] |
| Feature audit storage | Ad hoc CSV dumps for each step | Extend the existing DuckDB table-writing pattern | Phase 1 already established DuckDB as the inspectable persistence boundary. [CITED: src/tennisprediction/storage/duckdb.py] |
| Leakage testing harness | One-off notebooks or print-debug checks | `pytest` fixture-driven invariant tests | The repo already has a working pytest scaffold, and leakage is a hard phase gate. [CITED: pyproject.toml][CITED: AGENTS.md] |

**Key insight:** Hand-rolling tennis formulas is acceptable when the domain is specific, but hand-rolling generic as-of joins, grouped lag logic, audit storage, or test infrastructure is wasted complexity that directly increases leakage risk. [CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html][CITED: https://scikit-learn.org/stable/common_pitfalls.html][ASSUMED]

## Common Pitfalls

### Pitfall 1: Ranking Leakage From the Wrong Join Strategy
**What goes wrong:** A forward or nearest ranking lookup leaks later rankings into earlier matches. [CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html]  
**Why it happens:** `join_asof` supports multiple strategies, and only backward semantics match D-02. [CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html][CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**How to avoid:** Sort both frames, join by player, and use `strategy="backward"` with an optional tolerance only if a real business rule exists. [CITED: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html]  
**Warning signs:** Historical ranking features change when future ranking rows are added. [CITED: https://scikit-learn.org/stable/common_pitfalls.html]

### Pitfall 2: Same-Round Cross-Contamination
**What goes wrong:** One match in a same-round cohort updates Elo, H2H, or rest before another same-cohort match emits its pre-match snapshot. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**Why it happens:** A simple row-by-row loop assumes total order where the context explicitly says order may be untrustworthy inside a round/day. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**How to avoid:** Emit all snapshots from a cloned cohort baseline, then apply post-match updates after the cohort completes. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**Warning signs:** Reordering matches within the same cohort changes pre-match features. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]

### Pitfall 3: Treating MatchStats as Percentages or Complete Coverage
**What goes wrong:** Serve/return features are derived as if Sackmann stats were already percentages or universally present. [CITED: https://github.com/jeffsackmann/tennis_atp][CITED: https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/matches_data_dictionary.txt]  
**Why it happens:** The columns look familiar, but Sackmann documents them as integer totals with missing rows in some eras and competitions. [CITED: https://github.com/jeffsackmann/tennis_atp][CITED: https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/matches_data_dictionary.txt]  
**How to avoid:** Derive rates from totals, keep nulls visible, and persist exposure counts and missingness flags. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md][CITED: docs/data-contracts.md]  
**Warning signs:** Feature tables contain zeros where source stats were absent. [CITED: docs/data-contracts.md]

### Pitfall 4: Storing Only Differential Rows
**What goes wrong:** The model row exists, but planners cannot inspect whether a bad feature came from player A state, player B state, or differential math. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**Why it happens:** Differential rows are the downstream training shape, so they are tempting to treat as the only artifact. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**How to avoid:** Persist both player-side snapshots and the derived differential row, linked by `canonical_match_id`, side orientation, and `feature_version`. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**Warning signs:** Leakage debugging requires recomputing player-side state from raw tables. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]

### Pitfall 5: Relying on Implicit Sort Order
**What goes wrong:** Shifted or cumulative window expressions run on an unsorted stream and silently compute the wrong “prior” history. [CITED: https://docs.pola.rs/api/python/dev/reference/expressions/api/polars.Expr.shift.html][ASSUMED]  
**Why it happens:** `shift` is positional and window functions operate over the current row order unless you sort explicitly first. [CITED: https://docs.pola.rs/api/python/dev/reference/expressions/api/polars.Expr.shift.html][CITED: https://docs.pola.rs/user-guide/expressions/window-functions/][ASSUMED]  
**How to avoid:** Sort by deterministic chronological keys before every grouped lag/cumulative transform, and encode round precedence centrally. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]  
**Warning signs:** The same rows produce different recent-form features after a non-semantic reorder. [ASSUMED]

## Code Examples

Verified patterns from official sources:

### Point-in-Time Ranking Lookup

```python
# Source: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html
rank_features = (
    player_matches.sort(["canonical_player_id", "tourney_date"])
    .join_asof(
        rankings.sort(["canonical_player_id", "ranking_date"]),
        left_on="tourney_date",
        right_on="ranking_date",
        by="canonical_player_id",
        strategy="backward",
    )
    .rename(
        {
            "rank": "pre_match_rank",
            "points": "pre_match_rank_points",
            "ranking_date": "rank_source_date",
        }
    )
)
```

### Prior-Only Grouped Lag

```python
# Source: https://docs.pola.rs/api/python/dev/reference/expressions/api/polars.Expr.shift.html
# Source: https://docs.pola.rs/user-guide/expressions/window-functions/
history = history.sort(["canonical_player_id", "match_order"])

history = history.with_columns(
    pl.col("won").shift(1).over("canonical_player_id").alias("prev_won"),
    pl.col("won")
    .shift(1)
    .rolling_sum(window_size=5)
    .over("canonical_player_id")
    .alias("wins_last_5"),
)
```

### Leakage Invariant Test Shape

```python
# Source: https://scikit-learn.org/stable/common_pitfalls.html
def test_future_rows_do_not_change_historical_snapshot(feature_engine, full_history):
    target_match_id = "match:synthetic:example"
    full_snapshot = feature_engine.build(full_history).by_match[target_match_id]
    truncated_history = full_history.filter(pl.col("canonical_match_id") <= target_match_id)
    truncated_snapshot = feature_engine.build(truncated_history).by_match[target_match_id]
    assert full_snapshot == truncated_snapshot
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Recompute stateful features separately in training, backtesting, and live code | Persist one feature-engine contract and make downstream consumers read it [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] | Locked on 2026-06-16 in Phase 2 context [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] | Prevents silent drift between offline and live feature logic. |
| Arbitrary same-day row order | Shared pre-round baseline for effectively concurrent same-round matches [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] | Locked on 2026-06-16 in Phase 2 context [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] | Prevents same-round leakage without pretending the raw files carry trustworthy intra-round sequencing. |
| Match-row ranking columns as the only ranking source | Explicit ranking-table as-of lookup using the latest `ranking_date <= tourney_date` [CITED: https://github.com/jeffsackmann/tennis_atp][CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] | Project choice for Phase 2, aligned with upstream docs [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] | Makes ranking provenance auditable and keeps ranking logic consistent between training and prediction. |

**Deprecated/outdated:**
- Random or shuffled feature evaluation is outdated for this project because it violates the locked chronological leakage constraint. [CITED: AGENTS.md][CITED: .planning/REQUIREMENTS.md][CITED: https://scikit-learn.org/stable/common_pitfalls.html]
- Hiding missing stats behind zeros is outdated for this project because Phase 1 and Phase 2 both require explicit missingness and availability metadata. [CITED: docs/data-contracts.md][CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The proposed `src/tennisprediction/features/` module split is the cleanest Phase 2 layout. [ASSUMED] | Architecture Patterns | Low — planner can rename or regroup modules without changing feature semantics. |
| A2 | A hybrid Polars-plus-runner architecture is preferable to a purely vectorized dataframe pipeline for this phase. [ASSUMED] | Summary / Architecture Patterns | Medium — a different implementation style could still work, but only if it preserves same-round cohort behavior and auditability. |
| A3 | The recommended pytest file map is the right Wave 0 split for Phase 2 tests. [ASSUMED] | Validation Architecture | Low — filenames can move without changing the required verification coverage. |

## Open Questions (RESOLVED)

1. **`ranking_change` MVP semantics**
   - Resolution: Define `ranking_change` as the selected pre-match rank minus the immediately previous available ranking-row rank for the same player. Negative values indicate an improved ranking because lower ATP ranks are better. [CITED: .planning/REQUIREMENTS.md][CITED: https://github.com/jeffsackmann/tennis_atp][CITED: https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/matches_data_dictionary.txt]
   - Required provenance: Persist `previous_ranking_date`, `previous_rank`, and `previous_rank_points` alongside the selected pre-match `rank` and `rank_points` so downstream consumers can audit how the delta was produced. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]
   - Missing-history rule: When no previous ranking row exists, keep `ranking_change` and the previous-row provenance fields as `None` rather than inventing a baseline. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]

2. **Serve/return MVP scope**
   - Resolution: Phase 2 should expose only totals-backed rates whose numerators and denominators already exist in canonical Sackmann match-stat columns. The MVP contract stops at `service_first_won_rate`, `return_first_won_allowed_rate`, and `ace_rate`, plus explicit exposure counts and missingness flags. [CITED: .planning/REQUIREMENTS.md][CITED: https://github.com/jeffsackmann/tennis_atp][CITED: https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/matches_data_dictionary.txt]
   - Out of MVP: Do not add hold/break-style derived aggregates in this phase because their bookkeeping would expand the feature contract beyond the existing canonical totals-backed scope. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]

3. **Round precedence map breadth**
   - Resolution: Centralize one `ROUND_PRECEDENCE` table in the ordering module and make it the only source of deterministic round ordering in Phase 2. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]
   - Guardrail: Unknown round tokens must raise loudly through dedicated ordering tests instead of silently sorting to the end or defaulting to a guessed precedence. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md]
   - Test expectation: Phase 2 Wave 0 should include `tests/unit/test_feature_ordering.py` so FEAT-07 covers both normal precedence ordering and the fail-loud path for unseen round codes. [CITED: .planning/REQUIREMENTS.md]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Project Python runtime | Feature runner, tests, local scripts | ✓ | `.venv/bin/python 3.12.4` [CITED: local env probe: ./.venv/bin/python --version] | — |
| System `python3` | Generic shell commands | ✓, but wrong version for the project [CITED: local env probe: python3 --version] | `3.14.0` [CITED: local env probe: python3 --version] | Use `.venv/bin/python` instead. |
| `uv` | Standard project sync workflow | ✗ [CITED: local env probe: uv --version] | — | Use the existing `.venv` for execution; add a setup task if the planner wants `uv`-based bootstrap. |
| `polars`, `duckdb`, `pyarrow`, `pydantic` in `.venv` | Feature computation and persistence | ✓ [CITED: local env probe: ./.venv/bin/python imports] | `polars 1.41.2`, `duckdb 1.5.3`, `pyarrow 24.0.0`, `pydantic 2.13.4` [CITED: local env probe: ./.venv/bin/python imports] | — |
| `pytest`, `ruff`, `mypy` in `.venv` | Validation and quality gates | ✓ [CITED: local env probe: ./.venv/bin/python -m pytest --version][CITED: local env probe: ./.venv/bin/python -m mypy --version][CITED: local env probe: ./.venv/bin/python -m ruff --version] | `pytest 9.1.0`, `ruff 0.15.17`, `mypy 1.18.2` [CITED: local env probe: ./.venv/bin/python -m pytest --version][CITED: local env probe: ./.venv/bin/python -m mypy --version][CITED: local env probe: ./.venv/bin/python -m ruff --version] | — |

**Missing dependencies with no fallback:** none.  
**Missing dependencies with fallback:** global `uv`; host `python3` version mismatch versus project `==3.12.*`. [CITED: pyproject.toml][CITED: local env probe: python3 --version][CITED: local env probe: uv --version]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.1.0` [CITED: local env probe: ./.venv/bin/python -m pytest --version] |
| Config file | `pyproject.toml` via `[tool.pytest.ini_options]` [CITED: pyproject.toml] |
| Quick run command | `./.venv/bin/python -m pytest -q` |
| Full suite command | `./.venv/bin/python -m pytest -q` |

### Phase Requirements → Test Map

Recommended Phase 2 test map [ASSUMED]:

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FEAT-01 | Pre-match snapshots emit before state updates | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_runner.py -x` | ❌ Wave 0 |
| FEAT-02 | Overall and surface Elo update only after snapshot emission | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_state.py -x` | ❌ Wave 0 |
| FEAT-03 | Ranking/ranking-points lookup uses latest prior ranking only | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_rankings.py -x` | ❌ Wave 0 |
| FEAT-04 | Recent form windows 5/10/20 use only prior matches | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_state.py -x` | ❌ Wave 0 |
| FEAT-05 | Serve/return aggregates use prior stats and preserve missingness | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_state.py -x` | ❌ Wave 0 |
| FEAT-06 | H2H is prior-only and symmetric | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_state.py -x` | ❌ Wave 0 |
| FEAT-07 | Context/rest features derive only from canonical match context and prior played dates | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_ordering.py -x` | ❌ Wave 0 |
| FEAT-08 | Differential rows are reproducible from persisted player-side snapshots | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_differential.py -x` | ❌ Wave 0 |
| FEAT-09 | Future-row deletion and same-round reordering do not change historical snapshots | unit | `./.venv/bin/python -m pytest -q tests/unit/test_feature_leakage.py -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `./.venv/bin/python -m pytest -q tests/unit/test_feature_*.py`
- **Per wave merge:** `./.venv/bin/python -m pytest -q`
- **Phase gate:** Full suite green plus targeted leakage tests green before `$gsd-verify-work`

### Wave 0 Gaps

- [ ] `tests/unit/test_feature_runner.py` — chronological runner, snapshot-before-update, and same-round cohort cases
- [ ] `tests/unit/test_feature_ordering.py` — round precedence, same-day ordering, and unknown-round failure cases
- [ ] `tests/unit/test_feature_rankings.py` — ranking cutoff, previous-ranking provenance, and ranking-change cases
- [ ] `tests/unit/test_feature_state.py` — Elo, form, serve/return, H2H, and rest state transitions
- [ ] `tests/unit/test_feature_differential.py` — A/B orientation and reproducible differential row derivation
- [ ] `tests/unit/test_feature_leakage.py` — future-row deletion invariants and same-cohort reorder invariants
- [ ] Shared synthetic fixture builder for canonical match/ranking/stat histories with controllable edge cases

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No user auth surface in this phase. [CITED: .planning/ROADMAP.md] |
| V3 Session Management | no | No session surface in this phase. [CITED: .planning/ROADMAP.md] |
| V4 Access Control | no | Local batch feature generation has no user-role boundary in Phase 2. [CITED: .planning/ROADMAP.md] |
| V5 Input Validation | yes | Consume only Phase 1 validated canonical tables; reject raw CSV shortcuts and keep typed snapshot contracts. [CITED: docs/data-contracts.md][CITED: src/tennisprediction/domain/models.py] |
| V6 Cryptography | no | No cryptographic requirement in this offline feature phase. [CITED: .planning/ROADMAP.md] |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Future-data leakage through ranking, form, H2H, or stat windows | Information Disclosure / Tampering | Deterministic ordering, backward ranking lookup, pre-match snapshot emission, and invariant tests. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md][CITED: https://scikit-learn.org/stable/common_pitfalls.html] |
| Malformed or out-of-scope source rows contaminating feature state | Tampering | Read only canonical Phase 1 outputs and keep validation/quarantine boundaries intact. [CITED: docs/data-contracts.md][CITED: src/tennisprediction/domain/normalization.py] |
| Missing stat coverage silently becoming zeros | Tampering | Preserve nulls, add missingness flags, and persist exposure counts. [CITED: docs/data-contracts.md][CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |
| Irreproducible audit trail for downstream model/backtest phases | Repudiation | Persist `feature_version`, match IDs, side orientation, as-of context, lineage, and player-side audit state. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md] |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md` — locked Phase 2 ordering, snapshot, missingness, and auditability decisions
- `.planning/REQUIREMENTS.md` and `.planning/ROADMAP.md` — phase requirements, goal, and success criteria
- `src/tennisprediction/domain/models.py`, `src/tennisprediction/domain/normalization.py`, `src/tennisprediction/storage/duckdb.py`, `docs/data-contracts.md`, `pyproject.toml` — existing code and local project conventions
- Jeff Sackmann `tennis_atp` README — ranking coverage, `tourney_date` semantics, and match-stat coverage: https://github.com/jeffsackmann/tennis_atp
- Jeff Sackmann match data dictionary — `tourney_date`, rank, ranking points, and stat-column meanings: https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/matches_data_dictionary.txt

### Secondary (MEDIUM confidence)
- Polars `join_asof` reference — backward as-of join semantics: https://docs.pola.rs/py-polars/html/reference/dataframe/api/polars.DataFrame.join_asof.html
- Polars window functions guide — grouped transforms preserving row shape: https://docs.pola.rs/user-guide/expressions/window-functions/
- Polars `Expr.shift` reference — positional lag semantics: https://docs.pola.rs/api/python/dev/reference/expressions/api/polars.Expr.shift.html
- Polars `Expr.cum_sum` reference — cumulative totals semantics: https://docs.pola.rs/api/python/stable/reference/expressions/api/polars.Expr.cum_sum.html
- scikit-learn common pitfalls — leakage guidance: https://scikit-learn.org/stable/common_pitfalls.html
- scikit-learn pipelines — leakage-safe preprocessing boundary: https://scikit-learn.org/stable/modules/compose.html
- PyPI JSON endpoints for `polars`, `duckdb`, `pyarrow`, and `pytest` — current versions and publish dates

### Tertiary (LOW confidence)
- None — all external claims in this document were verified against official docs, local code, or official registries.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - The recommended runtime and libraries are already encoded in `pyproject.toml`, installed in `.venv`, and supported by official docs. [CITED: pyproject.toml][CITED: local env probe: ./.venv/bin/python imports]
- Architecture: MEDIUM - The contract boundaries are strongly grounded in locked context decisions, but the exact module split and some feature-specific formulas remain planner choices. [CITED: .planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md][ASSUMED]
- Pitfalls: HIGH - The major failure modes are directly supported by locked project constraints, Sackmann data semantics, and official leakage guidance. [CITED: AGENTS.md][CITED: https://github.com/jeffsackmann/tennis_atp][CITED: https://scikit-learn.org/stable/common_pitfalls.html]

**Research date:** 2026-06-16  
**Valid until:** 2026-07-16
