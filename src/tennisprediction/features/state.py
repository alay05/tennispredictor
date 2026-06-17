from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from tennisprediction.domain.models import CanonicalMatch, CanonicalMatchStat

BASE_ELO = 1500.0
ELO_K_FACTOR = 32.0
FORM_WINDOW_SIZES = (5, 10, 20)
MIN_STATS_SERVE_POINT_EXPOSURE = 50
MIN_HEAD_TO_HEAD_MATCHES = 2


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
class MatchStatAggregateState:
    stats_match_count: int = 0
    service_first_won_total: int = 0
    return_first_won_allowed_total: int = 0
    serve_point_exposure: int = 0
    return_serve_point_exposure: int = 0
    ace_total: int = 0
    ace_data_complete: bool = True


@dataclass(frozen=True)
class HeadToHeadState:
    first_player_id: str
    second_player_id: str
    first_player_wins: int = 0
    second_player_wins: int = 0

    @property
    def match_count(self) -> int:
        return self.first_player_wins + self.second_player_wins


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
class PreMatchStatSnapshot:
    service_first_won_rate: float | None
    return_first_won_allowed_rate: float | None
    ace_rate: float | None
    stats_match_count: int
    serve_point_exposure: int
    stats_missing: bool
    stats_low_sample: bool


@dataclass(frozen=True)
class PreMatchHeadToHeadSnapshot:
    head_to_head_match_count: int
    head_to_head_wins: int
    head_to_head_losses: int
    head_to_head_win_rate: float | None
    head_to_head_missing: bool
    head_to_head_low_sample: bool


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


def _safe_rate(*, numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return numerator / denominator


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


def _build_stat_records(
    *,
    canonical_match_id: str,
    canonical_player_id: str,
    as_of_date: str,
    surface: str,
    pre_state: MatchStatAggregateState,
    post_state: MatchStatAggregateState,
) -> list[PlayerStateAuditRecord]:
    return [
        PlayerStateAuditRecord(
            canonical_match_id=canonical_match_id,
            canonical_player_id=canonical_player_id,
            as_of_date=as_of_date,
            surface=surface,
            metric_name="service_first_won_rate",
            pre_value=_safe_rate(
                numerator=pre_state.service_first_won_total,
                denominator=pre_state.serve_point_exposure,
            ),
            post_value=_safe_rate(
                numerator=post_state.service_first_won_total,
                denominator=post_state.serve_point_exposure,
            ),
            pre_count=pre_state.serve_point_exposure,
            post_count=post_state.serve_point_exposure,
        ),
        PlayerStateAuditRecord(
            canonical_match_id=canonical_match_id,
            canonical_player_id=canonical_player_id,
            as_of_date=as_of_date,
            surface=surface,
            metric_name="return_first_won_allowed_rate",
            pre_value=_safe_rate(
                numerator=pre_state.return_first_won_allowed_total,
                denominator=pre_state.return_serve_point_exposure,
            ),
            post_value=_safe_rate(
                numerator=post_state.return_first_won_allowed_total,
                denominator=post_state.return_serve_point_exposure,
            ),
            pre_count=pre_state.return_serve_point_exposure,
            post_count=post_state.return_serve_point_exposure,
        ),
        PlayerStateAuditRecord(
            canonical_match_id=canonical_match_id,
            canonical_player_id=canonical_player_id,
            as_of_date=as_of_date,
            surface=surface,
            metric_name="ace_rate",
            pre_value=(
                _safe_rate(
                    numerator=pre_state.ace_total,
                    denominator=pre_state.serve_point_exposure,
                )
                if pre_state.ace_data_complete
                else None
            ),
            post_value=(
                _safe_rate(
                    numerator=post_state.ace_total,
                    denominator=post_state.serve_point_exposure,
                )
                if post_state.ace_data_complete
                else None
            ),
            pre_count=pre_state.serve_point_exposure,
            post_count=post_state.serve_point_exposure,
        ),
        PlayerStateAuditRecord(
            canonical_match_id=canonical_match_id,
            canonical_player_id=canonical_player_id,
            as_of_date=as_of_date,
            surface=surface,
            metric_name="stats_match_count",
            pre_value=float(pre_state.stats_match_count),
            post_value=float(post_state.stats_match_count),
            pre_count=None,
            post_count=None,
        ),
    ]


def _build_head_to_head_records(
    *,
    canonical_match_id: str,
    canonical_player_id: str,
    as_of_date: str,
    surface: str,
    pre_snapshot: PreMatchHeadToHeadSnapshot,
    post_snapshot: PreMatchHeadToHeadSnapshot,
) -> list[PlayerStateAuditRecord]:
    return [
        PlayerStateAuditRecord(
            canonical_match_id=canonical_match_id,
            canonical_player_id=canonical_player_id,
            as_of_date=as_of_date,
            surface=surface,
            metric_name="head_to_head_win_rate",
            pre_value=pre_snapshot.head_to_head_win_rate,
            post_value=post_snapshot.head_to_head_win_rate,
            pre_count=pre_snapshot.head_to_head_match_count,
            post_count=post_snapshot.head_to_head_match_count,
        ),
        PlayerStateAuditRecord(
            canonical_match_id=canonical_match_id,
            canonical_player_id=canonical_player_id,
            as_of_date=as_of_date,
            surface=surface,
            metric_name="head_to_head_match_count",
            pre_value=float(pre_snapshot.head_to_head_match_count),
            post_value=float(post_snapshot.head_to_head_match_count),
            pre_count=None,
            post_count=None,
        ),
    ]


def get_player_state(
    *,
    canonical_player_id: str,
    player_states: dict[str, PlayerFeatureState],
) -> PlayerFeatureState:
    state = player_states.get(canonical_player_id)
    if state is None:
        return PlayerFeatureState()
    return state


def get_match_stat_state(
    *,
    canonical_player_id: str,
    match_stat_states: dict[str, MatchStatAggregateState],
) -> MatchStatAggregateState:
    state = match_stat_states.get(canonical_player_id)
    if state is None:
        return MatchStatAggregateState()
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


def build_pre_match_stat_snapshot(*, state: MatchStatAggregateState) -> PreMatchStatSnapshot:
    stats_missing = state.stats_match_count == 0 or state.serve_point_exposure == 0
    stats_low_sample = (
        not stats_missing and state.serve_point_exposure < MIN_STATS_SERVE_POINT_EXPOSURE
    )

    service_first_won_rate: float | None = None
    return_first_won_allowed_rate: float | None = None
    ace_rate: float | None = None

    if not stats_missing and not stats_low_sample:
        service_first_won_rate = (
            state.service_first_won_total / state.serve_point_exposure
        )
        return_first_won_allowed_rate = (
            state.return_first_won_allowed_total / state.return_serve_point_exposure
        )
        if state.ace_data_complete:
            ace_rate = state.ace_total / state.serve_point_exposure

    return PreMatchStatSnapshot(
        service_first_won_rate=service_first_won_rate,
        return_first_won_allowed_rate=return_first_won_allowed_rate,
        ace_rate=ace_rate,
        stats_match_count=state.stats_match_count,
        serve_point_exposure=state.serve_point_exposure,
        stats_missing=stats_missing,
        stats_low_sample=stats_low_sample,
    )


def _canonical_pair(
    player_one_id: str,
    player_two_id: str,
) -> tuple[str, str]:
    if player_one_id <= player_two_id:
        return player_one_id, player_two_id
    return player_two_id, player_one_id


def get_head_to_head_state(
    *,
    canonical_player_id: str,
    opponent_canonical_player_id: str,
    head_to_head_states: dict[tuple[str, str], HeadToHeadState],
) -> HeadToHeadState | None:
    pair = _canonical_pair(canonical_player_id, opponent_canonical_player_id)
    return head_to_head_states.get(pair)


def build_pre_match_head_to_head_snapshot(
    *,
    canonical_player_id: str,
    opponent_canonical_player_id: str,
    state: HeadToHeadState | None,
) -> PreMatchHeadToHeadSnapshot:
    if state is None:
        return PreMatchHeadToHeadSnapshot(
            head_to_head_match_count=0,
            head_to_head_wins=0,
            head_to_head_losses=0,
            head_to_head_win_rate=None,
            head_to_head_missing=True,
            head_to_head_low_sample=False,
        )

    if canonical_player_id == state.first_player_id:
        wins = state.first_player_wins
        losses = state.second_player_wins
    else:
        wins = state.second_player_wins
        losses = state.first_player_wins

    match_count = state.match_count
    head_to_head_missing = match_count == 0
    head_to_head_low_sample = 0 < match_count < MIN_HEAD_TO_HEAD_MATCHES
    win_rate = None
    if match_count >= MIN_HEAD_TO_HEAD_MATCHES:
        win_rate = wins / match_count

    return PreMatchHeadToHeadSnapshot(
        head_to_head_match_count=match_count,
        head_to_head_wins=wins,
        head_to_head_losses=losses,
        head_to_head_win_rate=win_rate,
        head_to_head_missing=head_to_head_missing,
        head_to_head_low_sample=head_to_head_low_sample,
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


def _build_post_match_stat_state(
    *,
    state: MatchStatAggregateState,
    service_first_won: int,
    return_first_won_allowed: int,
    serve_points: int | None,
    return_serve_points: int | None,
    ace_count: int | None,
) -> MatchStatAggregateState:
    if serve_points is None or return_serve_points is None:
        return state

    return MatchStatAggregateState(
        stats_match_count=state.stats_match_count + 1,
        service_first_won_total=state.service_first_won_total + service_first_won,
        return_first_won_allowed_total=(
            state.return_first_won_allowed_total + return_first_won_allowed
        ),
        serve_point_exposure=state.serve_point_exposure + serve_points,
        return_serve_point_exposure=(
            state.return_serve_point_exposure + return_serve_points
        ),
        ace_total=state.ace_total + (ace_count or 0),
        ace_data_complete=state.ace_data_complete and ace_count is not None,
    )


def _build_post_head_to_head_state(
    *,
    winner_id: str,
    loser_id: str,
    prior_state: HeadToHeadState | None,
) -> HeadToHeadState:
    first_player_id, second_player_id = _canonical_pair(winner_id, loser_id)
    if prior_state is None:
        prior_state = HeadToHeadState(
            first_player_id=first_player_id,
            second_player_id=second_player_id,
        )

    if winner_id == prior_state.first_player_id:
        return HeadToHeadState(
            first_player_id=prior_state.first_player_id,
            second_player_id=prior_state.second_player_id,
            first_player_wins=prior_state.first_player_wins + 1,
            second_player_wins=prior_state.second_player_wins,
        )

    return HeadToHeadState(
        first_player_id=prior_state.first_player_id,
        second_player_id=prior_state.second_player_id,
        first_player_wins=prior_state.first_player_wins,
        second_player_wins=prior_state.second_player_wins + 1,
    )


def apply_match_result_batch(
    *,
    matches: list[CanonicalMatch],
    player_states: dict[str, PlayerFeatureState],
    match_stat_states: dict[str, MatchStatAggregateState],
    head_to_head_states: dict[tuple[str, str], HeadToHeadState],
    match_stats_by_row: dict[int, CanonicalMatchStat],
) -> tuple[
    dict[str, PlayerFeatureState],
    dict[str, MatchStatAggregateState],
    dict[tuple[str, str], HeadToHeadState],
    list[PlayerStateAuditRecord],
]:
    updated_player_states = dict(player_states)
    updated_match_stat_states = dict(match_stat_states)
    updated_head_to_head_states = dict(head_to_head_states)
    audit_records: list[PlayerStateAuditRecord] = []

    for match in matches:
        winner_id = match.winner_canonical_player_id
        loser_id = match.loser_canonical_player_id
        winner_state = get_player_state(
            canonical_player_id=winner_id,
            player_states=updated_player_states,
        )
        loser_state = get_player_state(
            canonical_player_id=loser_id,
            player_states=updated_player_states,
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

        updated_player_states[winner_id] = winner_post_state
        updated_player_states[loser_id] = loser_post_state

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

        match_stat = match_stats_by_row.get(match.lineage.source_row_number)
        if match_stat is not None:
            winner_stat_state = get_match_stat_state(
                canonical_player_id=winner_id,
                match_stat_states=updated_match_stat_states,
            )
            loser_stat_state = get_match_stat_state(
                canonical_player_id=loser_id,
                match_stat_states=updated_match_stat_states,
            )

            winner_post_stat_state = _build_post_match_stat_state(
                state=winner_stat_state,
                service_first_won=match_stat.first_won_player1,
                return_first_won_allowed=match_stat.first_won_player2,
                serve_points=match_stat.serve_points_player1,
                return_serve_points=match_stat.serve_points_player2,
                ace_count=match_stat.ace_player1,
            )
            loser_post_stat_state = _build_post_match_stat_state(
                state=loser_stat_state,
                service_first_won=match_stat.first_won_player2,
                return_first_won_allowed=match_stat.first_won_player1,
                serve_points=match_stat.serve_points_player2,
                return_serve_points=match_stat.serve_points_player1,
                ace_count=match_stat.ace_player2,
            )

            updated_match_stat_states[winner_id] = winner_post_stat_state
            updated_match_stat_states[loser_id] = loser_post_stat_state

            audit_records.extend(
                _build_stat_records(
                    canonical_match_id=match.canonical_match_id,
                    canonical_player_id=winner_id,
                    as_of_date=match.tourney_date,
                    surface=match.surface,
                    pre_state=winner_stat_state,
                    post_state=winner_post_stat_state,
                )
            )
            audit_records.extend(
                _build_stat_records(
                    canonical_match_id=match.canonical_match_id,
                    canonical_player_id=loser_id,
                    as_of_date=match.tourney_date,
                    surface=match.surface,
                    pre_state=loser_stat_state,
                    post_state=loser_post_stat_state,
                )
            )

        pair_key = _canonical_pair(winner_id, loser_id)
        prior_head_to_head = updated_head_to_head_states.get(pair_key)
        updated_head_to_head_states[pair_key] = _build_post_head_to_head_state(
            winner_id=winner_id,
            loser_id=loser_id,
            prior_state=prior_head_to_head,
        )

        winner_pre_head_to_head = build_pre_match_head_to_head_snapshot(
            canonical_player_id=winner_id,
            opponent_canonical_player_id=loser_id,
            state=prior_head_to_head,
        )
        loser_pre_head_to_head = build_pre_match_head_to_head_snapshot(
            canonical_player_id=loser_id,
            opponent_canonical_player_id=winner_id,
            state=prior_head_to_head,
        )
        winner_post_head_to_head = build_pre_match_head_to_head_snapshot(
            canonical_player_id=winner_id,
            opponent_canonical_player_id=loser_id,
            state=updated_head_to_head_states[pair_key],
        )
        loser_post_head_to_head = build_pre_match_head_to_head_snapshot(
            canonical_player_id=loser_id,
            opponent_canonical_player_id=winner_id,
            state=updated_head_to_head_states[pair_key],
        )

        audit_records.extend(
            _build_head_to_head_records(
                canonical_match_id=match.canonical_match_id,
                canonical_player_id=winner_id,
                as_of_date=match.tourney_date,
                surface=match.surface,
                pre_snapshot=winner_pre_head_to_head,
                post_snapshot=winner_post_head_to_head,
            )
        )
        audit_records.extend(
            _build_head_to_head_records(
                canonical_match_id=match.canonical_match_id,
                canonical_player_id=loser_id,
                as_of_date=match.tourney_date,
                surface=match.surface,
                pre_snapshot=loser_pre_head_to_head,
                post_snapshot=loser_post_head_to_head,
            )
        )

    return (
        updated_player_states,
        updated_match_stat_states,
        updated_head_to_head_states,
        audit_records,
    )
