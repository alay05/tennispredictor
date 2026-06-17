from __future__ import annotations

import logging
from pathlib import Path

import pytest


def test_settings_use_repo_local_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TENNISPREDICTION_DATA_DIR", raising=False)
    monkeypatch.delenv("TENNISPREDICTION_LOG_LEVEL", raising=False)

    from tennisprediction.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.repo_root == Path(__file__).resolve().parents[2]
    assert settings.data_dir == settings.repo_root / "data"
    assert settings.models_dir == settings.repo_root / "models"
    assert settings.reports_dir == settings.repo_root / "reports"
    assert settings.log_level == "INFO"


def test_settings_reject_paths_outside_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TENNISPREDICTION_DATA_DIR", "/tmp/tennis-data")

    from tennisprediction.config import get_settings

    get_settings.cache_clear()

    with pytest.raises(ValueError, match="must stay within the repository"):
        get_settings()


def test_configure_logging_returns_project_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TENNISPREDICTION_LOG_LEVEL", "DEBUG")

    from tennisprediction.config import get_settings
    from tennisprediction.logging import configure_logging

    get_settings.cache_clear()
    settings = get_settings()
    logger = configure_logging(settings)

    assert logger.name == "tennisprediction"
    assert logger.level == logging.DEBUG
