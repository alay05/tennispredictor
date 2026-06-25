# Phase 7: Alerts and Operational Hardening - Pattern Map

**Mapped:** 2026-06-24
**Files analyzed:** 11
**Analogs found:** 9 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/tennisprediction/monitoring/reports.py` | service | file-I/O, transform | `src/tennisprediction/monitoring/reports.py` | exact |
| `src/tennisprediction/monitoring/alerts.py` | service | transform, request-response | `src/tennisprediction/monitoring/reports.py` | role-match |
| `src/tennisprediction/cli.py` | controller | request-response | `src/tennisprediction/cli.py` | exact |
| `src/tennisprediction/config.py` | config | file-I/O | `src/tennisprediction/config.py` | exact |
| `src/tennisprediction/logging.py` | utility | event-driven | `src/tennisprediction/logging.py` | exact |
| `pyproject.toml` | config | batch | `pyproject.toml` | exact |
| `.pre-commit-config.yaml` | config | batch | `pyproject.toml` | partial |
| `.github/workflows/ci.yml` | config | batch | `pyproject.toml` | partial |
| `docs/operations.md` | documentation | batch | `docs/data-contracts.md` | role-match |
| `tests/unit/test_live_monitor_reports.py` | test | file-I/O, transform | `tests/unit/test_live_monitor_reports.py` | exact |
| `tests/unit/test_cli_smoke.py` | test | request-response | `tests/unit/test_cli_smoke.py` | exact |

## Pattern Assignments

### `src/tennisprediction/monitoring/reports.py` (service, file-I/O + transform)

**Analog:** `src/tennisprediction/monitoring/reports.py`

**Imports pattern** ([src/tennisprediction/monitoring/reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/monitoring/reports.py:1)):
```python
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from rich.console import Console
from rich.table import Table

from tennisprediction.config import Settings
```

**Canonical artifact write pattern** ([src/tennisprediction/monitoring/reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/monitoring/reports.py:14)):
```python
def write_live_monitor_reports(
    *,
    run_id: str,
    accepted_rows: list[dict[str, object]],
    rejected_rows: list[dict[str, object]],
    settings: Settings,
) -> Path:
    report_dir = settings.reports_dir / "monitoring" / run_id
    report_dir.mkdir(parents=True, exist_ok=False)

    ranked_rows = _rank_accepted_rows(accepted_rows)
    _write_json(report_dir / "summary.json", {...})
    _write_parquet(report_dir / "accepted_opportunities.parquet", ranked_rows)
    _write_parquet(report_dir / "rejected_opportunities.parquet", rejected_rows)
    _write_csv(report_dir / "ranked_opportunities.csv", ranked_rows)
    return report_dir
```

**Rich console pattern** ([src/tennisprediction/monitoring/reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/monitoring/reports.py:40)):
```python
def render_live_monitor_console(
    *,
    accepted_rows: list[dict[str, object]],
    rejected_rows: list[dict[str, object]],
    console: Console | None = None,
) -> None:
    active_console = console or Console()
    table = Table(title="Accepted Opportunities")
    table.add_column("Ticker")
    table.add_column("Match")
    ...
    for row in _rank_accepted_rows(accepted_rows):
        table.add_row(...)
    active_console.print(table)
    active_console.print({...})
```

**Ranking + summary helpers** ([src/tennisprediction/monitoring/reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/monitoring/reports.py:78)):
```python
def _rank_accepted_rows(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    return sorted(
        rows,
        key=lambda row: (
            -_float_or_default(row.get("expected_value_per_contract"), float("-inf")),
            -_float_or_default(row.get("edge"), float("-inf")),
            -_float_or_default(row.get("available_liquidity_dollars"), float("-inf")),
            -_float_or_default(row.get("confidence"), float("-inf")),
            _float_or_default(row.get("freshness_age_seconds"), float("inf")),
        ),
    )
```

### `src/tennisprediction/monitoring/alerts.py` (service, transform + request-response)

**Analog:** `src/tennisprediction/monitoring/reports.py`

**Why this analog:** Phase 07’s new operator-facing alert assembly should stay downstream of canonical accepted/rejected rows, not fork scan logic. The existing report module already separates row ranking, artifact persistence, and Rich rendering.

**Reuse the “rows first, views second” shape** ([src/tennisprediction/monitoring/reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/monitoring/reports.py:21)):
```python
report_dir = settings.reports_dir / "monitoring" / run_id
report_dir.mkdir(parents=True, exist_ok=False)

ranked_rows = _rank_accepted_rows(accepted_rows)
_write_json(report_dir / "summary.json", {...})
_write_parquet(report_dir / "accepted_opportunities.parquet", ranked_rows)
```

**Reuse the operator-table seam** ([src/tennisprediction/monitoring/reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/monitoring/reports.py:46)):
```python
active_console = console or Console()
table = Table(title="Accepted Opportunities")
table.add_column("Ticker")
table.add_column("Match")
table.add_column("EV")
...
active_console.print(table)
active_console.print({...})
```

**Backfill richer persisted payloads from the backtesting writer pattern** ([src/tennisprediction/backtesting/reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/backtesting/reports.py:22)):
```python
def write_backtest_reports(..., settings: Settings) -> Path:
    report_dir = settings.reports_dir / "backtesting" / run_id
    report_dir.mkdir(parents=True, exist_ok=False)
    _write_json(report_dir / "summary.json", {...})
    _write_json(report_dir / "uncertainty.json", asdict(uncertainty))
    _write_json(report_dir / "provenance.json", build_provenance_payload(batch, claim_guard))
```

### `src/tennisprediction/cli.py` (controller, request-response)

**Analog:** `src/tennisprediction/cli.py`

**Imports + app bootstrap pattern** ([src/tennisprediction/cli.py](/Users/andrewlay/tennisprediction/src/tennisprediction/cli.py:1)):
```python
from pathlib import Path
from typing import Annotated

import typer

from tennisprediction.config import get_settings
from tennisprediction.logging import configure_logging

app = typer.Typer(help="ATP-only tennis prediction project CLI.")
```

**Global callback pattern** ([src/tennisprediction/cli.py](/Users/andrewlay/tennisprediction/src/tennisprediction/cli.py:25)):
```python
@app.callback()
def main() -> None:
    """Initialize config and logging for every CLI invocation."""
    settings = get_settings()
    configure_logging(settings)
```

**Command option style** ([src/tennisprediction/cli.py](/Users/andrewlay/tennisprediction/src/tennisprediction/cli.py:42)):
```python
@app.command("collect-kalshi-snapshots")
def collect_kalshi_snapshots(
    access_key: Annotated[str, typer.Option(help="Kalshi access key.")],
    private_key: Annotated[
        Path,
        typer.Option(exists=True, dir_okay=False, help="Path to the Kalshi RSA private key."),
    ],
    database_path: Annotated[Path | None, typer.Option(help="Optional DuckDB path...")] = None,
) -> None:
```

**Compose service calls, then echo artifact path** ([src/tennisprediction/cli.py](/Users/andrewlay/tennisprediction/src/tennisprediction/cli.py:156)):
```python
result = run_kalshi_ev_scan(...)
report_dir = write_live_monitor_reports(
    run_id=result.run_id,
    accepted_rows=result.accepted_records,
    rejected_rows=result.rejected_records,
    settings=settings,
)
render_live_monitor_console(
    accepted_rows=result.accepted_records,
    rejected_rows=result.rejected_records,
)
typer.echo(str(report_dir))
```

### `src/tennisprediction/config.py` (config, file-I/O)

**Analog:** `src/tennisprediction/config.py`

**Settings model pattern** ([src/tennisprediction/config.py](/Users/andrewlay/tennisprediction/src/tennisprediction/config.py:14)):
```python
class Settings(BaseSettings):
    """Typed runtime configuration constrained to repository-local paths."""

    environment: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    data_dir: Path = Path("data")
    models_dir: Path = Path("models")
    reports_dir: Path = Path("reports")
    duckdb_path: Path = Path("data/duckdb/tennisprediction.duckdb")
```

**Pydantic settings config pattern** ([src/tennisprediction/config.py](/Users/andrewlay/tennisprediction/src/tennisprediction/config.py:24)):
```python
model_config = SettingsConfigDict(
    env_prefix="TENNISPREDICTION_",
    extra="ignore",
    frozen=True,
)
```

**Repo-local path guard pattern** ([src/tennisprediction/config.py](/Users/andrewlay/tennisprediction/src/tennisprediction/config.py:34)):
```python
@staticmethod
def _resolve_repo_path(value: Path) -> Path:
    candidate = value if value.is_absolute() else REPO_ROOT / value
    resolved = candidate.resolve(strict=False)

    if resolved != REPO_ROOT and REPO_ROOT not in resolved.parents:
        msg = f"{value} must stay within the repository"
        raise ValueError(msg)

    return resolved
```

**Cache the singleton settings object** ([src/tennisprediction/config.py](/Users/andrewlay/tennisprediction/src/tennisprediction/config.py:54)):
```python
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

### `src/tennisprediction/logging.py` (utility, event-driven)

**Analog:** `src/tennisprediction/logging.py`

**Current bootstrap seam to extend** ([src/tennisprediction/logging.py](/Users/andrewlay/tennisprediction/src/tennisprediction/logging.py:7)):
```python
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
```

**Apply-to-Phase-07 note:** keep `configure_logging(settings)` as the single bootstrap entrypoint. Add handlers/filters/adapters behind this function rather than wiring logging directly in CLI commands.

### `pyproject.toml` (config, batch)

**Analog:** `pyproject.toml`

**Dependency-group pattern** ([pyproject.toml](/Users/andrewlay/tennisprediction/pyproject.toml:22)):
```toml
[dependency-groups]
dev = [
  "mypy>=1.18,<1.19",
  "pre-commit>=4.3,<4.4",
  "pytest>=9.1,<9.2",
  "ruff>=0.15,<0.16",
]
```

**Packaged CLI script seam** ([pyproject.toml](/Users/andrewlay/tennisprediction/pyproject.toml:36)):
```toml
[project.scripts]
tennisprediction = "tennisprediction.cli:main"
```

**Quality-tool config pattern** ([pyproject.toml](/Users/andrewlay/tennisprediction/pyproject.toml:42)):
```toml
[tool.pytest.ini_options]
addopts = "-ra"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
python_version = "3.12"
strict = true
mypy_path = ["src"]
packages = ["tennisprediction"]
```

### `.pre-commit-config.yaml` (config, batch)

**Analog:** `pyproject.toml`

**Why this analog:** There is no existing hook config. Mirror the repo’s current gate sources from `pyproject.toml` rather than inventing new commands.

**Gate source of truth to mirror** ([pyproject.toml](/Users/andrewlay/tennisprediction/pyproject.toml:22)):
```toml
dev = [
  "mypy>=1.18,<1.19",
  "pre-commit>=4.3,<4.4",
  "pytest>=9.1,<9.2",
  "ruff>=0.15,<0.16",
]
```

**Tool settings the hooks should call** ([pyproject.toml](/Users/andrewlay/tennisprediction/pyproject.toml:42)):
```toml
[tool.pytest.ini_options]
addopts = "-ra"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.mypy]
strict = true
```

### `.github/workflows/ci.yml` (config, batch)

**Analog:** `pyproject.toml`

**Why this analog:** No workflow exists yet. CI should be a thin runner around the same package-manager and tool config already declared in `pyproject.toml`.

**Reuse the package + script contract** ([pyproject.toml](/Users/andrewlay/tennisprediction/pyproject.toml:5)):
```toml
[project]
requires-python = "==3.12.*"

[dependency-groups]
dev = [...]

[project.scripts]
tennisprediction = "tennisprediction.cli:main"
```

### `docs/operations.md` (documentation, batch)

**Analog:** `docs/data-contracts.md`

**Heading + boundary-writing pattern** ([docs/data-contracts.md](/Users/andrewlay/tennisprediction/docs/data-contracts.md:1)):
```markdown
# Phase 1 Data Contracts

Phase 1 defines the ATP-only canonical data boundary for the project. It covers ...
It does not include ...
```

**Section structure pattern** ([docs/data-contracts.md](/Users/andrewlay/tennisprediction/docs/data-contracts.md:5)):
```markdown
## Scope Boundary

- Accepted ...
- Non-ATP ...
- Out-of-scope ...
```

**Apply-to-Phase-07 note:** keep the same direct structure for operator docs:
setup, commands, outputs, limitations, and read-only scope boundaries as top-level sections with flat bullets.

### `tests/unit/test_live_monitor_reports.py` (test, file-I/O + transform)

**Analog:** `tests/unit/test_live_monitor_reports.py`

**Test setup pattern** ([tests/unit/test_live_monitor_reports.py](/Users/andrewlay/tennisprediction/tests/unit/test_live_monitor_reports.py:14)):
```python
def test_write_live_monitor_reports_ranks_rows_and_persists_accepted_rejected_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
    settings = Settings(
        data_dir=Path("data"),
        models_dir=Path("models"),
        reports_dir=Path("reports"),
        duckdb_path=Path("data/testing.duckdb"),
    )
```

**Artifact assertions pattern** ([tests/unit/test_live_monitor_reports.py](/Users/andrewlay/tennisprediction/tests/unit/test_live_monitor_reports.py:85)):
```python
assert report_dir == settings.reports_dir / "monitoring" / "scan-001"
assert (report_dir / "summary.json").is_file()
assert (report_dir / "accepted_opportunities.parquet").is_file()
assert (report_dir / "rejected_opportunities.parquet").is_file()
assert (report_dir / "ranked_opportunities.csv").is_file()
```

**Persisted-content verification pattern** ([tests/unit/test_live_monitor_reports.py](/Users/andrewlay/tennisprediction/tests/unit/test_live_monitor_reports.py:91)):
```python
ranked = pd.read_csv(report_dir / "ranked_opportunities.csv")
assert ranked["canonical_match_id"].tolist() == ["match-b", "match-a", "match-c"]
...
summary = json.loads((report_dir / "summary.json").read_text(encoding="utf-8"))
assert summary["accepted_count"] == 3
assert summary["rejection_reason_counts"] == {...}
```

### `tests/unit/test_cli_smoke.py` (test, request-response)

**Analog:** `tests/unit/test_cli_smoke.py`

**CLI runner + smoke pattern** ([tests/unit/test_cli_smoke.py](/Users/andrewlay/tennisprediction/tests/unit/test_cli_smoke.py:7)):
```python
from typer.testing import CliRunner

from tennisprediction.cli import app

runner = CliRunner()
```

**Settings-path validation test pattern** ([tests/unit/test_cli_smoke.py](/Users/andrewlay/tennisprediction/tests/unit/test_cli_smoke.py:14)):
```python
def test_settings_use_repo_local_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("TENNISPREDICTION_DATA_DIR", raising=False)
    ...
    settings = get_settings()
    assert settings.data_dir == settings.repo_root / "data"
```

**Logging seam smoke test** ([tests/unit/test_cli_smoke.py](/Users/andrewlay/tennisprediction/tests/unit/test_cli_smoke.py:41)):
```python
def test_configure_logging_returns_project_logger(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TENNISPREDICTION_LOG_LEVEL", "DEBUG")
    ...
    logger = configure_logging(settings)

    assert logger.name == "tennisprediction"
    assert logger.level == logging.DEBUG
```

**Typer invocation test pattern** ([tests/unit/test_cli_smoke.py](/Users/andrewlay/tennisprediction/tests/unit/test_cli_smoke.py:55)):
```python
def test_cli_version_bootstraps_successfully() -> None:
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.stdout
```

## Shared Patterns

### CLI orchestration
**Source:** [src/tennisprediction/cli.py](/Users/andrewlay/tennisprediction/src/tennisprediction/cli.py:25)
**Apply to:** New Phase 07 one-shot commands
```python
@app.callback()
def main() -> None:
    settings = get_settings()
    configure_logging(settings)
```

Keep all commands under the existing single `typer.Typer()` app, initialize settings/logging once in the callback, and have commands call pure module functions and `typer.echo(...)` final artifact locations.

### Canonical artifact persistence
**Source:** [src/tennisprediction/monitoring/reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/monitoring/reports.py:21)
**Apply to:** `monitoring/reports.py`, `monitoring/alerts.py`, report-related tests
```python
report_dir = settings.reports_dir / "monitoring" / run_id
report_dir.mkdir(parents=True, exist_ok=False)

ranked_rows = _rank_accepted_rows(accepted_rows)
_write_json(report_dir / "summary.json", {...})
_write_parquet(report_dir / "accepted_opportunities.parquet", ranked_rows)
_write_parquet(report_dir / "rejected_opportunities.parquet", rejected_rows)
_write_csv(report_dir / "ranked_opportunities.csv", ranked_rows)
```

The human-facing report should derive from the same canonical rows written to disk.

### Settings and path safety
**Source:** [src/tennisprediction/config.py](/Users/andrewlay/tennisprediction/src/tennisprediction/config.py:24)
**Apply to:** Any new threshold/report/path settings
```python
model_config = SettingsConfigDict(
    env_prefix="TENNISPREDICTION_",
    extra="ignore",
    frozen=True,
)
...
if resolved != REPO_ROOT and REPO_ROOT not in resolved.parents:
    msg = f"{value} must stay within the repository"
    raise ValueError(msg)
```

Add new settings to the same immutable `Settings` object and subject new path-like fields to the same repo-local validation.

### Logging bootstrap seam
**Source:** [src/tennisprediction/logging.py](/Users/andrewlay/tennisprediction/src/tennisprediction/logging.py:10)
**Apply to:** Audit logging across CLI and reporting flows
```python
def configure_logging(settings: Settings | None = None) -> logging.Logger:
    resolved_settings = settings or get_settings()
    level = getattr(logging, resolved_settings.log_level)
    logging.basicConfig(level=level, format=LOG_FORMAT, force=True)
```

Extend this function with handlers/formatters/context; do not configure logging ad hoc inside individual commands.

### Test style
**Source:** [tests/unit/test_live_monitor_reports.py](/Users/andrewlay/tennisprediction/tests/unit/test_live_monitor_reports.py:78), [tests/unit/test_cli_smoke.py](/Users/andrewlay/tennisprediction/tests/unit/test_cli_smoke.py:55)
**Apply to:** New Phase 07 tests
```python
report_dir = write_live_monitor_reports(...)
assert (report_dir / "summary.json").is_file()

result = runner.invoke(app, ["version"])
assert result.exit_code == 0
```

Favor small, deterministic unit tests that assert persisted artifacts, stable summary payloads, and Typer command behavior through `CliRunner`.

## No Analog Found

Files with no close existing match in the codebase:

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `.pre-commit-config.yaml` | config | batch | No hook-runner config exists yet; derive commands from `pyproject.toml` tool config. |
| `.github/workflows/ci.yml` | config | batch | No GitHub Actions workflow exists yet; derive gate steps from `pyproject.toml` and documented `uv run` commands. |

## Metadata

**Analog search scope:** `src/tennisprediction/`, `tests/unit/`, `docs/`, `pyproject.toml`
**Files scanned:** 11 primary files plus Phase 07 context/research artifacts
**Pattern extraction date:** 2026-06-24
