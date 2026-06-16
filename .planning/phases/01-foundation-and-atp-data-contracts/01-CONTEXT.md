# Phase 1: Foundation and ATP Data Contracts - Context

**Gathered:** 2026-06-16
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase establishes the reproducible ATP-only data foundation: pinned Sackmann source acquisition, dataset validation, canonical ATP-only tables, stable IDs, and documented rules for what is excluded from the canonical dataset. It does not extend into feature engineering, modeling, backtesting, Kalshi integration, or any later workflow stages.

</domain>

<decisions>
## Implementation Decisions

### Source handling
- **D-01:** Pin the Jeff Sackmann `tennis_atp` source by commit SHA, not by branch.
- **D-02:** Keep raw source snapshots immutable and record checksums plus attribution/license metadata alongside them.
- **D-03:** Normalize into derived canonical tables only after source validation passes.

### ATP edge cases
- **D-04:** Exclude qualifiers, retirements, walkovers, and incomplete matches from the canonical Phase 1 dataset.
- **D-05:** Preserve those rows only as raw source material or quarantine data if needed for audit, but do not include them in the Phase 1 canonical store.

### Canonical identity model
- **D-06:** Use stable source-derived IDs where Sackmann provides them.
- **D-07:** Introduce synthetic canonical IDs only where needed for matches, tournaments, or derived records.
- **D-08:** Preserve source-lineage fields on canonical tables.
- **D-09:** Do not introduce manual player-merge logic in Phase 1.

### Phase 1 scope
- **D-10:** Phase 1 stops at the data foundation: ingestion, validation, normalization, and data-rule documentation.
- **D-11:** Do not add a walking skeleton or end-to-end feature slice in Phase 1.

### the agent's Discretion
- Use the standard project stack from the research summary for the phase 1 implementation plan.
- Choose the exact packaging, validation, and storage layout details during planning as long as they preserve the locked data rules above.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project context and scope
- `project-outline.yaml` — source project spec and hard constraints
- `.planning/PROJECT.md` — durable project context and scope boundaries
- `.planning/REQUIREMENTS.md` — v1/v2 requirements and traceability
- `.planning/ROADMAP.md` — phase structure and Phase 1 goals
- `.planning/STATE.md` — current project state and blockers

### Research outputs
- `.planning/research/SUMMARY.md` — synthesis of stack, features, architecture, pitfalls, and roadmap implications
- `.planning/research/STACK.md` — Python/data/ML stack recommendations
- `.planning/research/FEATURES.md` — feature landscape, anti-features, and phase signals
- `.planning/research/ARCHITECTURE.md` — append-oriented architecture and build order
- `.planning/research/PITFALLS.md` — failure modes and prevention gates

### Project instructions
- `AGENTS.md` — local workflow instructions for this repository

### External references
- No external docs beyond the local project spec and research artifacts

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- No application codebase exists yet for Phase 1; there are no reusable runtime components to map forward.

### Established Patterns
- The repository is a greenfield planning scaffold with durable `.planning/` artifacts and no product source tree yet.

### Integration Points
- Phase 1 will create the first source-to-canonical data path that later phases consume for features, modeling, backtesting, and Kalshi mapping.

</code_context>

<specifics>
## Specific Ideas

- Raw data should be preserved separately from canonical tables so auditability is retained even when the canonical dataset excludes edge-case match types.
- The phase should treat the Sackmann repository as a versioned upstream dependency and keep lineage explicit in the derived tables.

</specifics>

<deferred>
## Deferred Ideas

None - discussion stayed within Phase 1 scope.

</deferred>

---

*Phase: 1-Foundation and ATP Data Contracts*
*Context gathered: 2026-06-16*
