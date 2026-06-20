# Phase 06: Market Mapping, Executable Pricing, and Live EV Monitor - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-20
**Phase:** 06-market-mapping-executable-pricing-and-live-ev-monitor
**Areas discussed:** Player identity normalization and alias overrides, Market-to-match mapping evidence and rejection policy, Executable price and liquidity source rules, Live/shadow scan behavior and ranking output

---

## Player identity normalization and alias overrides

| Option | Description | Selected |
|--------|-------------|----------|
| Exact normalized-name only | Match only on one deterministic normalized name form and reject everything else. | |
| Deterministic normalization + auditable manual alias overrides + non-binding fuzzy suggestions | Keep matching deterministic, allow manual rescue for naming drift, and preserve reviewability. | ✓ |
| Aggressive fuzzy auto-match | Let fuzzy/token heuristics auto-accept near matches to maximize coverage. | |

**User's choice:** Agent discretion — choose the strongest deterministic/auditable option.
**Notes:** Selected the middle path because the project explicitly rejects LLM-first or ambiguity-tolerant player matching. Manual aliases are necessary for Kalshi naming variation, but fuzzy scoring should only assist review, never auto-resolve.

---

## Market-to-match mapping evidence and rejection policy

| Option | Description | Selected |
|--------|-------------|----------|
| Strict pair + time window + contract semantics, fail closed | Require unique player resolution, one canonical match candidate, and consistent winner semantics before scoring. | ✓ |
| Title-first heuristic with manual rescue | Prefer lightweight title matching, then patch mistakes later. | |
| Best-effort broad mapping | Score the most likely match even if multiple candidates remain. | |

**User's choice:** Agent discretion — choose the strongest deterministic/auditable option.
**Notes:** Selected strict evidence with explicit `matched` / `ambiguous` / `unmatched` / `excluded` states. This best fits the repo’s existing “trustworthy probabilities and auditable EV” posture.

---

## Executable price and liquidity source rules

| Option | Description | Selected |
|--------|-------------|----------|
| Side-specific executable ask pricing from orderbooks | Score YES and NO from their own executable asks and explicit executable liquidity. | ✓ |
| Single normalized scalar from midpoint/last trade | Keep the Phase 04 scalar contract unchanged even though executable sides may diverge. | |
| Hybrid fallback to stale quotes and diagnostics | Use orderbook when present, but silently fall back to midpoint/last/bid for scoring continuity. | |

**User's choice:** Agent discretion — choose the strongest deterministic/auditable option.
**Notes:** Selected side-specific executable asks because real Kalshi fills are not complement-symmetric once spreads exist. Diagnostics can still retain midpoint/last/bid, but not as silent scoring fallbacks.

---

## Live/shadow scan behavior and ranking output

| Option | Description | Selected |
|--------|-------------|----------|
| Shadow-first read-only ranked monitor with accepted/rejected audit batches | Score persisted or fresh read-only snapshots, stay non-executing, and expose ranked accepted plus rejected summaries. | ✓ |
| Continuous live polling surface now | Build the more operationally hardened always-on scanner immediately in Phase 06. | |
| Minimal one-off scoring only | Avoid a monitor abstraction and only provide isolated scoring commands. | |

**User's choice:** Agent discretion — choose the strongest deterministic/auditable option.
**Notes:** Selected a shadow-first read-only monitor because it satisfies the roadmap goal without prematurely dragging Phase 07 operational hardening into Phase 06. A live-readonly one-shot path can still exist as a read-only extension.

---

## the agent's Discretion

- The user explicitly delegated all four gray areas with: “for all 4, do what you think is best. make informed decisions by considering all options.”
- The implementation still has discretion over exact storage layout, alias file format, candidate-ranking heuristics, and whether executable liquidity uses one ask level or a clearly labeled aggregate across immediately executable levels.

## Deferred Ideas

- UI-driven alias review and manual market-resolution tooling
- Alert-channel delivery and operational hardening beyond the Phase 06 read-only monitor
