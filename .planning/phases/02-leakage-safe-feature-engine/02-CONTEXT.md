# Phase 2: Leakage-Safe Feature Engine - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase builds the chronological pre-match feature pipeline on top of the Phase 1 canonical ATP domain tables. It defines how feature state is computed, ordered, persisted, and audited so later model training and live prediction can consume one leakage-safe feature contract. It does not include model training, calibration, Kalshi integration, backtesting, or alerting.

</domain>

<decisions>
## Implementation Decisions

### Chronological cutoff and ordering
- **D-01:** Feature generation must emit each match's pre-match snapshot before any state update from that match is applied.
- **D-02:** Ranking features must use the latest ranking row with `ranking_date <= tourney_date`; never look ahead beyond the match's tournament date boundary.
- **D-03:** Chronological processing order must be deterministic: `tourney_date`, then round precedence, then stable source tie-breakers (`source_file_path`, `source_row_number`).
- **D-04:** Matches that are effectively concurrent within the same round/day must not update each other's pre-match state; same-round cohorts should use a shared pre-round baseline when exact intra-round order is not trustworthy.

### Feature snapshot contract
- **D-05:** Every persisted feature snapshot must carry `feature_version`, `canonical_match_id`, `player_a_id`, `player_b_id`, `as_of_date`, source snapshot lineage, and side orientation so downstream training/prediction code never reconstructs provenance ad hoc.
- **D-06:** Persist both player-level pre-match state and the final differential feature row shape; later phases should consume stored contracts rather than recomputing differentials independently.
- **D-07:** Feature snapshots must include availability metadata and sample/exposure counts for sparse features, not just the final numeric rates.

### Missing and sparse data handling
- **D-08:** Missing rankings, missing match stats, and sparse H2H/form windows stay in-scope; they should produce null-or-empty feature values plus explicit missingness indicators rather than excluding the match.
- **D-09:** Rate features derived from sparse history should ship with exposure counts and use shrinkage/minimum-sample safeguards in implementation; never treat one-match rates as equally trustworthy to deep histories.
- **D-10:** Match-stat missingness from older eras or incomplete coverage must remain visible in the feature contract so later models can learn or filter on availability instead of silently receiving zeros.

### State persistence and auditability
- **D-11:** Phase 2 should persist audit state history, not only final feature snapshots. At minimum, keep pre-match state records that allow Elo, surface Elo, form, H2H, and aggregate calculations to be inspected after the fact.
- **D-12:** The feature engine is the single source of truth for stateful tennis features. Training, backtests, and live prediction must consume persisted snapshots/state instead of recomputing Elo, rankings, H2H, or rolling stats elsewhere.

### the agent's Discretion
- Choose the exact file/module split for the chronological runner, state stores, and feature schemas as long as the single-source-of-truth and auditability rules above are preserved.
- Choose the exact representation of round precedence and shrinkage formulas during planning/research as long as same-round leakage is prevented and sparse-feature confidence remains explicit.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context and scope
- `project-outline.yaml` — source project spec and hard constraints
- `.planning/PROJECT.md` — durable project context and ATP-only / Kalshi-only scope boundaries
- `.planning/REQUIREMENTS.md` — Phase 2 requirement IDs `FEAT-01` through `FEAT-09`
- `.planning/ROADMAP.md` — Phase 2 goal, dependency on Phase 1, and success criteria
- `.planning/STATE.md` — current project position and next-phase readiness

### Prior phase decisions
- `.planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md` — locked Phase 1 data-contract, quarantine, and lineage decisions
- `.planning/phases/01-foundation-and-atp-data-contracts/01-03-SUMMARY.md` — schema validation and quarantine behavior that feature inputs inherit
- `.planning/phases/01-foundation-and-atp-data-contracts/01-04-SUMMARY.md` — canonical table, ID, and persistence contracts that feature code must consume

### Research outputs
- `.planning/research/SUMMARY.md` — project-wide pipeline ordering and phase rationale
- `.planning/research/FEATURES.md` — required Phase 2 feature families, leakage expectations, and acceptance signals
- `.planning/research/ARCHITECTURE.md` — chronological state builder, feature snapshot layer, and single-source-of-truth architecture
- `.planning/research/PITFALLS.md` — leakage, sparse-feature, and ranking-as-of failure modes to encode as gates
- `.planning/research/STACK.md` — storage and testing recommendations for Parquet, DuckDB, and pytest leakage checks

### Existing implementation files
- `src/tennisprediction/domain/models.py` — canonical match, ranking, player, and match-stat contracts
- `src/tennisprediction/domain/normalization.py` — current validated-to-canonical pipeline and lineage model
- `src/tennisprediction/storage/duckdb.py` — existing DuckDB persistence pattern for canonical tables

### Project instructions
- `AGENTS.md` — local workflow rules, especially GSD workflow usage and project constraints

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/tennisprediction/domain/models.py`: canonical match, ranking, player, and match-stat dataclasses already define the upstream contracts the feature engine should consume.
- `src/tennisprediction/domain/normalization.py`: established pattern for lineage-aware transformation from validated rows into canonical entities.
- `src/tennisprediction/storage/duckdb.py`: existing DuckDB table-writing helper pattern can be extended for feature snapshots and audit state tables.
- `src/tennisprediction/ingestion/validation.py` and `src/tennisprediction/ingestion/quarantine.py`: validated snapshot boundary and quarantine outputs are already explicit, so Phase 2 does not need to revisit raw-source filtering.

### Established Patterns
- Data contracts are typed and lineage-preserving.
- Derived artifacts are expected to be reproducible from immutable upstream snapshots.
- Missing or excluded upstream data is represented explicitly, not silently coerced away.

### Integration Points
- Phase 2 should read from canonical matches, rankings, players, and match stats produced in Phase 1.
- New feature/state persistence should follow the DuckDB-centered storage pattern while keeping feature snapshots distinct from canonical source tables.
- Leakage tests should live close to the chronological runner and snapshot contract rather than inside later model code.

</code_context>

<specifics>
## Specific Ideas

- Same-round matches are the hardest leakage edge in this phase; planning should treat them as a first-class gate, not an implementation detail.
- Persist enough pre-match state that a failed leakage test can point to the exact pre/post transition for a specific match and player.
- Differential rows should remain reproducible from persisted player-side snapshots rather than being the only stored representation.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 2-Leakage-Safe Feature Engine*
*Context gathered: 2026-06-16*
