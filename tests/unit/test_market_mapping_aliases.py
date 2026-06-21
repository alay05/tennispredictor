from __future__ import annotations

import json
from pathlib import Path

import pytest

from tennisprediction.config import Settings
from tennisprediction.market_mapping.aliases import (
    PLAYER_ALIAS_OVERRIDES_PATH,
    load_player_alias_overrides,
    lookup_player_alias_override,
)


def _write_alias_artifact(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    artifact_path = tmp_path / "player_alias_overrides.json"
    artifact_path.write_text(json.dumps(rows, indent=2), encoding="utf-8")
    return artifact_path


def test_alias_artifact_default_path_is_version_controlled_src_file() -> None:
    resolved_path = Settings._resolve_repo_path(PLAYER_ALIAS_OVERRIDES_PATH)

    assert resolved_path == Settings._resolve_repo_path(
        Path("src/tennisprediction/market_mapping/player_alias_overrides.json")
    )
    assert resolved_path.is_relative_to(Settings().repo_root / "src")
    assert not resolved_path.is_relative_to(Settings().data_dir)


def test_alias_rows_require_all_audit_fields(tmp_path: Path) -> None:
    artifact_path = _write_alias_artifact(
        tmp_path,
        [
            {
                "raw_market_name": "Alex De Minaur",
                "normalized_market_name": "alex de minaur",
                "canonical_player_id": "player:sackmann:123",
                "canonical_player_name": "Alex De Minaur",
                "created_at_utc": "2026-06-20T12:00:00Z",
                "updated_at_utc": "2026-06-20T12:00:00Z",
            }
        ],
    )

    with pytest.raises(ValueError, match="source_note"):
        load_player_alias_overrides(artifact_path)


def test_load_player_alias_overrides_reads_empty_auditable_artifact(tmp_path: Path) -> None:
    artifact_path = _write_alias_artifact(
        tmp_path,
        [],
    )

    assert load_player_alias_overrides(artifact_path) == {}


def test_lookup_player_alias_override_is_additive_for_raw_and_normalized_names(
    tmp_path: Path,
) -> None:
    artifact_path = _write_alias_artifact(
        tmp_path,
        [
            {
                "raw_market_name": "A. de Minaur",
                "normalized_market_name": "a de minaur",
                "canonical_player_id": "player:sackmann:123",
                "canonical_player_name": "Alex De Minaur",
                "source_note": "Kalshi title abbreviates first name",
                "created_at_utc": "2026-06-20T12:00:00Z",
                "updated_at_utc": "2026-06-20T12:00:00Z",
            }
        ],
    )

    overrides = load_player_alias_overrides(artifact_path)

    raw_match = lookup_player_alias_override("A. de Minaur", overrides)
    normalized_match = lookup_player_alias_override("A de Minaur", overrides)

    assert raw_match is not None
    assert normalized_match is not None
    assert raw_match.canonical_player_id == "player:sackmann:123"
    assert normalized_match.canonical_player_id == "player:sackmann:123"
    assert lookup_player_alias_override("Completely Unknown", overrides) is None


def test_duplicate_alias_rows_fail_loudly_without_rewriting_canonical_ids(tmp_path: Path) -> None:
    artifact_path = _write_alias_artifact(
        tmp_path,
        [
            {
                "raw_market_name": "A. de Minaur",
                "normalized_market_name": "a de minaur",
                "canonical_player_id": "player:sackmann:123",
                "canonical_player_name": "Alex De Minaur",
                "source_note": "first mapping",
                "created_at_utc": "2026-06-20T12:00:00Z",
                "updated_at_utc": "2026-06-20T12:00:00Z",
            },
            {
                "raw_market_name": "A de Minaur",
                "normalized_market_name": "a de minaur",
                "canonical_player_id": "player:sackmann:999",
                "canonical_player_name": "Someone Else",
                "source_note": "conflicting rewrite attempt",
                "created_at_utc": "2026-06-20T12:05:00Z",
                "updated_at_utc": "2026-06-20T12:05:00Z",
            },
        ],
    )

    with pytest.raises(ValueError, match="duplicate"):
        load_player_alias_overrides(artifact_path)
