from __future__ import annotations

from itertools import groupby

from tennisprediction.domain.models import CanonicalMatch

ROUND_PRECEDENCE: dict[str, int] = {
    "RR": 0,
    "BR": 1,
    "R128": 2,
    "R64": 3,
    "R32": 4,
    "R16": 5,
    "QF": 6,
    "SF": 7,
    "F": 8,
    "ER": 9,
}


def _sort_key(match: CanonicalMatch) -> tuple[str, int, str, int]:
    round_name = match.round_name.strip()
    if round_name not in ROUND_PRECEDENCE:
        msg = f"unknown round token: {round_name}"
        raise ValueError(msg)
    return (
        match.tourney_date,
        ROUND_PRECEDENCE[round_name],
        match.lineage.source_file_path,
        match.lineage.source_row_number,
    )


def build_match_cohorts(matches: list[CanonicalMatch]) -> list[list[CanonicalMatch]]:
    ordered_matches = sorted(matches, key=_sort_key)
    cohorts: list[list[CanonicalMatch]] = []
    for _, grouped_matches in groupby(
        ordered_matches,
        key=lambda match: (match.tourney_date, match.round_name.strip()),
    ):
        cohorts.append(list(grouped_matches))
    return cohorts
