from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from tennisprediction.market_mapping.resolver import (
    require_matched_mapping,
    resolve_kalshi_market_mappings,
)
from tennisprediction.market_mapping.schemas import MappingConfidenceTier
from tests.unit.test_market_mapping_resolver import _seed_mapping_database


def test_require_matched_mapping_rejects_unmatched_and_manual_review_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = _seed_mapping_database(
        tmp_path,
        monkeypatch,
        market_title="ATP London: Taylor Fritz vs Frances Tiafoe",
        yes_sub_title="Taylor Fritz",
        no_sub_title="Frances Tiafoe",
        canonical_players=[
            ("player:fritz", "Taylor", "Fritz", "Taylor Fritz"),
            ("player:tiafoe", "Frances", "Tiafoe", "Frances Tiafoe"),
        ],
        canonical_matches=[
            {
                "canonical_match_id": "match:future-date",
                "winner_canonical_player_id": "player:fritz",
                "loser_canonical_player_id": "player:tiafoe",
                "tourney_date": "20240621",
                "round_name": "R16",
            }
        ],
    )

    unmatched_row = resolve_kalshi_market_mappings(database_path=database_path)[0]
    unmatched_rejection = require_matched_mapping(unmatched_row)
    assert unmatched_rejection is not None
    assert unmatched_rejection.market_ticker == unmatched_row.market_ticker
    assert unmatched_rejection.mapping_state == unmatched_row.mapping_state
    assert "timing_window_miss" in unmatched_rejection.rejection_reason_codes

    manual_review_row = replace(
        unmatched_row,
        mapping_state=unmatched_row.mapping_state.matched,
        mapping_confidence=MappingConfidenceTier.manual_review_required,
        rejection_reason_codes=(),
    )
    manual_review_rejection = require_matched_mapping(manual_review_row)
    assert manual_review_rejection is not None
    assert manual_review_rejection.market_ticker == unmatched_row.market_ticker
    assert "manual_review_required" in manual_review_rejection.rejection_reason_codes
