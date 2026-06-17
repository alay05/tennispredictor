from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from tennisprediction.domain.models import CanonicalMatch

BASE_ELO = 1500.0
ELO_K_FACTOR = 32.0
FORM_WINDOW_SIZES = (5, 10, 20)


@dataclass(frozen=True)
class PlayerFeatureState:
    elo_overall: float = BASE_ELO
    elo_by_surface: dict[str, float] | None = None
    last_played_date: str | None = None
    recent_results: tuple[int, ...] = ()
    matches_played_before: int = 0

    def surface_elo(self, surface: str) -> float:
        if self.elo_by_surface is None or surface not in self.elo_by_surface:
            return BASE_ELO
        return self.elo_by_surface[surface]


@dataclass(frozen=True)
class PreMatchStateSnapshot:
    elo_overall: float
    elo_surface: float
    rest_days: int | None
    form_last_5_win_rate: float | None
    form_last_10_win_rate: float | None
    form_last_20_win_rate: float | None
    form_last_5_count: int
    form_last_10_count: int
    form_last_20_count: int


@dataclass(frozen=True)
class PlayerStateAuditRecord:
    canonical_match_id: str
    canonical_player_id: str
    as_of_date: str
    surface: str
    metric_name: str
    pre_value: float | None
    post_value: float | None
    pre_count: int | None
    post_count: int | None


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y%m%d")


def _clone_surface_elos(state: PlayerFeatureState) -> dict[str, float]:
    if state.elo_by_surface is None:
        return {}
    return dict(state.elo_by_surface)


def _expected_score(player_elo: float, opponent_elo: float) -> float:
    return 1.0 / (1.0 + math.pow(10.0, (opponent_elo - player_elo) / 400.0))


def _window_rate(recent_results: tuple[int, ...], window_size: int) -> tuple[float | None, int]:
    window = recent_results[-window_size:]
    count = len(window)
    if count == 0:
        return None, 0
    return sum(window) / count, count


def _build_form_records(
    *,
    canonical_match_id: str,
    canonical_player_id: str,
    as_of_date: str,
    surface: str,
    pre_results: tuple[int, ...],
    post_results: tuple[int, ...],
) -> list[PlayerStateAuditRecord]:
    records: list[PlayerStateAuditRecord] = []
    for window_size in FORM_WINDOW_SIZES:
        pre_rate, pre_count = _window_rate(pre_results, window_size)
        post_rate, post_count = _window_rate(post_results, window_size)
        records.append(
            PlayerStateAuditRecord(
                canonical_match_id=canonical_match_id,
                canonical_player_id=canonical_player_id,
                as_of_date=as_of_date,
                surface=surface,
                metric_name=f"form_last_{window_size}_win_rate",
                pre_value=pre_rate,
                post_value=post_rate,
                pre_count=pre_count,
                post_count=post_count,
            )
        )
    return records


def get_player_state(
    *,
    canonical_player_id: str,
    player_states: dict[str, PlayerFeatureState],
) -> PlayerFeatureState:
    state = player_states.get(canonical_player_id)
    if state is None:
        return PlayerFeatureState()
    return state


def compute_days_rest(*, last_played_date: str | None, as_of_date: str) -> int | None:
    if last_played_date is None:
        return None
    return (_parse_date(as_of_date) - _parse_date(last_played_date)).days


def build_pre_match_snapshot(
    *,
    state: PlayerFeatureState,
    as_of_date: str,
    surface: str,
) -> PreMatchStateSnapshot:
    form_last_5_win_rate, form_last_5_count = _window_rate(state.recent_results, 5)
    form_last_10_win_rate, form_last_10_count = _window_rate(state.recent_results, 10)
    form_last_20_win_rate, form_last_20_count = _window_rate(state.recent_results, 20)

    return PreMatchStateSnapshot(
        elo_overall=state.elo_overall,
        elo_surface=state.surface_elo(surface),
        rest_days=compute_days_rest(
            last_played_date=state.last_played_date,
            as_of_date=as_of_date,
        ),
        form_last_5_win_rate=form_last_5_win_rate,
        form_last_10_win_rate=form_last_10_win_rate,
        form_last_20_win_rate=form_last_20_win_rate,
        form_last_5_count=form_last_5_count,
        form_last_10_count=form_last_10_count,
        form_last_20_count=form_last_20_count,
    )


def _build_post_match_state(
    *,
    state: PlayerFeatureState,
    surface: str,
    result: int,
    overall_delta: float,
    surface_delta: float,
    as_of_date: str,
) -> PlayerFeatureState:
    updated_surface_elos = _clone_surface_elos(state)
    updated_surface_elos[surface] = state.surface_elo(surface) + surface_delta

    updated_results = (*state.recent_results, result)[-20:]

    return PlayerFeatureState(
        elo_overall=state.elo_overall + overall_delta,
        elo_by_surface=updated_surface_elos,
        last_played_date=as_of_date,
        recent_results=updated_results,
        matches_played_before=state.matches_played_before + 1,
    )


def apply_match_result_batch(
    *,
    matches: list[CanonicalMatch],
    player_states: dict[str, PlayerFeatureState],
) -> tuple[dict[str, PlayerFeatureState], list[PlayerStateAuditRecord]]:
    updated_states = dict(player_states)
    audit_records: list[PlayerStateAuditRecord] = []

    for match in matches:
        winner_id = match.winner_canonical_player_id
        loser_id = match.loser_canonical_player_id
        winner_state = get_player_state(
            canonical_player_id=winner_id,
            player_states=updated_states,
        )
        loser_state = get_player_state(
            canonical_player_id=loser_id,
            player_states=updated_states,
        )

        winner_expected = _expected_score(winner_state.elo_overall, loser_state.elo_overall)
        loser_expected = _expected_score(loser_state.elo_overall, winner_state.elo_overall)
        winner_surface_expected = _expected_score(
            winner_state.surface_elo(match.surface),
            loser_state.surface_elo(match.surface),
        )
        loser_surface_expected = _expected_score(
            loser_state.surface_elo(match.surface),
            winner_state.surface_elo(match.surface),
        )

        winner_post_state = _build_post_match_state(
            state=winner_state,
            surface=match.surface,
            result=1,
            overall_delta=ELO_K_FACTOR * (1.0 - winner_expected),
            surface_delta=ELO_K_FACTOR * (1.0 - winner_surface_expected),
            as_of_date=match.tourney_date,
        )
        loser_post_state = _build_post_match_state(
            state=loser_state,
            surface=match.surface,
            result=0,
            overall_delta=ELO_K_FACTOR * (0.0 - loser_expected),
            surface_delta=ELO_K_FACTOR * (0.0 - loser_surface_expected),
            as_of_date=match.tourney_date,
        )

        updated_states[winner_id] = winner_post_state
        updated_states[loser_id] = loser_post_state

        audit_records.extend(
            [
                PlayerStateAuditRecord(
                    canonical_match_id=match.canonical_match_id,
                    canonical_player_id=winner_id,
                    as_of_date=match.tourney_date,
                    surface=match.surface,
                    metric_name="elo_overall",
                    pre_value=winner_state.elo_overall,
                    post_value=winner_post_state.elo_overall,
                    pre_count=None,
                    post_count=None,
                ),
                PlayerStateAuditRecord(
                    canonical_match_id=match.canonical_match_id,
                    canonical_player_id=winner_id,
                    as_of_date=match.tourney_date,
                    surface=match.surface,
                    metric_name="elo_surface",
                    pre_value=winner_state.surface_elo(match.surface),
                    post_value=winner_post_state.surface_elo(match.surface),
                    pre_count=None,
                    post_count=None,
                ),
                PlayerStateAuditRecord(
                    canonical_match_id=match.canonical_match_id,
                    canonical_player_id=loser_id,
                    as_of_date=match.tourney_date,
                    surface=match.surface,
                    metric_name="elo_overall",
                    pre_value=loser_state.elo_overall,
                    post_value=loser_post_state.elo_overall,
                    pre_count=None,
                    post_count=None,
                ),
                PlayerStateAuditRecord(
                    canonical_match_id=match.canonical_match_id,
                    canonical_player_id=loser_id,
                    as_of_date=match.tourney_date,
                    surface=match.surface,
                    metric_name="elo_surface",
                    pre_value=loser_state.surface_elo(match.surface),
                    post_value=loser_post_state.surface_elo(match.surface),
                    pre_count=None,
                    post_count=None,
                ),
            ]
        )
        audit_records.extend(
            _build_form_records(
                canonical_match_id=match.canonical_match_id,
                canonical_player_id=winner_id,
                as_of_date=match.tourney_date,
                surface=match.surface,
                pre_results=winner_state.recent_results,
                post_results=winner_post_state.recent_results,
            )
        )
        audit_records.extend(
            _build_form_records(
                canonical_match_id=match.canonical_match_id,
                canonical_player_id=loser_id,
                as_of_date=match.tourney_date,
                surface=match.surface,
                pre_results=loser_state.recent_results,
                post_results=loser_post_state.recent_results,
            )
        )

    return updated_states, audit_records
