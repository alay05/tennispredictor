from __future__ import annotations

from importlib import import_module
import logging
from pathlib import Path
import tomllib

import pytest
from typer.testing import CliRunner

from tennisprediction.cli import app

runner = CliRunner()


def _load_packaged_entrypoint() -> object:
    pyproject = Path(__file__).resolve().parents[2] / "pyproject.toml"
    package_config = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    script_target = package_config["project"]["scripts"]["tennisprediction"]
    module_name, attribute_name = script_target.split(":", maxsplit=1)
    return getattr(import_module(module_name), attribute_name)


def test_settings_use_repo_local_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TENNISPREDICTION_DATA_DIR", raising=False)
    monkeypatch.delenv("TENNISPREDICTION_LOG_LEVEL", raising=False)
    monkeypatch.delenv("TENNISPREDICTION_ALERT_CHANNELS", raising=False)

    from tennisprediction.config import get_settings

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.repo_root == Path(__file__).resolve().parents[2]
    assert settings.data_dir == settings.repo_root / "data"
    assert settings.models_dir == settings.repo_root / "models"
    assert settings.reports_dir == settings.repo_root / "reports"
    assert settings.log_level == "INFO"
    assert settings.alert_channels == ("terminal", "file")
    assert settings.default_feature_version == "02-04"
    assert settings.default_model_family == "logistic_regression"
    assert settings.default_calibration_method == "sigmoid"
    assert settings.default_monitoring_run_id == "live-monitor"
    assert settings.default_monitoring_report_run_id == "live-monitor"
    assert settings.default_min_edge == pytest.approx(0.05)
    assert settings.default_min_confidence == pytest.approx(0.35)
    assert settings.default_min_liquidity == pytest.approx(5.0)


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


def test_packaged_entrypoint_bootstraps_typer_help() -> None:
    result = runner.invoke(_load_packaged_entrypoint(), ["--help"])

    assert result.exit_code == 0
    assert "ingest-snapshot" in result.stdout
    assert "build-features" in result.stdout
    assert "train-artifact-bundle" in result.stdout
    assert "evaluate-artifact" in result.stdout
    assert "run-backtest" in result.stdout
    assert "collect-kalshi-snapshots" in result.stdout
    assert "scan-kalshi-ev" in result.stdout
    assert "review-monitoring-report" in result.stdout


def test_cli_version_bootstraps_successfully() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.stdout
