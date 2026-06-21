from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import duckdb

from tennisprediction.config import Settings, get_settings
from tennisprediction.market_mapping.aliases import (
    PLAYER_ALIAS_OVERRIDES_PATH,
    load_player_alias_overrides,
    lookup_player_alias_override,
)
from tennisprediction.market_mapping.normalization import normalize_market_player_name
from tennisprediction.market_mapping.schemas import (
    MappingConfidenceTier,
    MarketMappingEvidenceRow,
    MarketMappingState,
    PlayerAliasOverrideRecord,
    PlayerNameResolutionResult,
    UnscorableMappingRecord,
)
from tennisprediction.storage.duckdb import _replace_table

_TITLE_VS_PATTERN = re.compile(
    r"(?P<left>.+?)\s+vs\s+(?P<right>.+)",
    re.IGNORECASE,
)
_REQUIRED_MARKET_COLUMNS = (
    "ticker",
    "event_ticker",
    "title",
    "yes_sub_title",
    "no_sub_title",
    "collected_at_utc",
)
_EVIDENCE_TABLE = "market_mapping_evidence"


@dataclass(frozen=True)
class _CanonicalPlayerRow:
    canonical_player_id: str
    full_name: str


@dataclass(frozen=True)
class _CanonicalMatchRow:
    canonical_match_id: str
    winner_canonical_player_id: str
    loser_canonical_player_id: str
    tourney_date: str


def resolve_kalshi_market_mappings(
    *,
    database_path: str | Path | None = None,
    alias_overrides_path: str | Path = PLAYER_ALIAS_OVERRIDES_PATH,
) -> list[MarketMappingEvidenceRow]:
    database_file = _resolve_database_path(database_path)
    try:
        overrides = load_player_alias_overrides(alias_overrides_path)
    except FileNotFoundError:
        overrides = {}

    connection = duckdb.connect(str(database_file))
    try:
        latest_markets = _load_latest_market_rows(connection)
        canonical_players = _load_canonical_players(connection)
        canonical_matches = _load_canonical_matches(connection)
    finally:
        connection.close()

    return [
        _resolve_single_market(
            market_row=market_row,
            canonical_players=canonical_players,
            canonical_matches=canonical_matches,
            overrides=overrides,
        )
        for market_row in latest_markets
    ]


def persist_market_mapping_evidence(
    rows: list[MarketMappingEvidenceRow],
    *,
    database_path: str | Path | None = None,
) -> Path:
    database_file = _resolve_database_path(database_path)
    database_file.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_file))
    try:
        _replace_table(
            connection,
            table_name=_EVIDENCE_TABLE,
            rows=[_evidence_row_as_dict(row) for row in rows],
            ddl="""
                create table market_mapping_evidence (
                    market_ticker varchar,
                    event_ticker varchar,
                    collected_at_utc timestamp,
                    raw_title varchar,
                    raw_yes_sub_title varchar,
                    raw_no_sub_title varchar,
                    normalized_yes_player_name varchar,
                    normalized_no_player_name varchar,
                    alias_hit_player_ids_json varchar,
                    candidate_canonical_match_ids_json varchar,
                    mapping_state varchar,
                    mapping_confidence varchar,
                    canonical_match_id varchar,
                    yes_canonical_player_id varchar,
                    no_canonical_player_id varchar,
                    yes_maps_to_player_a boolean,
                    no_maps_to_player_b boolean,
                    rejection_reason_codes_json varchar
                )
            """,
        )
    finally:
        connection.close()

    return database_file


def require_matched_mapping(
    row: MarketMappingEvidenceRow,
) -> UnscorableMappingRecord | None:
    if (
        row.mapping_state == MarketMappingState.matched
        and row.mapping_confidence != MappingConfidenceTier.manual_review_required
    ):
        return None

    rejection_reason_codes = row.rejection_reason_codes
    if row.mapping_confidence == MappingConfidenceTier.manual_review_required:
        rejection_reason_codes = _append_reason(
            rejection_reason_codes,
            "manual_review_required",
        )
    elif not rejection_reason_codes:
        rejection_reason_codes = (f"mapping_state_{row.mapping_state.value}",)

    return UnscorableMappingRecord(
        market_ticker=row.market_ticker,
        event_ticker=row.event_ticker,
        mapping_state=row.mapping_state,
        mapping_confidence=row.mapping_confidence,
        canonical_match_id=row.canonical_match_id,
        rejection_reason_codes=rejection_reason_codes,
    )


def _resolve_single_market(
    *,
    market_row: dict[str, Any],
    canonical_players: list[_CanonicalPlayerRow],
    canonical_matches: list[_CanonicalMatchRow],
    overrides: dict[str, PlayerAliasOverrideRecord],
) -> MarketMappingEvidenceRow:
    title = _required_str(market_row, "title")
    yes_sub_title = _required_str(market_row, "yes_sub_title")
    no_sub_title = _required_str(market_row, "no_sub_title")
    event_ticker = _required_str(market_row, "event_ticker")
    collected_at = _required_datetime(market_row, "collected_at_utc")

    normalized_yes = normalize_market_player_name(yes_sub_title)
    normalized_no = normalize_market_player_name(no_sub_title)

    if not event_ticker.startswith("ATP"):
        return _build_evidence_row(
            market_row=market_row,
            normalized_yes=normalized_yes,
            normalized_no=normalized_no,
            alias_hit_player_ids=(),
            candidate_match_ids=(),
            mapping_state=MarketMappingState.excluded,
            mapping_confidence=MappingConfidenceTier.manual_review_required,
            canonical_match_id=None,
            yes_canonical_player_id=None,
            no_canonical_player_id=None,
            yes_maps_to_player_a=None,
            no_maps_to_player_b=None,
            rejection_reason_codes=("non_atp_event",),
        )

    title_pair = _parse_title_pair(title)
    if title_pair is None:
        return _build_evidence_row(
            market_row=market_row,
            normalized_yes=normalized_yes,
            normalized_no=normalized_no,
            alias_hit_player_ids=(),
            candidate_match_ids=(),
            mapping_state=MarketMappingState.excluded,
            mapping_confidence=MappingConfidenceTier.manual_review_required,
            canonical_match_id=None,
            yes_canonical_player_id=None,
            no_canonical_player_id=None,
            yes_maps_to_player_a=None,
            no_maps_to_player_b=None,
            rejection_reason_codes=("unsupported_contract_shape",),
        )

    left_resolution = _resolve_player_name(
        raw_market_name=title_pair[0],
        canonical_players=canonical_players,
        overrides=overrides,
    )
    right_resolution = _resolve_player_name(
        raw_market_name=title_pair[1],
        canonical_players=canonical_players,
        overrides=overrides,
    )
    pair_reasons = _pair_resolution_reasons(left_resolution, right_resolution)
    pair_confidence = _resolution_confidence(left_resolution, right_resolution)

    alias_hit_player_ids = tuple(
        sorted(
            {
                resolution.resolved_canonical_player_id
                for resolution in (
                    left_resolution,
                    right_resolution,
                )
                if resolution.resolution_source == "alias_override"
                and resolution.resolved_canonical_player_id is not None
            }
        )
    )

    if pair_reasons:
        return _build_evidence_row(
            market_row=market_row,
            normalized_yes=normalized_yes,
            normalized_no=normalized_no,
            alias_hit_player_ids=alias_hit_player_ids,
            candidate_match_ids=(),
            mapping_state=MarketMappingState.ambiguous,
            mapping_confidence=MappingConfidenceTier.manual_review_required,
            canonical_match_id=None,
            yes_canonical_player_id=None,
            no_canonical_player_id=None,
            yes_maps_to_player_a=None,
            no_maps_to_player_b=None,
            rejection_reason_codes=pair_reasons,
        )

    assert left_resolution.resolved_canonical_player_id is not None
    assert right_resolution.resolved_canonical_player_id is not None

    same_day_matches = _same_day_candidate_matches(
        canonical_matches=canonical_matches,
        left_player_id=left_resolution.resolved_canonical_player_id,
        right_player_id=right_resolution.resolved_canonical_player_id,
        collected_at=collected_at,
    )

    if len(same_day_matches) > 1:
        return _build_evidence_row(
            market_row=market_row,
            normalized_yes=normalized_yes,
            normalized_no=normalized_no,
            alias_hit_player_ids=alias_hit_player_ids,
            candidate_match_ids=tuple(
                match.canonical_match_id for match in same_day_matches
            ),
            mapping_state=MarketMappingState.ambiguous,
            mapping_confidence=pair_confidence,
            canonical_match_id=None,
            yes_canonical_player_id=None,
            no_canonical_player_id=None,
            yes_maps_to_player_a=None,
            no_maps_to_player_b=None,
            rejection_reason_codes=("multiple_canonical_matches",),
        )

    if not same_day_matches:
        return _build_evidence_row(
            market_row=market_row,
            normalized_yes=normalized_yes,
            normalized_no=normalized_no,
            alias_hit_player_ids=alias_hit_player_ids,
            candidate_match_ids=(),
            mapping_state=MarketMappingState.unmatched,
            mapping_confidence=pair_confidence,
            canonical_match_id=None,
            yes_canonical_player_id=None,
            no_canonical_player_id=None,
            yes_maps_to_player_a=None,
            no_maps_to_player_b=None,
            rejection_reason_codes=("timing_window_miss",),
        )

    matched_canonical_match = same_day_matches[0]
    yes_resolution = _resolve_player_name(
        raw_market_name=yes_sub_title,
        canonical_players=canonical_players,
        overrides=overrides,
    )
    no_resolution = _resolve_player_name(
        raw_market_name=no_sub_title,
        canonical_players=canonical_players,
        overrides=overrides,
    )
    alias_hit_player_ids = tuple(
        sorted(
            {
                *alias_hit_player_ids,
                *(
                    resolution.resolved_canonical_player_id
                    for resolution in (yes_resolution, no_resolution)
                    if resolution.resolution_source == "alias_override"
                    and resolution.resolved_canonical_player_id is not None
                ),
            }
        )
    )
    overall_confidence = _resolution_confidence(
        left_resolution,
        right_resolution,
        yes_resolution,
        no_resolution,
    )

    orientation = _resolve_side_orientation(
        yes_resolution=yes_resolution,
        no_resolution=no_resolution,
        title_player_ids=(
            left_resolution.resolved_canonical_player_id,
            right_resolution.resolved_canonical_player_id,
        ),
        matched_canonical_match=matched_canonical_match,
    )
    if orientation is None:
        return _build_evidence_row(
            market_row=market_row,
            normalized_yes=normalized_yes,
            normalized_no=normalized_no,
            alias_hit_player_ids=alias_hit_player_ids,
            candidate_match_ids=(matched_canonical_match.canonical_match_id,),
            mapping_state=MarketMappingState.ambiguous,
            mapping_confidence=MappingConfidenceTier.manual_review_required,
            canonical_match_id=None,
            yes_canonical_player_id=None,
            no_canonical_player_id=None,
            yes_maps_to_player_a=None,
            no_maps_to_player_b=None,
            rejection_reason_codes=("ambiguous_side_orientation",),
        )

    yes_player_id, no_player_id, yes_maps_to_player_a, no_maps_to_player_b = orientation
    return _build_evidence_row(
        market_row=market_row,
        normalized_yes=normalized_yes,
        normalized_no=normalized_no,
        alias_hit_player_ids=alias_hit_player_ids,
        candidate_match_ids=(matched_canonical_match.canonical_match_id,),
        mapping_state=MarketMappingState.matched,
        mapping_confidence=overall_confidence,
        canonical_match_id=matched_canonical_match.canonical_match_id,
        yes_canonical_player_id=yes_player_id,
        no_canonical_player_id=no_player_id,
        yes_maps_to_player_a=yes_maps_to_player_a,
        no_maps_to_player_b=no_maps_to_player_b,
        rejection_reason_codes=(),
    )


def _load_latest_market_rows(
    connection: duckdb.DuckDBPyConnection,
) -> list[dict[str, Any]]:
    records = connection.execute(
        """
        with ranked as (
            select
                ticker,
                event_ticker,
                title,
                yes_sub_title,
                no_sub_title,
                collected_at_utc,
                row_number() over (
                    partition by ticker
                    order by collected_at_utc desc, response_index desc
                ) as snapshot_rank
            from kalshi_market_detail_snapshots
        )
        select
            ticker,
            event_ticker,
            title,
            yes_sub_title,
            no_sub_title,
            collected_at_utc
        from ranked
        where snapshot_rank = 1
        order by ticker
        """
    ).fetchall()
    return [
        dict(zip(_REQUIRED_MARKET_COLUMNS, record, strict=True))
        for record in records
    ]


def _load_canonical_players(
    connection: duckdb.DuckDBPyConnection,
) -> list[_CanonicalPlayerRow]:
    records = connection.execute(
        """
        select canonical_player_id, full_name
        from canonical_players
        order by canonical_player_id
        """
    ).fetchall()
    return [
        _CanonicalPlayerRow(
            canonical_player_id=canonical_player_id,
            full_name=full_name,
        )
        for canonical_player_id, full_name in records
    ]


def _load_canonical_matches(
    connection: duckdb.DuckDBPyConnection,
) -> list[_CanonicalMatchRow]:
    records = connection.execute(
        """
        select
            canonical_match_id,
            winner_canonical_player_id,
            loser_canonical_player_id,
            tourney_date
        from canonical_matches
        order by canonical_match_id
        """
    ).fetchall()
    return [
        _CanonicalMatchRow(
            canonical_match_id=canonical_match_id,
            winner_canonical_player_id=winner_canonical_player_id,
            loser_canonical_player_id=loser_canonical_player_id,
            tourney_date=tourney_date,
        )
        for (
            canonical_match_id,
            winner_canonical_player_id,
            loser_canonical_player_id,
            tourney_date,
        ) in records
    ]


def _parse_title_pair(title: str) -> tuple[str, str] | None:
    _, _, trailing_title = title.rpartition(":")
    candidate = trailing_title.strip() if trailing_title else title.strip()
    match = _TITLE_VS_PATTERN.fullmatch(candidate)
    if match is None:
        return None
    left = match.group("left").strip()
    right = match.group("right").strip()
    if not left or not right:
        return None
    return left, right


def _resolve_player_name(
    *,
    raw_market_name: str,
    canonical_players: list[_CanonicalPlayerRow],
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

    matching_players = [
        player
        for player in canonical_players
        if normalize_market_player_name(player.full_name) == normalized_market_name
    ]
    if len(matching_players) == 1:
        matched_player = matching_players[0]
        return PlayerNameResolutionResult(
            raw_market_name=raw_market_name,
            normalized_market_name=normalized_market_name,
            candidate_canonical_player_ids=(matched_player.canonical_player_id,),
            resolved_canonical_player_id=matched_player.canonical_player_id,
            resolved_canonical_player_name=matched_player.full_name,
            resolution_source="unique_normalized_match",
        )

    return PlayerNameResolutionResult(
        raw_market_name=raw_market_name,
        normalized_market_name=normalized_market_name,
        candidate_canonical_player_ids=tuple(
            player.canonical_player_id for player in matching_players
        ),
        resolved_canonical_player_id=None,
        resolved_canonical_player_name=None,
        resolution_source="unresolved",
    )


def _pair_resolution_reasons(
    left_resolution: PlayerNameResolutionResult,
    right_resolution: PlayerNameResolutionResult,
) -> tuple[str, ...]:
    if (
        not left_resolution.resolved_canonical_player_id
        or not right_resolution.resolved_canonical_player_id
    ):
        return ("ambiguous_player_identity",)
    if (
        left_resolution.resolved_canonical_player_id
        == right_resolution.resolved_canonical_player_id
    ):
        return ("duplicate_player_identity",)
    return ()


def _resolution_confidence(
    *resolutions: PlayerNameResolutionResult,
) -> MappingConfidenceTier:
    if any(
        resolution.resolution_source == "unresolved"
        for resolution in resolutions
    ):
        return MappingConfidenceTier.manual_review_required
    if any(
        resolution.resolution_source == "alias_override"
        for resolution in resolutions
    ):
        return MappingConfidenceTier.alias_override
    return MappingConfidenceTier.exact_names


def _same_day_candidate_matches(
    *,
    canonical_matches: list[_CanonicalMatchRow],
    left_player_id: str,
    right_player_id: str,
    collected_at: datetime,
) -> list[_CanonicalMatchRow]:
    pair_ids = {left_player_id, right_player_id}
    same_day = collected_at.strftime("%Y%m%d")
    return [
        match
        for match in canonical_matches
        if {match.winner_canonical_player_id, match.loser_canonical_player_id} == pair_ids
        and match.tourney_date == same_day
    ]


def _resolve_side_orientation(
    *,
    yes_resolution: PlayerNameResolutionResult,
    no_resolution: PlayerNameResolutionResult,
    title_player_ids: tuple[str, str],
    matched_canonical_match: _CanonicalMatchRow,
) -> tuple[str, str, bool, bool] | None:
    yes_player_id = yes_resolution.resolved_canonical_player_id
    no_player_id = no_resolution.resolved_canonical_player_id
    if yes_player_id is None or no_player_id is None:
        return None
    if yes_player_id == no_player_id:
        return None
    if {yes_player_id, no_player_id} != set(title_player_ids):
        return None

    player_a_id = matched_canonical_match.winner_canonical_player_id
    player_b_id = matched_canonical_match.loser_canonical_player_id
    return (
        yes_player_id,
        no_player_id,
        yes_player_id == player_a_id,
        no_player_id == player_b_id,
    )


def _build_evidence_row(
    *,
    market_row: dict[str, Any],
    normalized_yes: str,
    normalized_no: str,
    alias_hit_player_ids: tuple[str, ...],
    candidate_match_ids: tuple[str, ...],
    mapping_state: MarketMappingState,
    mapping_confidence: MappingConfidenceTier,
    canonical_match_id: str | None,
    yes_canonical_player_id: str | None,
    no_canonical_player_id: str | None,
    yes_maps_to_player_a: bool | None,
    no_maps_to_player_b: bool | None,
    rejection_reason_codes: tuple[str, ...],
) -> MarketMappingEvidenceRow:
    return MarketMappingEvidenceRow(
        market_ticker=_required_str(market_row, "ticker"),
        event_ticker=_required_str(market_row, "event_ticker"),
        collected_at_utc=_required_datetime(market_row, "collected_at_utc"),
        raw_title=_required_str(market_row, "title"),
        raw_yes_sub_title=_required_str(market_row, "yes_sub_title"),
        raw_no_sub_title=_required_str(market_row, "no_sub_title"),
        normalized_yes_player_name=normalized_yes,
        normalized_no_player_name=normalized_no,
        alias_hit_player_ids=alias_hit_player_ids,
        candidate_canonical_match_ids=candidate_match_ids,
        mapping_state=mapping_state,
        mapping_confidence=mapping_confidence,
        canonical_match_id=canonical_match_id,
        yes_canonical_player_id=yes_canonical_player_id,
        no_canonical_player_id=no_canonical_player_id,
        yes_maps_to_player_a=yes_maps_to_player_a,
        no_maps_to_player_b=no_maps_to_player_b,
        rejection_reason_codes=rejection_reason_codes,
    )


def _evidence_row_as_dict(row: MarketMappingEvidenceRow) -> dict[str, Any]:
    raw_row = asdict(row)
    raw_row["alias_hit_player_ids_json"] = json.dumps(
        list(raw_row.pop("alias_hit_player_ids")),
        sort_keys=True,
        separators=(",", ":"),
    )
    raw_row["candidate_canonical_match_ids_json"] = json.dumps(
        list(raw_row.pop("candidate_canonical_match_ids")),
        sort_keys=True,
        separators=(",", ":"),
    )
    raw_row["rejection_reason_codes_json"] = json.dumps(
        list(raw_row.pop("rejection_reason_codes")),
        sort_keys=True,
        separators=(",", ":"),
    )
    raw_row["mapping_state"] = row.mapping_state.value
    raw_row["mapping_confidence"] = row.mapping_confidence.value
    return raw_row


def _append_reason(
    existing_reasons: tuple[str, ...],
    reason: str,
) -> tuple[str, ...]:
    if reason in existing_reasons:
        return existing_reasons
    return existing_reasons + (reason,)


def _required_str(row: dict[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str):
        msg = f"{key} must be a string"
        raise TypeError(msg)
    return value


def _required_datetime(row: dict[str, Any], key: str) -> datetime:
    value = row.get(key)
    if not isinstance(value, datetime):
        msg = f"{key} must be a datetime"
        raise TypeError(msg)
    return value


def _resolve_database_path(database_path: str | Path | None) -> Path:
    settings = get_settings()
    if database_path is None:
        return settings.duckdb_path
    return Settings._resolve_repo_path(Path(database_path))
