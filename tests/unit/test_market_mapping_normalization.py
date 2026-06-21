from __future__ import annotations

from dataclasses import dataclass

from tennisprediction.market_mapping.aliases import lookup_player_alias_override
from tennisprediction.market_mapping.normalization import normalize_market_player_name
from tennisprediction.market_mapping.schemas import (
    PlayerAliasOverrideRecord,
    PlayerNameResolutionResult,
)


@dataclass(frozen=True)
class _CanonicalPlayerFixture:
    canonical_player_id: str
    full_name: str


def _resolve_player_name(
    raw_market_name: str,
    canonical_players: list[_CanonicalPlayerFixture],
    overrides: dict[str, PlayerAliasOverrideRecord],
) -> PlayerNameResolutionResult:
    normalized_market_name = normalize_market_player_name(raw_market_name)
    alias_override = lookup_player_alias_override(raw_market_name, overrides)

    if alias_override is not None:
        return PlayerNameResolutionResult(
            raw_market_name=raw_market_name,
            normalized_market_name=normalized_market_name,
            candidate_canonical_player_ids=(),
            resolved_canonical_player_id=alias_override.canonical_player_id,
            resolved_canonical_player_name=alias_override.canonical_player_name,
            resolution_source="alias_override",
        )

    candidate_players = [
        player
        for player in canonical_players
        if normalize_market_player_name(player.full_name) == normalized_market_name
    ]

    if len(candidate_players) == 1:
        candidate_player = candidate_players[0]
        return PlayerNameResolutionResult(
            raw_market_name=raw_market_name,
            normalized_market_name=normalized_market_name,
            candidate_canonical_player_ids=(candidate_player.canonical_player_id,),
            resolved_canonical_player_id=candidate_player.canonical_player_id,
            resolved_canonical_player_name=candidate_player.full_name,
            resolution_source="unique_normalized_match",
        )

    return PlayerNameResolutionResult(
        raw_market_name=raw_market_name,
        normalized_market_name=normalized_market_name,
        candidate_canonical_player_ids=tuple(
            player.canonical_player_id for player in candidate_players
        ),
        resolved_canonical_player_id=None,
        resolved_canonical_player_name=None,
        resolution_source="unresolved",
    )


def test_normalize_market_player_name_ascii_folds_and_preserves_token_order() -> None:
    assert normalize_market_player_name("João   Fonseca!") == "joao fonseca"


def test_ambiguous_normalized_names_stay_unresolved_without_alias_override() -> None:
    canonical_players = [
        _CanonicalPlayerFixture("player:sackmann:1", "Joao Fonseca"),
        _CanonicalPlayerFixture("player:sackmann:2", "João Fonseca"),
    ]

    result = _resolve_player_name(
        "JOAO FONSECA!!!",
        canonical_players,
        overrides={},
    )

    assert result.normalized_market_name == "joao fonseca"
    assert result.candidate_canonical_player_ids == (
        "player:sackmann:1",
        "player:sackmann:2",
    )
    assert result.resolved_canonical_player_id is None
    assert result.resolved_canonical_player_name is None
    assert result.resolution_source == "unresolved"


def test_alias_override_can_resolve_otherwise_ambiguous_name_without_rewriting_identities() -> None:
    canonical_players = [
        _CanonicalPlayerFixture("player:sackmann:1", "Joao Fonseca"),
        _CanonicalPlayerFixture("player:sackmann:2", "João Fonseca"),
    ]
    overrides = {
        "joao fonseca": PlayerAliasOverrideRecord(
            raw_market_name="JOAO FONSECA!!!",
            normalized_market_name="joao fonseca",
            canonical_player_id="player:sackmann:2",
            canonical_player_name="João Fonseca",
            source_note="kalshi title confirmed against ATP player id",
            created_at_utc="2026-06-20T12:00:00Z",
            updated_at_utc="2026-06-20T12:00:00Z",
        )
    }

    result = _resolve_player_name(
        "JOAO FONSECA!!!",
        canonical_players,
        overrides=overrides,
    )

    assert result.candidate_canonical_player_ids == ()
    assert result.resolved_canonical_player_id == "player:sackmann:2"
    assert result.resolved_canonical_player_name == "João Fonseca"
    assert result.resolution_source == "alias_override"
