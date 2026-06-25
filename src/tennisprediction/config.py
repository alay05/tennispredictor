from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_PATH_FIELDS = ("data_dir", "models_dir", "reports_dir", "duckdb_path")
AlertChannel = Literal["terminal", "file"]


class Settings(BaseSettings):
    """Typed runtime configuration constrained to repository-local paths."""

    environment: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    data_dir: Path = Path("data")
    models_dir: Path = Path("models")
    reports_dir: Path = Path("reports")
    duckdb_path: Path = Path("data/duckdb/tennisprediction.duckdb")
    alert_channels: tuple[AlertChannel, ...] = ("terminal", "file")
    default_feature_version: str = "02-04"
    default_model_family: Literal["logistic_regression", "random_forest", "xgboost"] = (
        "logistic_regression"
    )
    default_calibration_method: Literal["sigmoid", "isotonic"] = "sigmoid"
    default_monitoring_run_id: str = "live-monitor"
    default_monitoring_report_run_id: str = "live-monitor"
    default_min_edge: float = 0.05
    default_min_confidence: float = 0.35
    default_min_liquidity: float = 5.0

    model_config = SettingsConfigDict(
        env_prefix="TENNISPREDICTION_",
        extra="ignore",
        frozen=True,
    )

    @property
    def repo_root(self) -> Path:
        return REPO_ROOT

    @staticmethod
    def _resolve_repo_path(value: Path) -> Path:
        candidate = value if value.is_absolute() else REPO_ROOT / value
        resolved = candidate.resolve(strict=False)

        if resolved != REPO_ROOT and REPO_ROOT not in resolved.parents:
            msg = f"{value} must stay within the repository"
            raise ValueError(msg)

        return resolved

    @field_validator("alert_channels", mode="before")
    @classmethod
    def parse_alert_channels(cls, value: object) -> object:
        if isinstance(value, str):
            return tuple(channel.strip() for channel in value.split(",") if channel.strip())
        return value

    @model_validator(mode="after")
    def ensure_repo_local_paths(self) -> Settings:
        for field_name in REPO_PATH_FIELDS:
            resolved_path = self._resolve_repo_path(getattr(self, field_name))
            object.__setattr__(self, field_name, resolved_path)

        invalid_channels = [
            channel for channel in self.alert_channels if channel not in {"terminal", "file"}
        ]
        if invalid_channels:
            invalid_display = ", ".join(invalid_channels)
            msg = f"alert_channels must stay within terminal/file, got: {invalid_display}"
            raise ValueError(msg)
        if not self.alert_channels:
            msg = "alert_channels must include at least one terminal/file destination"
            raise ValueError(msg)

        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
