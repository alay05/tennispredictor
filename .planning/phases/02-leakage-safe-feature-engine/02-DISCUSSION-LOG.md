# Phase 2: Leakage-Safe Feature Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-16
**Phase:** 2-Leakage-Safe Feature Engine
**Areas discussed:** Match ordering and as-of cutoff, Feature snapshot contract, Missing-data policy, State/history persistence

---

## Match ordering and as-of cutoff

| Option | Description | Selected |
|--------|-------------|----------|
| Strict source row order | Treat raw file order as fully chronological inside a tournament date. | |
| Deterministic round-aware order | Use `tourney_date`, round precedence, and stable source tie-breakers, with cohort protection for same-round ambiguity. | ✓ |
| Ignore same-day ambiguity | Accept possible same-day leakage and rely on tests only. | |

**User's choice:** Agent discretion delegated by user.
**Notes:** Locked the safer round-aware ordering model and explicitly prevented same-round matches from updating each other's pre-match state when exact order is unknowable.

---

## Feature snapshot contract

| Option | Description | Selected |
|--------|-------------|----------|
| Differential rows only | Persist only player A vs player B feature rows. | |
| Rich snapshot contract | Persist player-side pre-match state plus differential rows, versioning, lineage, orientation, and availability metadata. | ✓ |
| Minimal lineage | Keep only match id and feature values. | |

**User's choice:** Agent discretion delegated by user.
**Notes:** Chose the richer contract so later training, backtesting, and live prediction can share one persisted source of truth and debug leakage issues.

---

## Missing-data policy

| Option | Description | Selected |
|--------|-------------|----------|
| Drop incomplete rows | Exclude matches whenever rankings or stats are missing. | |
| Explicit missingness | Keep matches, emit null-or-empty values with flags and exposure counts, and guard sparse rates. | ✓ |
| Fill zeros | Coerce missing ranking/stat features to zero-like defaults. | |

**User's choice:** Agent discretion delegated by user.
**Notes:** Preserved missingness explicitly to avoid biasing older or stat-sparse eras and to keep data availability visible to later model selection.

---

## State/history persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Final snapshots only | Store only the final feature rows used by modeling. | |
| Audit state + snapshots | Store pre-match state history alongside feature snapshots for Elo, form, H2H, and aggregate inspection. | ✓ |
| Recompute on demand | Keep no state history and reconstruct during tests/debugging. | |

**User's choice:** Agent discretion delegated by user.
**Notes:** Chose explicit audit persistence because Phase 2 is the leakage gate for the whole project and later debugging should not depend on ad hoc recomputation.

---

## the agent's Discretion

- User explicitly delegated all Phase 2 gray-area choices to the agent.
- Exact module boundaries, storage table names, and shrinkage formulas remain planner/research discretion within the locked context decisions.

## Deferred Ideas

None.
