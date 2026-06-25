from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from tennisprediction import operations
from tennisprediction.cli import app

runner = CliRunner()
VALID_SOURCE_COMMIT_SHA = "0123456789abcdef0123456789abcdef01234567"


def test_cli_help_exposes_one_shot_commands_and_omits_watch_mode_flags() -> None:
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    for command_name in (
        "ingest-snapshot",
        "build-features",
        "train-artifact-bundle",
        "evaluate-artifact",
        "run-backtest",
        "collect-kalshi-snapshots",
        "scan-kalshi-ev",
        "review-monitoring-report",
    ):
        assert command_name in result.stdout

    assert "--watch" not in result.stdout
    assert "--poll-interval" not in result.stdout
    assert "--daemon" not in result.stdout


def test_cli_rejects_watch_mode_flags() -> None:
    result = runner.invoke(
        app,
        [
            "scan-kalshi-ev",
            "--artifact-dir",
            ".",
            "--expected-feature-version",
            "feature-v1",
            "--expected-split-manifest-id",
            "split-001",
            "--watch",
        ],
    )

    assert result.exit_code != 0
    assert "No such option: --watch" in result.output


@pytest.mark.parametrize(
    ("command_name", "helper_name"),
    (
        ("ingest-snapshot", "ingest_snapshot"),
        ("build-features", "build_features"),
        ("train-artifact-bundle", "train_artifact_bundle"),
        ("evaluate-artifact", "evaluate_artifact"),
        ("run-backtest", "run_backtest"),
        ("collect-kalshi-snapshots", "collect_kalshi_snapshots"),
        ("scan-kalshi-ev", "scan_kalshi_ev"),
        ("review-monitoring-report", "report_monitoring_run"),
    ),
)
def test_commands_delegate_to_operations_helpers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    command_name: str,
    helper_name: str,
) -> None:
    calls: list[dict[str, Any]] = []
    private_key = tmp_path / "kalshi.pem"
    private_key.write_text("fixture private key", encoding="utf-8")
    artifact_dir = tmp_path / "artifact-bundle"
    artifact_dir.mkdir()
    output_path = tmp_path / f"{command_name}.out"
    output_path.write_text("ok", encoding="utf-8")

    def fake_helper(**kwargs: Any) -> Path:
        calls.append(kwargs)
        return output_path

    monkeypatch.setattr(operations, helper_name, fake_helper)

    command_args = {
        "ingest-snapshot": [
            "ingest-snapshot",
            "--source-commit-sha",
            VALID_SOURCE_COMMIT_SHA,
        ],
        "build-features": [
            "build-features",
            "--feature-version",
            "feature-v2",
        ],
        "train-artifact-bundle": [
            "train-artifact-bundle",
            "--run-id",
            "train-001",
            "--feature-version",
            "feature-v2",
            "--train-end-date",
            "2024-06-01",
            "--validation-end-date",
            "2024-09-01",
            "--test-end-date",
            "2024-12-01",
        ],
        "evaluate-artifact": [
            "evaluate-artifact",
            "--artifact-dir",
            str(artifact_dir),
            "--expected-feature-version",
            "feature-v2",
            "--expected-split-manifest-id",
            "split-001",
        ],
        "run-backtest": [
            "run-backtest",
            "--artifact-dir",
            str(artifact_dir),
            "--expected-feature-version",
            "feature-v2",
            "--expected-split-manifest-id",
            "split-001",
            "--run-id",
            "backtest-001",
        ],
        "collect-kalshi-snapshots": [
            "collect-kalshi-snapshots",
            "--access-key",
            "test-access-key",
            "--private-key",
            str(private_key),
        ],
        "scan-kalshi-ev": [
            "scan-kalshi-ev",
            "--artifact-dir",
            str(artifact_dir),
            "--expected-feature-version",
            "feature-v2",
            "--expected-split-manifest-id",
            "split-001",
        ],
        "review-monitoring-report": [
            "review-monitoring-report",
            "--run-id",
            "live-monitor",
        ],
    }

    result = runner.invoke(app, command_args[command_name])

    assert result.exit_code == 0
    assert result.stdout.strip() == str(output_path)
    assert len(calls) == 1
