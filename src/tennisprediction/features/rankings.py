from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from tennisprediction.domain.models import CanonicalRanking


@dataclass(frozen=True)
class AttachedRanking:
    rank: int | None
    rank_points: int | None
    ranking_change: int | None
    previous_rank: int | None
    previous_rank_points: int | None
    previous_ranking_date: str | None
    rank_missing: bool
    rank_points_missing: bool
    ranking_age_days: int | None


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d")


def _ranking_sort_key(ranking: CanonicalRanking) -> tuple[str, str, int]:
    return (
        ranking.ranking_date,
        ranking.lineage.source_file_path,
        ranking.lineage.source_row_number,
    )


def attach_prior_rankings(
    *,
    canonical_player_id: str,
    as_of_date: str,
    rankings: list[CanonicalRanking],
) -> AttachedRanking:
    eligible_rankings = sorted(
        [
            ranking
            for ranking in rankings
            if ranking.canonical_player_id == canonical_player_id
            and ranking.ranking_date <= as_of_date
        ],
        key=_ranking_sort_key,
    )
    if not eligible_rankings:
        return AttachedRanking(
            rank=None,
            rank_points=None,
            ranking_change=None,
            previous_rank=None,
            previous_rank_points=None,
            previous_ranking_date=None,
            rank_missing=True,
            rank_points_missing=True,
            ranking_age_days=None,
        )

    selected_ranking = eligible_rankings[-1]
    previous_ranking = eligible_rankings[-2] if len(eligible_rankings) > 1 else None
    ranking_change = None
    if previous_ranking is not None:
        ranking_change = selected_ranking.rank - previous_ranking.rank

    return AttachedRanking(
        rank=selected_ranking.rank,
        rank_points=selected_ranking.points,
        ranking_change=ranking_change,
        previous_rank=previous_ranking.rank if previous_ranking is not None else None,
        previous_rank_points=previous_ranking.points if previous_ranking is not None else None,
        previous_ranking_date=(
            previous_ranking.ranking_date if previous_ranking is not None else None
        ),
        rank_missing=False,
        rank_points_missing=False,
        ranking_age_days=(
            _parse_date(as_of_date) - _parse_date(selected_ranking.ranking_date)
        ).days,
    )
