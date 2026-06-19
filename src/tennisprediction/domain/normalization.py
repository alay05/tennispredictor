from __future__ import annotations

from collections.abc import Iterable

from tennisprediction.domain.ids import CanonicalIdFactory
from tennisprediction.domain.models import (
    CanonicalMatch,
    CanonicalMatchStat,
    CanonicalPlayer,
    CanonicalRanking,
    CanonicalSnapshot,
    CanonicalTournament,
    SourceLineage,
)
from tennisprediction.ingestion.quarantine import split_validated_snapshot
from tennisprediction.ingestion.validation import ValidatedSnapshot


def _build_lineage(
    validated_snapshot: ValidatedSnapshot, *, source_file_path: str, source_row_number: int
) -> SourceLineage:
    return SourceLineage(
        source_repo=validated_snapshot.manifest.source_repo,
        source_commit_sha=validated_snapshot.manifest.commit_sha,
        source_file_path=source_file_path,
        source_row_number=source_row_number,
        source_snapshot_root=str(validated_snapshot.manifest.snapshot_root),
    )


def _iter_rows(
    rows_by_file: dict[str, list[dict[str, str]]],
) -> Iterable[tuple[str, int, dict[str, str]]]:
    for source_file_path, rows in rows_by_file.items():
        for source_row_number, row in enumerate(rows, start=2):
            yield source_file_path, source_row_number, row


def _normalize_players(
    validated_snapshot: ValidatedSnapshot,
    rows: dict[str, list[dict[str, str]]],
) -> list[CanonicalPlayer]:
    players: list[CanonicalPlayer] = []
    seen_ids: set[int] = set()
    for source_file_path, source_row_number, row in _iter_rows(rows):
        if source_file_path != "atp_players.csv":
            continue

        source_player_id = int(row["player_id"])
        if source_player_id in seen_ids:
            continue
        seen_ids.add(source_player_id)
        players.append(
            CanonicalPlayer(
                canonical_player_id=CanonicalIdFactory.player_id(source_player_id),
                source_player_id=source_player_id,
                first_name=row["name_first"].strip(),
                last_name=row["name_last"].strip(),
                full_name=f"{row['name_first'].strip()} {row['name_last'].strip()}".strip(),
                lineage=_build_lineage(
                    validated_snapshot,
                    source_file_path=source_file_path,
                    source_row_number=source_row_number,
                ),
            )
        )
    return players


def _normalize_tournaments(
    validated_snapshot: ValidatedSnapshot, rows: dict[str, list[dict[str, str]]]
) -> list[CanonicalTournament]:
    tournaments: list[CanonicalTournament] = []
    seen_ids: set[str] = set()
    for source_file_path, source_row_number, row in _iter_rows(rows):
        if not source_file_path.startswith("atp_matches_"):
            continue

        canonical_tournament_id = CanonicalIdFactory.tournament_id(
            source_tourney_id=row["tourney_id"],
            tourney_name=row["tourney_name"],
            tourney_date=row["tourney_date"],
        )
        if canonical_tournament_id in seen_ids:
            continue
        seen_ids.add(canonical_tournament_id)
        tournaments.append(
            CanonicalTournament(
                canonical_tournament_id=canonical_tournament_id,
                source_tourney_id=row["tourney_id"].strip(),
                tourney_name=row["tourney_name"].strip(),
                surface=row["surface"].strip(),
                tourney_level=row["tourney_level"].strip(),
                tourney_date=row["tourney_date"].strip(),
                lineage=_build_lineage(
                    validated_snapshot,
                    source_file_path=source_file_path,
                    source_row_number=source_row_number,
                ),
            )
        )
    return tournaments


def _normalize_matches(
    validated_snapshot: ValidatedSnapshot, rows: dict[str, list[dict[str, str]]]
) -> list[CanonicalMatch]:
    matches: list[CanonicalMatch] = []
    for source_file_path, source_row_number, row in _iter_rows(rows):
        if not source_file_path.startswith("atp_matches_"):
            continue

        canonical_tournament_id = CanonicalIdFactory.tournament_id(
            source_tourney_id=row["tourney_id"],
            tourney_name=row["tourney_name"],
            tourney_date=row["tourney_date"],
        )
        winner_source_player_id = int(row["winner_id"])
        loser_source_player_id = int(row["loser_id"])
        matches.append(
            CanonicalMatch(
                canonical_match_id=CanonicalIdFactory.match_id(
                    source_file_path=source_file_path,
                    source_row_number=source_row_number,
                    source_tourney_id=row["tourney_id"],
                    winner_source_player_id=winner_source_player_id,
                    loser_source_player_id=loser_source_player_id,
                    round_name=row["round"],
                ),
                canonical_tournament_id=canonical_tournament_id,
                winner_canonical_player_id=CanonicalIdFactory.player_id(winner_source_player_id),
                loser_canonical_player_id=CanonicalIdFactory.player_id(loser_source_player_id),
                source_tourney_id=row["tourney_id"].strip(),
                surface=row["surface"].strip(),
                tourney_name=row["tourney_name"].strip(),
                tourney_level=row["tourney_level"].strip(),
                tourney_date=row["tourney_date"].strip(),
                round_name=row["round"].strip(),
                best_of=int(row["best_of"]),
                score=row["score"].strip(),
                lineage=_build_lineage(
                    validated_snapshot,
                    source_file_path=source_file_path,
                    source_row_number=source_row_number,
                ),
            )
        )
    return matches


def _normalize_rankings(
    validated_snapshot: ValidatedSnapshot, rows: dict[str, list[dict[str, str]]]
) -> list[CanonicalRanking]:
    rankings: list[CanonicalRanking] = []
    for source_file_path, source_row_number, row in _iter_rows(rows):
        if not source_file_path.startswith("atp_rankings"):
            continue

        source_player_id = int(row["player"])
        rankings.append(
            CanonicalRanking(
                canonical_ranking_id=CanonicalIdFactory.ranking_id(
                    source_player_id=source_player_id,
                    ranking_date=row["ranking_date"],
                ),
                canonical_player_id=CanonicalIdFactory.player_id(source_player_id),
                ranking_date=row["ranking_date"].strip(),
                rank=int(row["rank"]),
                points=int(row["points"]),
                lineage=_build_lineage(
                    validated_snapshot,
                    source_file_path=source_file_path,
                    source_row_number=source_row_number,
                ),
            )
        )
    return rankings


def _normalize_match_stats(
    validated_snapshot: ValidatedSnapshot, rows: dict[str, list[dict[str, str]]]
) -> list[CanonicalMatchStat]:
    match_stats: list[CanonicalMatchStat] = []
    for source_file_path, source_row_number, row in _iter_rows(rows):
        if not source_file_path.startswith("atp_matchstats_"):
            continue

        def _optional_int(value: str) -> int | None:
            stripped = value.strip()
            return int(stripped) if stripped else None

        source_match_id = int(row["match_id"])
        match_stats.append(
            CanonicalMatchStat(
                canonical_match_stat_id=CanonicalIdFactory.match_stat_id(source_match_id),
                source_match_id=source_match_id,
                first_won_player1=int(row["1stWon1"]),
                first_won_player2=int(row["1stWon2"]),
                ace_player1=_optional_int(row.get("ace1", "")),
                ace_player2=_optional_int(row.get("ace2", "")),
                serve_points_player1=_optional_int(row.get("svpt1", "")),
                serve_points_player2=_optional_int(row.get("svpt2", "")),
                lineage=_build_lineage(
                    validated_snapshot,
                    source_file_path=source_file_path,
                    source_row_number=source_row_number,
                ),
            )
        )
    return match_stats


def normalize_snapshot(validated_snapshot: ValidatedSnapshot) -> CanonicalSnapshot:
    partitioned = split_validated_snapshot(validated_snapshot)
    accepted_rows = partitioned.accepted_rows

    return CanonicalSnapshot(
        players=_normalize_players(validated_snapshot, accepted_rows),
        tournaments=_normalize_tournaments(validated_snapshot, accepted_rows),
        matches=_normalize_matches(validated_snapshot, accepted_rows),
        rankings=_normalize_rankings(validated_snapshot, accepted_rows),
        match_stats=_normalize_match_stats(validated_snapshot, accepted_rows),
        quarantined_rows=partitioned.quarantined_rows,
        quarantined_files=partitioned.quarantined_files,
    )
