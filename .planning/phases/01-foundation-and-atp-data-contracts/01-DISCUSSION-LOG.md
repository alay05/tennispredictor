# Phase 1: Foundation and ATP Data Contracts - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md - this log preserves the alternatives considered.

**Date:** 2026-06-16
**Phase:** 1-Foundation and ATP Data Contracts
**Areas discussed:** Source handling, ATP edge cases, Canonical identity model, Phase 1 scope

---

## Source handling

| Option | Description | Selected |
|--------|-------------|----------|
| Pin source + checksums + attribution | Pin Sackmann by commit SHA, retain raw immutable snapshots, and record checksums plus license/attribution metadata | ✓ |
| Branch-based source tracking | Track the upstream branch and derive data dynamically | |
| Minimal source metadata | Keep only source commit without file-level integrity metadata | |

**User's choice:** You asked me to figure this out.
**Notes:** Use commit SHA pinning, immutable raw snapshots, and explicit provenance metadata to keep the dataset reproducible.

---

## ATP edge cases

| Option | Description | Selected |
|--------|-------------|----------|
| Exclude from canonical dataset | Leave qualifiers, retirements, walkovers, and incomplete matches out of the canonical Phase 1 store | ✓ |
| Include with flags | Keep them in the canonical store with special-case flags | |
| Keep everything | Normalize all rows now and sort the rules out later | |

**User's choice:** Exclude from the canonical dataset.
**Notes:** Preserve auditability in raw/quarantine data if needed, but Phase 1 canonical tables should not include those match types.

---

## Canonical identity model

| Option | Description | Selected |
|--------|-------------|----------|
| Stable source IDs + synthetic canonical IDs | Use source IDs where available and synthesize canonical IDs where needed, while preserving lineage fields | ✓ |
| Manual player merge now | Add player alias merge logic in Phase 1 | |
| Rebuild identities later | Skip stable IDs until downstream phases | |

**User's choice:** You asked me to figure this out.
**Notes:** Preserve source lineage and keep Phase 1 identity handling deterministic; no manual merge logic in this phase.

---

## Phase 1 scope

| Option | Description | Selected |
|--------|-------------|----------|
| Data foundation only | Stop at ingestion, validation, normalization, and data-rule documentation | ✓ |
| Add walking skeleton | Include a thin end-to-end pipeline slice in Phase 1 | |
| Expand into features | Start feature engineering in Phase 1 | |

**User's choice:** Stop at Phase 1.
**Notes:** Keep Phase 1 tightly scoped to the data contract and leave executable vertical slices to later phases.

## the agent's Discretion

- Packaging, validation, and storage layout details were left to the agent.

## Deferred Ideas

- Walking skeleton for Phase 1 - deferred because the user explicitly scoped Phase 1 to the data foundation only.
