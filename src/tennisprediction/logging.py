from __future__ import annotations

import logging

from tennisprediction.config import Settings, get_settings

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def configure_logging(settings: Settings | None = None) -> logging.Logger:
    resolved_settings = settings or get_settings()
    level = getattr(logging, resolved_settings.log_level)

    logging.basicConfig(
        level=level,
        format=LOG_FORMAT,
        force=True,
    )

    logger = logging.getLogger("tennisprediction")
    logger.setLevel(level)
    return logger
