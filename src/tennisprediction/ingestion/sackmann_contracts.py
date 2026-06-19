from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ATP_ALLOWED_PATTERNS = (
    re.compile(r"^atp_players\.csv$"),
    re.compile(r"^atp_rankings(?:_(?:\d{4}|\d{2}s|current))?\.csv$"),
    re.compile(r"^atp_matches_\d{4}\.csv$"),
    re.compile(r"^atp_matchstats_\d{4}\.csv$"),
)

OUT_OF_SCOPE_TOKENS = ("qual", "chall", "futures", "doubles", "itf", "wta")


@dataclass(frozen=True)
class FileScopeDecision:
    accepted: bool
    reason: str | None = None


def classify_file_scope(relative_path: str | Path) -> FileScopeDecision:
    name = Path(relative_path).name.lower()
    if any(token in name for token in OUT_OF_SCOPE_TOKENS):
        return FileScopeDecision(accepted=False, reason="out_of_scope_file_family")

    if any(pattern.fullmatch(name) for pattern in ATP_ALLOWED_PATTERNS):
        return FileScopeDecision(accepted=True)

    return FileScopeDecision(accepted=False, reason="unknown_file_family")
