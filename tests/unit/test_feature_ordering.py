from __future__ import annotations

import pytest

from tennisprediction.domain.models import CanonicalMatch, SourceLineage
from tennisprediction.features.ordering import build_match_cohorts


def _lineage(*, file_name: str, row_number: int) -> SourceLineage:
    return SourceLineage(
        source_repo="JeffSackmann/tennis_atp",
        source_commit_sha="abcdef1",
        source_file_path=file_name,
        source_row_number=row_number,
        source_snapshot_root="/tmp/raw-snapshot",
    )


def test_build_match_cohorts_rejects_unknown_round_token() -> None:
    match = CanonicalMatch(
        canonical_match_id="match:synthetic:unknown-round",
        canonical_tournament_id="tournament:synthetic:example-open:20240115",
        winner_canonical_player_id="player:sackmann:1",
        loser_canonical_player_id="player:sackmann:2",
        source_tourney_id="2024-001",
        surface="Hard",
        tourney_name="Example Open",
        tourney_level="A",
        tourney_date="20240115",
        round_name="WEIRD",
        best_of=3,
        score="6-4 6-4",
        lineage=_lineage(file_name="atp_matches_2024.csv", row_number=2),
    )

    with pytest.raises(ValueError, match="WEIRD"):
        build_match_cohorts([match])
