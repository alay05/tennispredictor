from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class RawSchema:
    required_columns: tuple[str, ...]
    integer_columns: tuple[str, ...] = ()
    optional_integer_columns: tuple[str, ...] = ()
    date_columns: tuple[str, ...] = ()


RawPlayerSchema = RawSchema(
    required_columns=("player_id", "name_first", "name_last"),
    integer_columns=("player_id",),
)
RawRankingSchema = RawSchema(
    required_columns=("ranking_date", "rank", "player", "points"),
    integer_columns=("rank", "player", "points"),
    date_columns=("ranking_date",),
)
RawTournamentSchema = RawSchema(
    required_columns=(
        "tourney_id",
        "tourney_name",
        "surface",
        "tourney_level",
        "tourney_date",
    ),
    date_columns=("tourney_date",),
)
RawMatchSchema = RawSchema(
    required_columns=(
        "tourney_id",
        "surface",
        "tourney_name",
        "tourney_date",
        "tourney_level",
        "winner_id",
        "loser_id",
        "score",
        "best_of",
        "round",
    ),
    integer_columns=("winner_id", "loser_id", "best_of"),
    date_columns=("tourney_date",),
)
RawMatchStatSchema = RawSchema(
    required_columns=("match_id", "1stWon1", "1stWon2"),
    integer_columns=("match_id",),
    optional_integer_columns=("ace1", "ace2", "svpt1", "svpt2"),
)


def schema_for_file(relative_path: str | Path) -> RawSchema:
    name = Path(relative_path).name
    if name == "atp_players.csv":
        return RawPlayerSchema
    if name.startswith("atp_rankings"):
        return RawRankingSchema
    if name.startswith("atp_matches_"):
        return RawMatchSchema
    if name.startswith("atp_matchstats_"):
        return RawMatchStatSchema
    msg = f"no schema registered for {name}"
    raise KeyError(msg)


def validate_date_value(value: str, *, file_name: str, column: str) -> None:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        msg = f"{file_name}: column {column} must parse as YYYYMMDD date"
        raise ValueError(msg) from exc
