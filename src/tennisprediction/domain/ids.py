from __future__ import annotations

from hashlib import sha256


class CanonicalIdFactory:
    """Deterministic canonical IDs derived from source identity."""

    @staticmethod
    def player_id(source_player_id: int | str) -> str:
        return f"player:sackmann:{int(source_player_id)}"

    @staticmethod
    def tournament_id(*, source_tourney_id: str, tourney_name: str, tourney_date: str) -> str:
        payload = "|".join(
            (
                "tournament",
                source_tourney_id.strip(),
                tourney_name.strip().lower(),
                tourney_date.strip(),
            )
        )
        return f"tournament:synthetic:{sha256(payload.encode('utf-8')).hexdigest()[:16]}"

    @staticmethod
    def match_id(
        *,
        source_file_path: str,
        source_row_number: int,
        source_tourney_id: str,
        winner_source_player_id: int | str,
        loser_source_player_id: int | str,
        round_name: str,
    ) -> str:
        payload = "|".join(
            (
                "match",
                source_file_path,
                str(source_row_number),
                source_tourney_id.strip(),
                str(int(winner_source_player_id)),
                str(int(loser_source_player_id)),
                round_name.strip().upper(),
            )
        )
        return f"match:synthetic:{sha256(payload.encode('utf-8')).hexdigest()[:16]}"

    @staticmethod
    def ranking_id(*, source_player_id: int | str, ranking_date: str) -> str:
        payload = "|".join(("ranking", str(int(source_player_id)), ranking_date.strip()))
        return f"ranking:synthetic:{sha256(payload.encode('utf-8')).hexdigest()[:16]}"

    @staticmethod
    def match_stat_id(source_match_id: int | str) -> str:
        return f"match-stat:sackmann:{int(source_match_id)}"
