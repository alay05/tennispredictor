from __future__ import annotations

import re
import unicodedata

_NON_WORD_PATTERN = re.compile(r"[^\w\s]")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def _ascii_fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return normalized.encode("ascii", "ignore").decode("ascii")


def normalize_market_player_name(value: str) -> str:
    folded = _ascii_fold(value).lower()
    stripped_punctuation = _NON_WORD_PATTERN.sub(" ", folded)
    collapsed_whitespace = _WHITESPACE_PATTERN.sub(" ", stripped_punctuation).strip()
    return collapsed_whitespace
