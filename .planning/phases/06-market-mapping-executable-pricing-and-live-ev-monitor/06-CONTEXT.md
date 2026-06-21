# Phase 06: Market Mapping, Executable Pricing, and Live EV Monitor - Context

**Gathered:** 2026-06-20
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase turns the existing read-only Kalshi snapshot surface and the existing ATP/model artifacts into a deterministic scoring layer: resolve Kalshi ATP match-winner markets onto canonical ATP matches, derive executable side-specific pricing and liquidity inputs from fresh orderbook data, reject ambiguous/unscorable markets explicitly, and expose a ranked read-only monitor for shadow-mode or live-readonly scans. It does not add trade execution, non-Kalshi venues, non-ATP tours, or alert-channel hardening.

</domain>

<decisions>
## Implementation Decisions

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
- **D-17:** Ranked opportunities must sort by expected value first, then edge, executable liquidity, confidence, and freshness. Operator-facing output must include ticker, canonical match ID, player pairing, selected side, model probability, executable entry price, price source, expected value, edge, executable liquidity, freshness age, mapping state, mapping confidence tier, and any rejection reason summary.
- **D-18:** `mapping_confidence` must be an explicit deterministic evidence tier, not a hidden heuristic score. MVP tiers should distinguish at least `exact_names`, `alias_override`, and `manual_review_required`, with only non-review-required tiers eligible for accepted ranked output.
- **D-19:** Phase 06 should persist both accepted and rejected scan outputs for auditability. Human-readable CLI output can default to the ranked accepted table plus summary counts for rejected or excluded records, while the full machine-readable record set remains available for later reporting and alerts.

### the agent's Discretion
- Choose the exact storage format and module split for alias overrides, mapping evidence tables, and executable-pricing adapters as long as the audit fields above remain explicit and version-controlled.
- Choose the exact candidate-ranking heuristic used to propose ambiguous-name review candidates, provided the heuristic never auto-accepts a non-unique match.
- Choose whether executable liquidity should use only the top ask level or a clearly labeled sum across immediately executable levels, provided the source label and evidence payload make the choice inspectable.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and phase contract
- `project-outline.yaml` — source project spec and the ATP-only / Kalshi-only hard constraints
- `.planning/PROJECT.md` — durable project context and v1 scope fences
- `.planning/REQUIREMENTS.md` — Phase 06 requirement IDs `MKT-01` through `MKT-08`
- `.planning/ROADMAP.md` — Phase 06 goal, dependency on Phase 05, and success criteria
- `.planning/STATE.md` — current project state plus the open Phase 06 concern about naming, side orientation, and executable pricing assumptions
- `AGENTS.md` — local workflow rules and repository-specific constraints

### Prior phase decisions that Phase 06 inherits
- `.planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md` — canonical player-ID boundaries and the Phase 01 decision not to merge player identities manually
- `.planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md` — canonical match, feature-version, and persisted snapshot contracts used by later prediction/scoring stages
- `.planning/phases/04-backtesting-and-ev-decision-core/04-RESEARCH.md` — the explicit Phase 04 deferral of real Kalshi price-source and liquidity semantics into Phase 06
- `.planning/phases/05-kalshi-read-only-market-integration/05-03-SUMMARY.md` — the current read-only collection flow, retry behavior, and open-market orderbook snapshot surface

### Existing implementation files and contracts
- `src/tennisprediction/kalshi/schemas.py` — normalized Kalshi market, market-detail, and orderbook DTO contracts
- `src/tennisprediction/kalshi/client.py` — authenticated read client and the transport-to-DTO normalization boundary
- `src/tennisprediction/kalshi/jobs.py` — read-only snapshot collection workflow and current market-state handling
- `src/tennisprediction/kalshi/snapshots.py` — persisted market/detail/orderbook snapshot rows, including best bid/ask and collected timestamps
- `src/tennisprediction/backtesting/schemas.py` — current normalized market-input, threshold, and opportunity-record contracts that Phase 06 must evolve carefully
- `src/tennisprediction/ev/opportunity.py` — accepted/rejected opportunity batch logic and threshold snapshot pattern to preserve
- `src/tennisprediction/modeling/registry.py` — trusted artifact bundle loading and manifest validation for model selection
- `src/tennisprediction/modeling/datasets.py` — canonical match ID and feature-column conventions used by modeling rows
- `src/tennisprediction/features/persistence.py` — persisted feature snapshot and differential-row conventions that later scoring paths should reuse
- `src/tennisprediction/domain/normalization.py` — existing deterministic normalization style for upstream tennis data
- `src/tennisprediction/cli.py` — current CLI shape and command-registration pattern that the Phase 06 monitor should extend

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/tennisprediction/kalshi/schemas.py`: already gives frozen DTOs for market titles, subtitles, status, best quotes, and orderbook levels.
- `src/tennisprediction/kalshi/snapshots.py`: already persists best bid/ask summaries plus full yes/no level JSON and collection timestamps, which Phase 06 can promote into executable-pricing evidence.
- `src/tennisprediction/kalshi/jobs.py`: already separates listing, market-detail, and orderbook collection behind read-only jobs and explicit market-state handling.
- `src/tennisprediction/backtesting/schemas.py` and `src/tennisprediction/ev/opportunity.py`: already define the accepted/rejected opportunity audit surface, threshold snapshots, and reason-code flow that live scanning should preserve.
- `src/tennisprediction/modeling/registry.py`: already provides trusted manifest-first model loading, which Phase 06 can reuse when choosing artifacts for scoring.

### Established Patterns
- Kalshi transport details are normalized immediately into project-owned DTOs and snapshot rows; business logic should keep consuming project-owned contracts rather than raw API payloads.
- `canonical_match_id` is the cross-phase join key between feature snapshots, modeling rows, replay outputs, and future market-mapping/scoring records.
- Auditability is explicit throughout the repo: request metadata, lineage metadata, threshold snapshots, and accepted/rejected records are preserved instead of inferred later.

### Integration Points
- Phase 06 should sit between persisted Kalshi snapshots and the EV decision engine: mapping produces canonical match alignment, executable-pricing adapts orderbooks into scoring inputs, and the scorer emits ranked accepted/rejected batches.
- The scan surface should reuse trusted artifact loading plus the existing CLI registration style, not create a separate execution path outside the project CLI.
- Alias overrides and mapping evidence should remain project-owned artifacts so later alerting/reporting phases can explain why a market was matched, rejected, or excluded.

</code_context>

<specifics>
## Specific Ideas

- Treat executable pricing as an adapter layer in front of the existing EV evaluator rather than embedding Kalshi orderbook parsing inside the opportunity-record builder.
- Keep alias overrides as a small versioned project artifact with explicit audit metadata so manual decisions survive re-runs and remain reviewable.
- Require player-pair evidence plus time-window alignment for matching; title-only matching is too brittle for ATP rematches, duplicate surnames, and noisy Kalshi wording.
- Shadow-mode output should make rejected and excluded counts visible, because the main operator value in Phase 06 is often understanding why a market was not scorable yet.

</specifics>

<deferred>
## Deferred Ideas

- UI-driven alias review and manual match-resolution tooling remain future work; this phase should stay CLI/file-based and auditable.
- Alert-channel delivery, polling hardening, and operator configuration depth belong to Phase 07.

</deferred>

---

*Phase: 06-Market Mapping, Executable Pricing, and Live EV Monitor*
*Context gathered: 2026-06-20*
