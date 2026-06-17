from __future__ import annotations

import logging
from pathlib import Path

import pytest

from tennisprediction.config import Settings, get_settings
from tennisprediction.logging import configure_logging


def test_settings_stay_within_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = Path(__file__).resolve().parents[2]

    get_settings.cache_clear()
    monkeypatch.delenv("TENNISPREDICTION_REPO_ROOT", raising=False)
    monkeypatch.setenv("TENNISPREDICTION_DATA_DIR", "runtime-data")
    monkeypatch.setenv("TENNISPREDICTION_DUCKDB_PATH", "runtime-data/duckdb/app.duckdb")

    settings = get_settings()

    assert isinstance(settings, Settings)
    assert settings.repo_root == repo_root
    assert settings.data_dir == repo_root / "runtime-data"
    assert settings.data_dir.is_relative_to(repo_root)
    assert settings.duckdb_path == repo_root / "runtime-data/duckdb/app.duckdb"
    assert settings.duckdb_path.is_relative_to(repo_root)


def test_configure_logging_returns_project_logger() -> None:
    logger = configure_logging("DEBUG")

    assert logger.name == "tennisprediction"
    assert logger.level == logging.DEBUG
