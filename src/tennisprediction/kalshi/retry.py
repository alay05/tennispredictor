from __future__ import annotations

import time
from collections.abc import Callable

from tennisprediction.kalshi.client import KalshiRequestError

__all__ = ["retry_kalshi_read_call"]


def retry_kalshi_read_call[T](
    call: Callable[[], T],
    *,
    max_attempts: int = 4,
    initial_backoff_seconds: float = 0.25,
    max_backoff_seconds: float = 2.0,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> T:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1")
    if initial_backoff_seconds < 0:
        raise ValueError("initial_backoff_seconds must be non-negative")
    if max_backoff_seconds < initial_backoff_seconds:
        raise ValueError("max_backoff_seconds must be >= initial_backoff_seconds")

    attempt = 1
    while True:
        try:
            return call()
        except KalshiRequestError as exc:
            if exc.status_code != 429 or attempt >= max_attempts:
                raise

            delay_seconds = min(
                max_backoff_seconds,
                initial_backoff_seconds * (2 ** (attempt - 1)),
            )
            sleep_fn(delay_seconds)
            attempt += 1
