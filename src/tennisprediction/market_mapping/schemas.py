from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal


class MarketMappingState(StrEnum):
    matched = "matched"
    ambiguous = "ambiguous"
    unmatched = "unmatched"
    excluded = "excluded"


class MappingConfidenceTier(StrEnum):
    exact_names = "exact_names"
    alias_override = "alias_override"
    manual_review_required = "manual_review_required"


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


@dataclass(frozen=True)
class MarketMappingEvidenceRow:
    market_ticker: str
    event_ticker: str
    collected_at_utc: datetime
    raw_title: str
    raw_yes_sub_title: str
    raw_no_sub_title: str
    normalized_yes_player_name: str
    normalized_no_player_name: str
    alias_hit_player_ids: tuple[str, ...]
    candidate_canonical_match_ids: tuple[str, ...]
    mapping_state: MarketMappingState
    mapping_confidence: MappingConfidenceTier
    canonical_match_id: str | None
    yes_canonical_player_id: str | None
    no_canonical_player_id: str | None
    yes_maps_to_player_a: bool | None
    no_maps_to_player_b: bool | None
    rejection_reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class UnscorableMappingRecord:
    market_ticker: str
    event_ticker: str
    mapping_state: MarketMappingState
    mapping_confidence: MappingConfidenceTier
    canonical_match_id: str | None
    rejection_reason_codes: tuple[str, ...]
