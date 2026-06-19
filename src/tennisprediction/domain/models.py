from __future__ import annotations

from dataclasses import dataclass

from tennisprediction.ingestion.validation import FileQuarantineRecord


@dataclass(frozen=True)
class SourceLineage:
    source_repo: str
    source_commit_sha: str
    source_file_path: str
    source_row_number: int
    source_snapshot_root: str


@dataclass(frozen=True)
class CanonicalPlayer:
    canonical_player_id: str
    source_player_id: int
    first_name: str
    last_name: str
    full_name: str
    lineage: SourceLineage


@dataclass(frozen=True)
class CanonicalTournament:
    canonical_tournament_id: str
    source_tourney_id: str
    tourney_name: str
    surface: str
    tourney_level: str
    tourney_date: str
    lineage: SourceLineage


@dataclass(frozen=True)
class CanonicalMatch:
    canonical_match_id: str
    canonical_tournament_id: str
    winner_canonical_player_id: str
    loser_canonical_player_id: str
    source_tourney_id: str
    surface: str
    tourney_name: str
    tourney_level: str
    tourney_date: str
    round_name: str
    best_of: int
    score: str
    lineage: SourceLineage


@dataclass(frozen=True)
class CanonicalRanking:
    canonical_ranking_id: str
    canonical_player_id: str
    ranking_date: str
    rank: int
    points: int
    lineage: SourceLineage


@dataclass(frozen=True)
class CanonicalMatchStat:
    canonical_match_stat_id: str
    source_match_id: int
    first_won_player1: int
    first_won_player2: int
    ace_player1: int | None
    ace_player2: int | None
    serve_points_player1: int | None
    serve_points_player2: int | None
    lineage: SourceLineage


@dataclass(frozen=True)
class CanonicalSnapshot:
    players: list[CanonicalPlayer]
    tournaments: list[CanonicalTournament]
    matches: list[CanonicalMatch]
    rankings: list[CanonicalRanking]
    match_stats: list[CanonicalMatchStat]
    quarantined_rows: dict[str, list[dict[str, str]]]
    quarantined_files: dict[str, FileQuarantineRecord]
