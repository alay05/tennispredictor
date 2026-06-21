from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class PlayerAliasOverrideRecord:
    raw_market_name: str
    normalized_market_name: str
    canonical_player_id: str
    canonical_player_name: str
    source_note: str
    created_at_utc: str
    updated_at_utc: str


@dataclass(frozen=True)
class PlayerNameResolutionResult:
    raw_market_name: str
    normalized_market_name: str
    candidate_canonical_player_ids: tuple[str, ...]
    resolved_canonical_player_id: str | None
    resolved_canonical_player_name: str | None
    resolution_source: Literal["alias_override", "unique_normalized_match", "unresolved"]
