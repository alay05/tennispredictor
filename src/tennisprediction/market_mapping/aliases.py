from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tennisprediction.config import Settings
from tennisprediction.market_mapping.normalization import normalize_market_player_name
from tennisprediction.market_mapping.schemas import PlayerAliasOverrideRecord

PLAYER_ALIAS_OVERRIDES_PATH = Path(
    "src/tennisprediction/market_mapping/player_alias_overrides.json"
)
_REQUIRED_ALIAS_FIELDS = (
    "raw_market_name",
    "normalized_market_name",
    "canonical_player_id",
    "canonical_player_name",
    "source_note",
    "created_at_utc",
    "updated_at_utc",
)


def load_player_alias_overrides(
    path: str | Path = PLAYER_ALIAS_OVERRIDES_PATH,
) -> dict[str, PlayerAliasOverrideRecord]:
    candidate_path = Path(path)
    artifact_path = (
        candidate_path.resolve(strict=False)
        if candidate_path.is_absolute()
        else Settings._resolve_repo_path(candidate_path)
    )
    if not artifact_path.is_file():
        raise FileNotFoundError(artifact_path)

    raw_payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    if not isinstance(raw_payload, list):
        msg = "alias override artifact must contain a JSON list"
        raise ValueError(msg)

    overrides: dict[str, PlayerAliasOverrideRecord] = {}
    seen_raw_names: set[str] = set()
    seen_normalized_names: set[str] = set()

    for row in raw_payload:
        record = _validate_alias_row(row)

        raw_key = normalize_market_player_name(record.raw_market_name)
        normalized_key = record.normalized_market_name

        if raw_key in seen_raw_names:
            msg = f"duplicate alias raw_market_name key: {record.raw_market_name}"
            raise ValueError(msg)
        if normalized_key in seen_normalized_names:
            msg = f"duplicate alias normalized_market_name key: {record.normalized_market_name}"
            raise ValueError(msg)

        seen_raw_names.add(raw_key)
        seen_normalized_names.add(normalized_key)
        overrides[raw_key] = record
        overrides[normalized_key] = record

    return overrides


def lookup_player_alias_override(
    raw_market_name: str,
    overrides: dict[str, PlayerAliasOverrideRecord],
) -> PlayerAliasOverrideRecord | None:
    normalized_lookup = normalize_market_player_name(raw_market_name)
    if raw_market_name in overrides:
        return overrides[raw_market_name]
    return overrides.get(normalized_lookup)


def _validate_alias_row(row: Any) -> PlayerAliasOverrideRecord:
    if not isinstance(row, dict):
        msg = "alias override row must be a JSON object"
        raise ValueError(msg)

    missing_fields = [field_name for field_name in _REQUIRED_ALIAS_FIELDS if field_name not in row]
    if missing_fields:
        msg = f"alias override row missing required fields: {', '.join(missing_fields)}"
        raise ValueError(msg)

    values: dict[str, str] = {}
    for field_name in _REQUIRED_ALIAS_FIELDS:
        value = row[field_name]
        if not isinstance(value, str):
            msg = f"alias override field {field_name} must be a string"
            raise ValueError(msg)
        stripped_value = value.strip()
        if not stripped_value:
            msg = f"alias override field {field_name} must not be empty"
            raise ValueError(msg)
        values[field_name] = stripped_value

    normalized_market_name = normalize_market_player_name(values["normalized_market_name"])
    if normalized_market_name != values["normalized_market_name"]:
        msg = "alias override normalized_market_name must already be normalized"
        raise ValueError(msg)

    return PlayerAliasOverrideRecord(
        raw_market_name=values["raw_market_name"],
        normalized_market_name=values["normalized_market_name"],
        canonical_player_id=values["canonical_player_id"],
        canonical_player_name=values["canonical_player_name"],
        source_note=values["source_note"],
        created_at_utc=values["created_at_utc"],
        updated_at_utc=values["updated_at_utc"],
    )
