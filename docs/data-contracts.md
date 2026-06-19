# Phase 1 Data Contracts

Phase 1 defines the ATP-only canonical data boundary for the project. It covers raw Jeff Sackmann snapshot validation, quarantine rules, canonical IDs, and lineage. It does not include a walking skeleton, feature generation, model training, backtesting, Kalshi integration, or any end-to-end slice beyond data foundation work.

## Scope Boundary

- Accepted raw source families are `atp_players.csv`, `atp_rankings*.csv`, `atp_matches_YYYY.csv`, and `atp_matchstats_YYYY.csv`.
- Non-ATP, doubles, Challenger, Futures, ITF, WTA, and other out-of-scope file families are not normalized into canonical tables.
- Out-of-scope files remain auditable through file-level quarantine metadata rather than disappearing silently.

## Validation Rules

- Snapshot checksum verification must pass before any canonical normalization begins.
- Raw players, rankings, matches, tournaments, and match stats must satisfy the expected Phase 1 column contract.
- Integer columns must parse as integers.
- Chronological raw date columns such as `ranking_date` and `tourney_date` must parse as `YYYYMMDD`.
- Normalization consumes only the validated snapshot contract from Phase 1. It must not read raw CSVs directly.

## Exclusion and Quarantine Rules

- Qualifiers are excluded from the canonical Phase 1 dataset when the match round is `Q1`, `Q2`, `Q3`, or `QR`.
- Retirements are excluded when the match comment indicates `retired`.
- Walkovers are excluded when the match comment indicates `walkover` or the score text includes walkover notation.
- Incomplete matches are excluded when the match comment indicates `incomplete`.
- Excluded match rows remain available through row-level quarantine output with deterministic reason codes.
- Out-of-scope file families remain available through file-level quarantine output with deterministic reason codes.

## Missing Stats Policy

- Match-stat nullable columns such as aces and serve points remain nullable in Phase 1.
- Missing stat values are not coerced to zero during validation or canonical normalization.
- Canonical match-stat records preserve missing values as missing so later feature work can make explicit, leakage-safe decisions about availability and imputation.

## Canonical ID Policy

- Sackmann player IDs are reused as the stable player identity boundary.
- Canonical player IDs are deterministic wrappers around the source player ID.
- Tournaments receive deterministic synthetic IDs because Phase 1 treats tournament identity as a normalized derived contract.
- Matches receive deterministic synthetic IDs because the raw match rows do not expose a stable canonical match ID for Phase 1.
- Rankings receive deterministic synthetic IDs keyed by source player ID and ranking date.
- Match stats reuse the source `match_id` as the stable upstream identity when present.
- Phase 1 does not introduce manual player-merge logic.

## Lineage Policy

- Every canonical player, tournament, match, ranking, and match-stat record preserves source lineage.
- Lineage includes the source repository, pinned commit SHA, raw file path, raw row number, and snapshot root.
- Canonical tables are therefore rebuildable from raw snapshots while preserving auditability.

## Canonical Table Boundary

Phase 1 canonical tables are:

- `canonical_players`
- `canonical_tournaments`
- `canonical_matches`
- `canonical_rankings`
- `canonical_match_stats`

These tables contain ATP-only, validated, non-quarantined records. Quarantined rows and files are not written into those canonical tables.
