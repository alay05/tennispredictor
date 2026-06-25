# Phase 7: Alerts and Operational Hardening - Research

**Researched:** 2026-06-24
**Domain:** Python CLI operations, terminal/file reporting, audit logging, and repo quality gates for the ATP-to-Kalshi workflow. [VERIFIED: codebase grep]
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** v1 alert delivery remains terminal/file-only. Phase 7 must not add email, SMS, Slack, push, webhook, or other external notification channels.
- **D-02:** The operator-facing alert/report layer should build on the existing persisted monitoring outputs from Phase 06 rather than inventing a parallel storage path.
- **D-03:** The primary operator surface should be a polished human-facing report on top of the existing Phase 06 machine-readable artifacts: easy to scan, focused on actionable accepted opportunities, and explicit about rejected/excluded counts and health warnings.
- **D-04:** Exact report layout, wording, and Rich presentation details are delegated to the agent, provided the output stays concise, operator-friendly, and evidence-forward.
- **D-05:** Recommendation language should stay read-only and advisory. The surface may rank, label, and summarize opportunities, but it must not imply or trigger automated execution.
- **D-06:** Phase 7 should expose one-shot operator commands only. Continuous polling, daemonized scanning, schedulers, and long-running workflows are deferred to later work.
- **D-07:** Operator-tunable settings for this phase should at minimum cover thresholds, artifact/report selection, and storage paths. Polling/continuous-run controls are out of scope for now.
- **D-08:** Phase 7 should harden the workflow with strong local quality gates and repository-level CI expectations, not just ad hoc commands.
- **D-09:** Documentation should be good enough for a developer/operator to set up the project, run the main CLI flows, understand the outputs, and understand the scope boundaries and trust limitations of the signals.

### the agent's Discretion
- Choose the exact Rich report composition, CLI subcommand split, and documentation file structure as long as they preserve the read-only, terminal/file-first v1 boundary.
- Choose the exact quality-gate packaging (for example local commands, helper targets, pre-commit wiring, CI workflow shape) as long as tests, linting, formatting, and typing are clearly runnable and documented.

### Deferred Ideas (OUT OF SCOPE)
- External notification channels (email, Slack, SMS, webhooks, push) are deferred beyond v1.
- Continuous polling, schedulers, and long-running scan services are deferred to later phases.
</user_constraints>

## Project Constraints (from AGENTS.md)

- Keep the system ATP-only; do not widen Phase 07 reporting, commands, or docs toward WTA or other tours. [VERIFIED: codebase grep]
- Keep Kalshi as the only live market integration and keep the v1 surface read-only; no trade execution language or automation belongs in this phase. [VERIFIED: codebase grep]
- Preserve Jeff Sackmann `tennis_atp` as the primary historical source and keep chronology/calibration/backtesting caveats visible in operator docs. [VERIFIED: codebase grep]
- Engineering quality is a hard requirement: code must stay modular, typed, logged, configurable, reproducible, and covered by focused unit tests for critical logic. [VERIFIED: codebase grep]
- Follow the repo’s GSD workflow rule for future implementation work; direct repo edits outside a GSD workflow are disallowed unless the user explicitly bypasses that rule. [VERIFIED: codebase grep]

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OPS-01 | Terminal and persisted opportunity reports include match, ticker, model probability, market probability, edge, EV, liquidity, mapping confidence, and recommendation. | Extend `src/tennisprediction/monitoring/reports.py` from Phase 06 instead of creating a parallel reporting path; use Rich tables plus persisted machine-readable artifacts from the same ranked rows. [VERIFIED: codebase grep] [CITED: https://rich.readthedocs.io/en/stable/console.html] |
| OPS-02 | Configurable thresholds, model artifact selection, report selection, storage paths, and terminal/file alert channel settings for one-shot runs. | Locked decisions D-06 and D-07 resolve the stale polling language in favor of a one-shot settings surface; use `pydantic-settings` in the existing `Settings` seam instead of manual env parsing. [VERIFIED: codebase grep] [CITED: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/] |
| OPS-03 | Audit logging across ingestion, features, training, backtesting, polling, mapping, EV filtering, and alert decisions. | Replace the current bootstrap-only logging seam with contextual file/console handlers and run-level metadata using stdlib logging adapters/filters. [VERIFIED: codebase grep] [CITED: https://docs.python.org/3/howto/logging-cookbook.html] [CITED: https://docs.python.org/3/library/logging.handlers.html] |
| OPS-04 | CLI commands for ingestion, feature build, training, evaluation, backtesting, Kalshi snapshot collection, live scan, and opportunity reporting. | Keep one Typer app and add subcommands/groups under the existing callback bootstrap pattern; also fix the packaged entrypoint before adding more commands. [VERIFIED: codebase grep] [VERIFIED: local CLI run] [CITED: https://typer.tiangolo.com/tutorial/commands/callback/] |
| OPS-05 | CI or local quality gates for tests, linting, formatting, typing, and critical leakage/EV logic. | Implement repo-local commands with `uv run`, add `.pre-commit-config.yaml`, and add GitHub Actions CI wired to `uv sync --locked`. [VERIFIED: codebase grep] [CITED: https://pre-commit.com/] [CITED: https://docs.astral.sh/uv/guides/integration/github/] |
| OPS-06 | Setup and operations documentation for data sources, Kalshi config, commands, outputs, limitations, and v1 boundaries. | Add operator-facing docs that explain the one-shot CLI workflow, output directories, backtest trust limits, and read-only v1 boundaries already locked in project context. [VERIFIED: codebase grep] |
</phase_requirements>

## Summary

Phase 07 is a composition and hardening phase, not a new domain phase: the repo already has the core monitor/report primitives in `src/tennisprediction/monitoring/scan.py`, `src/tennisprediction/monitoring/reports.py`, `src/tennisprediction/config.py`, and `src/tennisprediction/logging.py`, but the operator surface is still incomplete and thin. [VERIFIED: codebase grep] The current Typer CLI exposes only `version`, `health`, `collect-kalshi-snapshots`, and `scan-kalshi-ev`, so Phase 07 should primarily add command coverage, richer report rendering, and end-to-end operational consistency on top of existing Phase 06 outputs. [VERIFIED: local CLI run] [VERIFIED: codebase grep]

The most important codebase-specific finding is that the packaged console entry point is not yet operational: `python -m tennisprediction.cli --help` shows the Typer command tree, but `uv run tennisprediction --help` produces no CLI output because `[project.scripts]` points at `tennisprediction.cli:main` instead of the Typer app object or a callable that invokes `app()`. [VERIFIED: local CLI run] [VERIFIED: codebase grep] That should be treated as a Wave 0 ops fix before new commands are added. [ASSUMED]

The other major gaps are auditability and repo-level guardrails. Logging is currently just `basicConfig()` plus a project logger name, with no file handler, no contextual fields, and no pipeline-stage correlation metadata. [VERIFIED: codebase grep] The repo also has no `.pre-commit-config.yaml`, no `.github/workflows/` CI definition, and no operator setup guide beyond `docs/data-contracts.md`, so OPS-03 through OPS-06 will require new repo surfaces, not just code comments. [VERIFIED: codebase grep]

**Primary recommendation:** implement Phase 07 with the existing Typer + Rich + `pydantic-settings` + stdlib logging stack, fix the packaged CLI entrypoint first, and add repo config/docs rather than introducing new runtime dependencies. [VERIFIED: codebase grep] [CITED: https://typer.tiangolo.com/tutorial/commands/callback/] [CITED: https://rich.readthedocs.io/en/stable/console.html] [CITED: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/] [CITED: https://docs.python.org/3/howto/logging-cookbook.html]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Operator CLI entrypoints | API / Backend | Database / Storage | Typer commands orchestrate local Python business logic and write/read repo-local artifacts. [VERIFIED: codebase grep] [CITED: https://typer.tiangolo.com/tutorial/commands/callback/] |
| Human-facing opportunity reports | API / Backend | Database / Storage | The report is generated server-side in Python from accepted/rejected records and persisted under `reports/`. [VERIFIED: codebase grep] [CITED: https://rich.readthedocs.io/en/stable/console.html] |
| Machine-readable report persistence | Database / Storage | API / Backend | `summary.json`, CSV, and Parquet are the canonical artifacts that operator rendering should derive from, not replace. [VERIFIED: codebase grep] |
| Audit logging | API / Backend | Database / Storage | Log context is assembled in Python and then emitted to console/file handlers for later review. [VERIFIED: codebase grep] [CITED: https://docs.python.org/3/howto/logging-cookbook.html] |
| Quality gates and CI | API / Backend | CDN / Static | The commands live in repo config and CI workflow YAML; no browser tier participates. [VERIFIED: codebase grep] [CITED: https://docs.astral.sh/uv/guides/integration/github/] |
| Setup and operator documentation | CDN / Static | API / Backend | Markdown docs are static artifacts that describe how to run the Python workflow and interpret outputs. [VERIFIED: codebase grep] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `typer` | `0.26.7` latest on PyPI, released 2026-06-03; repo env has `0.26.7`. [CITED: https://pypi.org/project/typer/] [VERIFIED: local CLI run] | Typed multi-command CLI surface. [CITED: https://typer.tiangolo.com/tutorial/commands/callback/] | Official docs show grouped commands and top-level callbacks, which matches the repo’s single-app pattern and avoids ad hoc CLI plumbing. [VERIFIED: codebase grep] [CITED: https://typer.tiangolo.com/tutorial/commands/callback/] |
| `rich` | `15.0.0` latest on PyPI, released 2026-04-12; repo env has `15.0.0`. [CITED: https://pypi.org/project/rich/] [VERIFIED: local CLI run] | Operator-facing terminal tables plus optional persisted text/HTML/SVG exports. [CITED: https://rich.readthedocs.io/en/stable/console.html] | Rich’s `Console(record=True)` and table APIs fit the locked “terminal/file-first” requirement without hand-rolled formatting. [CITED: https://rich.readthedocs.io/en/stable/console.html] [CITED: https://rich.readthedocs.io/en/stable/tables.html] |
| `pydantic-settings` | `2.14.2` latest on PyPI, released 2026-06-19; repo env has `2.14.1`. [CITED: https://pypi.org/project/pydantic-settings/] [VERIFIED: local CLI run] | Central settings for thresholds, artifact paths, report paths, and optional dotenv loading. [CITED: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/] | The repo already uses `BaseSettings` and repo-local path validation, so Phase 07 should extend that seam instead of creating a second config system. [VERIFIED: codebase grep] [CITED: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/] |
| `logging` / `logging.handlers` (stdlib) | Python `3.12` project runtime; official docs checked against Python `3.14.6`. [VERIFIED: local CLI run] [CITED: https://docs.python.org/3/howto/logging-cookbook.html] | Console/file audit logging with contextual metadata and rotation. [CITED: https://docs.python.org/3/howto/logging-cookbook.html] | The standard library already provides adapters, filters, `dictConfig`, and rotating file handlers, so no third-party logging framework is needed for v1. [CITED: https://docs.python.org/3/howto/logging-cookbook.html] [CITED: https://docs.python.org/3/library/logging.handlers.html] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `uv` | `0.11.24` latest on PyPI, released 2026-06-23; local access is `python3 -m uv 0.11.21`. [CITED: https://pypi.org/project/uv/] [VERIFIED: local CLI run] | Locked environment sync and all local/CI quality-gate execution. [CITED: https://docs.astral.sh/uv/guides/integration/github/] | Use for every documented local command and CI step so global tool installs are irrelevant. [CITED: https://docs.astral.sh/uv/guides/integration/github/] |
| `pytest` | `9.1.1` latest on PyPI, released 2026-06-19; repo env has `9.1.0`. [CITED: https://pypi.org/project/pytest/] [VERIFIED: local CLI run] | Unit and smoke verification. [VERIFIED: codebase grep] | Use for CLI/report/logging tests and keep leakage/EV tests in the fast default gate. [VERIFIED: codebase grep] |
| `ruff` | `0.15.19` latest on PyPI, released 2026-06-24; repo env has `0.15.17`. [CITED: https://pypi.org/project/ruff/] [VERIFIED: local CLI run] | Lint and format checks. [VERIFIED: codebase grep] | Use as the single lint/format gate already configured in `pyproject.toml`. [VERIFIED: codebase grep] |
| `mypy` | `2.1.0` latest on PyPI, released 2026-05-11; repo env has `1.18.2`. [CITED: https://pypi.org/project/mypy/] [VERIFIED: local CLI run] | Static typing checks for CLI/config/logging/report DTO seams. [VERIFIED: codebase grep] | Use strict typing at API boundaries; the repo already opts into strict mode. [VERIFIED: codebase grep] |
| `pre-commit` | `4.6.0` latest on PyPI, released 2026-04-21; repo env has `4.3.0`. [CITED: https://pypi.org/project/pre-commit/] [VERIFIED: local CLI run] | Local hook runner for repeatable quality gates. [CITED: https://pre-commit.com/] | Add `.pre-commit-config.yaml` and run `pre-commit install --install-hooks` so developers can run the same gates before pushing. [CITED: https://pre-commit.com/] |
| GitHub Actions | `actions/checkout@v6`, `actions/setup-python@v6`, `astral-sh/setup-uv@v8.1.0` are the current official examples reviewed on 2026-06-24. [CITED: https://docs.github.com/en/actions/tutorials/build-and-test-code/python] [CITED: https://docs.astral.sh/uv/guides/integration/github/] | Repo-level CI for the same local gates. [CITED: https://docs.github.com/en/actions/tutorials/build-and-test-code/python] | Use a small CI job that installs uv, syncs the lockfile, and runs the same commands documented for local use. [CITED: https://docs.astral.sh/uv/guides/integration/github/] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `typer` | `argparse` | `argparse` is fine for basic scripts, but the repo already uses Typer and Phase 07 needs grouped commands, typed options, and consistent help output. [VERIFIED: codebase grep] [CITED: https://typer.tiangolo.com/tutorial/commands/callback/] |
| `rich` | Manual string formatting / CSV-only output | Manual formatting is brittle for operator summaries and loses the ability to export the same console output cleanly. [CITED: https://rich.readthedocs.io/en/stable/console.html] |
| `pydantic-settings` | Manual `os.environ` parsing | Manual parsing would duplicate validation and weaken the repo’s path-safety guarantees. [VERIFIED: codebase grep] [CITED: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/] |
| stdlib logging | `structlog` or `loguru` | Those can work, but Phase 07 does not need a new dependency because stdlib logging already covers contextual fields, filters, rotation, and handler fan-out. [CITED: https://docs.python.org/3/howto/logging-cookbook.html] [CITED: https://docs.python.org/3/library/logging.handlers.html] |
| ad hoc shell-only gates | `pre-commit` + GitHub Actions | Shell scripts alone do not give the repo-level local/CI consistency locked by D-08. [CITED: https://pre-commit.com/] [CITED: https://docs.astral.sh/uv/guides/integration/github/] |

**Installation:** No new Phase 07 runtime package is required. Implement the phase against the existing locked environment and document `UV_CACHE_DIR=.uv-cache python3 -m uv sync --locked --dev` as the standard bootstrap command. [VERIFIED: codebase grep] [VERIFIED: local CLI run]

**Version verification:** The repo’s lockfile/runtime currently lags the latest PyPI releases for `pydantic-settings`, `pytest`, `ruff`, `mypy`, `pre-commit`, and the standalone `uv` release line, but all required tooling is already runnable through `python3 -m uv run ...`. [VERIFIED: local CLI run] [CITED: https://pypi.org/project/pydantic-settings/] [CITED: https://pypi.org/project/pytest/] [CITED: https://pypi.org/project/ruff/] [CITED: https://pypi.org/project/mypy/] [CITED: https://pypi.org/project/pre-commit/] [CITED: https://pypi.org/project/uv/]

## Package Legitimacy Audit

> Phase 07 does not require any new external package additions; the table below is a spot-check of the existing operator/quality stack only. [VERIFIED: codebase grep]

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `typer` | PyPI [CITED: https://pypi.org/project/typer/] | Released 2026-06-03. [CITED: https://pypi.org/project/typer/] | Unknown from seam. [VERIFIED: package-legitimacy check] | `https://github.com/fastapi/typer` [VERIFIED: package-legitimacy check] | `SUS` because the seam reported `too-new` and `unknown-downloads`. [VERIFIED: package-legitimacy check] | Existing pinned dependency only; no new Phase 07 install decision. |
| `rich` | PyPI [CITED: https://pypi.org/project/rich/] | Released 2026-04-12. [CITED: https://pypi.org/project/rich/] | Unknown from seam. [VERIFIED: package-legitimacy check] | `https://github.com/Textualize/rich` [VERIFIED: package-legitimacy check] | `SUS` because the seam lacked download telemetry. [VERIFIED: package-legitimacy check] | Existing pinned dependency only; no new Phase 07 install decision. |
| `pydantic-settings` | PyPI [CITED: https://pypi.org/project/pydantic-settings/] | Released 2026-06-19. [CITED: https://pypi.org/project/pydantic-settings/] | Unknown from seam. [VERIFIED: package-legitimacy check] | `https://github.com/pydantic/pydantic-settings` [VERIFIED: package-legitimacy check] | `SUS` because the seam reported `too-new` and `unknown-downloads`. [VERIFIED: package-legitimacy check] | Existing pinned dependency only; no new Phase 07 install decision. |
| `pre-commit` | PyPI [CITED: https://pypi.org/project/pre-commit/] | Released 2026-04-21. [CITED: https://pypi.org/project/pre-commit/] | Unknown from seam. [VERIFIED: package-legitimacy check] | `https://github.com/pre-commit/pre-commit` [VERIFIED: package-legitimacy check] | `SUS` because the seam lacked download telemetry. [VERIFIED: package-legitimacy check] | Existing pinned dependency only; no new Phase 07 install decision. |
| `pytest` | PyPI [CITED: https://pypi.org/project/pytest/] | Released 2026-06-19. [CITED: https://pypi.org/project/pytest/] | Unknown from seam. [VERIFIED: package-legitimacy check] | `https://github.com/pytest-dev/pytest` [VERIFIED: package-legitimacy check] | `SUS` because the seam reported `too-new` and `unknown-downloads`. [VERIFIED: package-legitimacy check] | Existing pinned dependency only; no new Phase 07 install decision. |
| `ruff` | PyPI [CITED: https://pypi.org/project/ruff/] | Released 2026-06-24. [CITED: https://pypi.org/project/ruff/] | Unknown from seam. [VERIFIED: package-legitimacy check] | `https://docs.astral.sh/ruff` from seam metadata. [VERIFIED: package-legitimacy check] | `SUS` because the seam reported `too-new` and `unknown-downloads`. [VERIFIED: package-legitimacy check] | Existing pinned dependency only; no new Phase 07 install decision. |
| `mypy` | PyPI [CITED: https://pypi.org/project/mypy/] | Released 2026-05-11. [CITED: https://pypi.org/project/mypy/] | Unknown from seam. [VERIFIED: package-legitimacy check] | `https://www.mypy-lang.org/` from seam metadata. [VERIFIED: package-legitimacy check] | `SUS` because the seam lacked download telemetry. [VERIFIED: package-legitimacy check] | Existing pinned dependency only; no new Phase 07 install decision. |

**Packages removed due to [SLOP] verdict:** none. [VERIFIED: package-legitimacy check]
**Packages flagged as suspicious [SUS]:** `typer`, `rich`, `pydantic-settings`, `pre-commit`, `pytest`, `ruff`, `mypy`, but only because the legitimacy seam could not supply download telemetry and treated recent releases conservatively; Phase 07 does not recommend adding any new package beyond the already-pinned repo stack. [VERIFIED: package-legitimacy check] [CITED: https://pypi.org/project/typer/] [CITED: https://pypi.org/project/rich/] [CITED: https://pypi.org/project/pydantic-settings/] [CITED: https://pypi.org/project/pre-commit/] [CITED: https://pypi.org/project/pytest/] [CITED: https://pypi.org/project/ruff/] [CITED: https://pypi.org/project/mypy/]

## Architecture Patterns

### System Architecture Diagram

The recommended Phase 07 data flow is a thin orchestration layer on top of existing Phase 06 monitor artifacts. [VERIFIED: codebase grep]

```text
Operator
  |
  v
Typer CLI callback
  - load Settings
  - configure logging
  - stamp run_id / artifact selection
  |
  +--> ingest / feature / train / evaluate / backtest commands
  |      |
  |      v
  |   existing pipeline modules
  |
  +--> kalshi collection / live scan / report commands
         |
         v
   monitoring.scan.run_kalshi_ev_scan()
         |
         +--> accepted/rejected decision rows
         |      |
         |      +--> summary.json / parquet / csv
         |      +--> Rich operator report
         |      +--> audit log file + console log
         |
         +--> warnings / rejection counts / trust banners
```

This design preserves D-02 and D-03 because the human-facing report is assembled from the same canonical rows already persisted for machine consumption. [VERIFIED: codebase grep]

### Recommended Project Structure

The existing repo shape should be extended, not replaced. [VERIFIED: codebase grep]

```text
src/tennisprediction/
├── cli.py                # single Typer app; add grouped one-shot commands here or via sub-typers
├── config.py             # extend Settings with report/audit/runtime knobs
├── logging.py            # replace bootstrap-only setup with contextual file/console handlers
├── monitoring/
│   ├── scan.py           # keep scoring/orchestration here
│   ├── reports.py        # keep canonical row ranking + persistence here
│   └── alerts.py         # add operator-facing recommendation/report assembly here
└── ...

docs/
├── data-contracts.md     # existing
└── operations.md         # Phase 07 operator/setup/runbook

.github/workflows/
└── ci.yml                # repo-level quality gates

.pre-commit-config.yaml   # local quality gates
```

### Pattern 1: Single Typer App With Callback-Owned Global Options

**What:** Keep one `typer.Typer()` app and use `@app.callback()` for shared setup flags or context that must apply before subcommands. [CITED: https://typer.tiangolo.com/tutorial/commands/callback/]
**When to use:** Use this for global report/log/config options, environment selection, or shared run metadata. [CITED: https://typer.tiangolo.com/tutorial/commands/callback/]
**Example:**

```python
# Source: https://typer.tiangolo.com/tutorial/commands/callback/
import typer

app = typer.Typer()
state: dict[str, object] = {}

@app.callback()
def main(run_id: str = "manual", verbose: bool = False) -> None:
    state["run_id"] = run_id
    state["verbose"] = verbose

@app.command("report-opportunities")
def report_opportunities() -> None:
    ...

if __name__ == "__main__":
    app()
```

### Pattern 2: Canonical Rows First, Rich View Second

**What:** Persist one ranked list of canonical decision rows, then derive both the operator console view and any saved summary text/HTML from that same list. [VERIFIED: codebase grep] [CITED: https://rich.readthedocs.io/en/stable/console.html]
**When to use:** Use this for Phase 07 report polish so OPS-01 does not fork into separate “machine” and “human” truth sources. [VERIFIED: codebase grep]
**Example:**

```python
# Source: https://rich.readthedocs.io/en/stable/console.html
from rich.console import Console
from rich.table import Table

console = Console(record=True)
table = Table("Ticker", "Match", "EV", "Edge", title="Accepted Opportunities")

for row in ranked_rows:
    table.add_row(row["market_ticker"], row["canonical_match_id"], row["ev"], row["edge"])

console.print(table)
console.save_text("reports/monitoring/run-001/operator-report.txt")
```

### Pattern 3: Contextual Audit Logging With Adapters/Filters

**What:** Use one project logger hierarchy with contextual fields like `run_id`, `command`, `artifact_run_id`, `market_ticker`, and `decision_state` added through adapters or filters. [CITED: https://docs.python.org/3/howto/logging-cookbook.html]
**When to use:** Use this for CLI commands that span multiple modules and need correlated audit trails. [VERIFIED: codebase grep]
**Example:**

```python
# Source: https://docs.python.org/3/howto/logging-cookbook.html
import logging

base_logger = logging.getLogger("tennisprediction")
audit_logger = logging.LoggerAdapter(
    base_logger,
    {"run_id": "scan-001", "command": "scan-kalshi-ev"},
)

audit_logger.info("starting live scan")
```

### Anti-Patterns to Avoid

- **Parallel report storage paths:** Do not create a second alert/report directory tree that diverges from `reports/monitoring/<run_id>/`; extend the existing writer. [VERIFIED: codebase grep]
- **Packaged CLI no-op:** Do not add more commands until `[project.scripts]` invokes the real Typer application path. [VERIFIED: codebase grep] [VERIFIED: local CLI run]
- **String-only logging:** Do not rely on free-form log messages with no stable fields; Phase 07 needs searchable run metadata. [VERIFIED: codebase grep] [CITED: https://docs.python.org/3/howto/logging-cookbook.html]
- **Undocumented one-off shell commands:** Do not treat a copied terminal incantation as a quality gate; make the gate runnable through `uv run`, `pre-commit`, and CI. [CITED: https://pre-commit.com/] [CITED: https://docs.astral.sh/uv/guides/integration/github/] |

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLI parsing/help/completion | Custom `sys.argv` or ad hoc `argparse` trees | `typer` | Typer already matches the repo, generates help, and supports grouped commands cleanly. [VERIFIED: codebase grep] [CITED: https://typer.tiangolo.com/tutorial/commands/callback/] |
| Terminal report formatting | Manual width-padding or print-only tables | `rich.Table` + `Console(record=True)` | Rich handles readable terminal layout and optional persisted exports from the same render path. [CITED: https://rich.readthedocs.io/en/stable/tables.html] [CITED: https://rich.readthedocs.io/en/stable/console.html] |
| Env/config parsing | Hand-written `os.environ.get()` sprawl | `pydantic-settings` | The repo already centralizes repo-local path safety in `Settings`. [VERIFIED: codebase grep] [CITED: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/] |
| Audit log rotation/context | Custom file appenders and string interpolation | stdlib logging adapters/filters + rotating handlers | The standard library already covers context injection and disk rotation. [CITED: https://docs.python.org/3/howto/logging-cookbook.html] [CITED: https://docs.python.org/3/library/logging.handlers.html] |
| Local/CI quality orchestration | One-off shell scripts only | `pre-commit` + GitHub Actions + `uv run` | This gives one documented gate surface for developers and CI. [CITED: https://pre-commit.com/] [CITED: https://docs.astral.sh/uv/guides/integration/github/] |

**Key insight:** Phase 07 should assemble existing validated business logic into reliable operator workflows; custom replacements for CLI, config, logging, or gates would add operational risk without improving the ATP/Kalshi domain logic. [VERIFIED: codebase grep]

## Common Pitfalls

### Pitfall 1: Fixing the report UX by forking the data contract

**What goes wrong:** A prettier operator report starts writing its own JSON/CSV structure instead of using the accepted/rejected row contract already shipped in Phase 06. [VERIFIED: codebase grep]
**Why it happens:** It is tempting to treat the Rich view as a separate feature instead of a rendering of canonical ranked rows. [ASSUMED]
**How to avoid:** Keep one ranked-row assembly step, then derive console, text, summary, and persisted artifacts from that shared object. [VERIFIED: codebase grep]
**Warning signs:** New report directories or new duplicated “opportunity summary” schemas appear outside `reports/monitoring/<run_id>/`. [VERIFIED: codebase grep]

### Pitfall 2: Shipping more commands without fixing the packaged entrypoint

**What goes wrong:** Documentation advertises `tennisprediction ...` commands, but the installed console script still no-ops because it only calls `main()` instead of invoking the Typer app. [VERIFIED: local CLI run] [VERIFIED: codebase grep]
**Why it happens:** The module execution path works, so the project-script path can be missed. [VERIFIED: local CLI run]
**How to avoid:** Treat the script target as a Wave 0 requirement and add a smoke test for the installed command path. [ASSUMED]
**Warning signs:** `python -m tennisprediction.cli --help` works but `uv run tennisprediction --help` prints nothing. [VERIFIED: local CLI run]

### Pitfall 3: Audit logs become noisy but still unauditable

**What goes wrong:** The code logs a lot more lines, but none carry stable run metadata, artifact IDs, or decision identifiers. [VERIFIED: codebase grep]
**Why it happens:** Plain `logger.info("...")` calls are added without adapters, filters, or handler structure. [VERIFIED: codebase grep]
**How to avoid:** Standardize fields such as `run_id`, `command`, `artifact_run_id`, `market_ticker`, `mapping_state`, and `decision_state` at the logging seam. [CITED: https://docs.python.org/3/howto/logging-cookbook.html]
**Warning signs:** Reconstructing one live scan requires grepping free-form text instead of filtering by fields. [ASSUMED]

### Pitfall 4: Quality gates are documented but not executable

**What goes wrong:** The phase adds a README checklist but still leaves the repo without pre-commit config or CI workflow files. [VERIFIED: codebase grep]
**Why it happens:** Docs are faster to write than runnable repo config. [ASSUMED]
**How to avoid:** Add the local and CI configs in the same slice as the documentation and wire them to the documented `uv run` commands. [CITED: https://pre-commit.com/] [CITED: https://docs.astral.sh/uv/guides/integration/github/]
**Warning signs:** `.pre-commit-config.yaml` and `.github/workflows/ci.yml` are still missing after OPS-05 is marked complete. [VERIFIED: codebase grep]

### Pitfall 5: Secrets leak into logs or persisted reports

**What goes wrong:** Kalshi access keys, private-key paths, or request signing details get logged as part of “helpful” operator diagnostics. [VERIFIED: codebase grep]
**Why it happens:** Audit logging is added late and the easiest fields to serialize are the full settings or client request objects. [ASSUMED]
**How to avoid:** Log IDs, paths, and safe metadata only; explicitly exclude secret material and redact sensitive settings fields. [CITED: https://docs.python.org/3/howto/logging-cookbook.html]
**Warning signs:** Log lines include raw auth headers, private key contents, or full settings dumps. [ASSUMED]

## Code Examples

Verified patterns from official sources:

### Export A Persisted Operator Report From The Same Rich Render

```python
# Source: https://rich.readthedocs.io/en/stable/console.html
from rich.console import Console
from rich.table import Table

console = Console(record=True)
table = Table("Ticker", "Match", "EV", title="Accepted Opportunities")
table.add_row("KXATP-001", "match:001", "0.083")
console.print(table)
console.save_text("operator-report.txt")
```

### Use Dotenv-Backed Settings Without Hand Parsing

```python
# Source: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    reports_dir: str = "reports"
```

### Install And Run Pre-commit Hooks For The Whole Repo

```bash
# Source: https://pre-commit.com/
pre-commit install --install-hooks
pre-commit run --all-files
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Typer depended on external Click packaging assumptions. [CITED: https://pypi.org/project/typer/] | Typer 0.26 vendors Click internally. [CITED: https://pypi.org/project/typer/] | Typer `0.26.0`, 2026-05-26. [CITED: https://pypi.org/project/typer/] | Avoid writing Phase 07 code that depends on direct Click internals or plugin assumptions. [CITED: https://pypi.org/project/typer/] |
| CI examples commonly showed `pip install -r requirements.txt`. [CITED: https://docs.github.com/en/actions/tutorials/build-and-test-code/python] | The official uv guide now recommends `setup-uv`, `uv sync --locked --all-extras --dev`, and `uv run ...`. [CITED: https://docs.astral.sh/uv/guides/integration/github/] | uv guide reviewed 2026-06-24; page updated June 23, 2026. [CITED: https://docs.astral.sh/uv/guides/integration/github/] | Phase 07 should document uv-native quality gates instead of drifting back to mixed pip/venv commands. [CITED: https://docs.astral.sh/uv/guides/integration/github/] |

**Deprecated/outdated:**
- Treating `uv` as a global binary requirement is outdated for this repo because the environment can already be driven through `python3 -m uv` even when the standalone `uv` shell command is missing. [VERIFIED: local CLI run]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Fixing `[project.scripts]` should be treated as a Wave 0 task before any CLI expansion. | Summary / Common Pitfalls | New commands could be implemented correctly but still be unusable through the advertised package entrypoint. |
| A2 | Free-form log lines without stable fields would be insufficient for audit review. | Common Pitfalls | If the team only wants human-readable logs, the logging design could be simpler than recommended. |
| A3 | Documentation and repo config should land in the same plan slice for OPS-05/OPS-06. | Common Pitfalls | The planner might otherwise split them, which could still work if sequencing is managed carefully. |

## Resolved Questions

1. **OPS-02 source of truth**
   - Resolution: Locked decisions D-06 and D-07 are authoritative. Phase 07 does not include configurable polling interval or any other continuous-run control. [VERIFIED: codebase grep]
   - Updated contract: OPS-02 means configurable thresholds, model artifact selection, report selection, storage paths, and terminal/file alert channel settings for one-shot runs. [VERIFIED: codebase grep]
   - Follow-through: `ROADMAP.md`, `REQUIREMENTS.md`, and the Phase 07 plans must use this one-shot wording so execution starts from a resolved contract with no polling mismatch left open. [VERIFIED: codebase grep]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python3` | bootstrap and `python3 -m uv` entry | ✓ | `3.14.0` globally. [VERIFIED: local CLI run] | Use `python3 -m uv run python` for the project-pinned interpreter. [VERIFIED: local CLI run] |
| project Python via `uv` | actual repo runtime | ✓ | `3.12.4`. [VERIFIED: local CLI run] | none |
| `python3 -m uv` | lockfile sync and all documented commands | ✓ | `0.11.21`. [VERIFIED: local CLI run] | none |
| `uv` shell binary | docs convenience only | ✗ | — [VERIFIED: local CLI run] | Document `python3 -m uv ...` instead. [VERIFIED: local CLI run] |
| `pytest` | tests | ✓ via `uv run` | `9.1.0`. [VERIFIED: local CLI run] | none |
| `ruff` | lint/format gates | ✓ via `uv run` | `0.15.17`. [VERIFIED: local CLI run] | none |
| `mypy` | typing gate | ✓ via `uv run` | `1.18.2`. [VERIFIED: local CLI run] | none |
| `pre-commit` | local hook gate | ✓ via `uv run` | `4.3.0`. [VERIFIED: local CLI run] | Can still run underlying `uv run` commands directly until config is added. [VERIFIED: local CLI run] |
| `.github/workflows/ci.yml` | repo CI | ✗ | — [VERIFIED: codebase grep] | Local `uv run` commands only until workflow is added. [VERIFIED: codebase grep] |
| `.pre-commit-config.yaml` | local hook config | ✗ | — [VERIFIED: codebase grep] | Manual `uv run` commands only until config is added. [VERIFIED: codebase grep] |

**Missing dependencies with no fallback:**
- None at the machine level; the missing pieces are repo config artifacts, not local tool availability. [VERIFIED: local CLI run] [VERIFIED: codebase grep]

**Missing dependencies with fallback:**
- Standalone `uv` binary is missing, but `python3 -m uv` fully covers the required workflow. [VERIFIED: local CLI run]
- Repo CI and pre-commit config are missing, but local `uv run` commands can still serve as Phase 07’s initial verification path. [VERIFIED: codebase grep] [VERIFIED: local CLI run]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest 9.1.0` via `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest`. [VERIFIED: local CLI run] |
| Config file | `pyproject.toml`. [VERIFIED: codebase grep] |
| Quick run command | `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_cli_smoke.py tests/unit/test_live_monitor_reports.py tests/unit/test_live_scan_orchestration.py tests/unit/test_feature_leakage.py tests/unit/test_backtesting_decisions.py tests/unit/test_live_scan_pricing_contract.py -x` [VERIFIED: codebase grep] |
| Full suite command | `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q` [VERIFIED: codebase grep] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OPS-01 | Report writer persists and ranks accepted/rejected outputs; Phase 07 should expand it to recommendation/human summary coverage. [VERIFIED: codebase grep] | unit | `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_live_monitor_reports.py -x` | ✅ |
| OPS-02 | Settings remain repo-local and should gain new Phase 07 knobs without breaking path safety. [VERIFIED: codebase grep] | unit | `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_cli_smoke.py -x` | ✅ |
| OPS-03 | Audit logging must carry stable command/run context across modules. [CITED: https://docs.python.org/3/howto/logging-cookbook.html] | unit | `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_operational_logging.py -x` | ❌ Wave 0 |
| OPS-04 | CLI commands cover the full operator flow and the packaged entrypoint works. [VERIFIED: local CLI run] | smoke | `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_cli_commands.py -x` | ❌ Wave 0 |
| OPS-05 | Lint, format, typing, leakage, and EV checks run locally and in CI. [VERIFIED: codebase grep] | mixed | `UV_CACHE_DIR=.uv-cache python3 -m uv run ruff check . && UV_CACHE_DIR=.uv-cache python3 -m uv run mypy src && UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q tests/unit/test_feature_leakage.py tests/unit/test_backtesting_decisions.py tests/unit/test_live_scan_pricing_contract.py -x` [ASSUMED] | ⚠️ Partial |
| OPS-06 | Docs explain setup, commands, outputs, limitations, and boundaries. [VERIFIED: codebase grep] | manual-only | `— manual doc review against command/output checklist` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** run the quick `pytest` command plus the narrow `ruff`/`mypy` target for touched files. [ASSUMED]
- **Per wave merge:** run `UV_CACHE_DIR=.uv-cache python3 -m uv run pytest -q`, `UV_CACHE_DIR=.uv-cache python3 -m uv run ruff check .`, and `UV_CACHE_DIR=.uv-cache python3 -m uv run mypy src`. [VERIFIED: codebase grep]
- **Phase gate:** full suite green, packaged CLI smoke green, and docs/CI config present before `$gsd-verify-work`. [ASSUMED]

### Wave 0 Gaps

- [ ] `tests/unit/test_operational_logging.py` — covers OPS-03 logging context, handler fan-out, and redaction behavior.
- [ ] `tests/unit/test_cli_commands.py` — covers OPS-04 command tree and the packaged `tennisprediction` entrypoint path.
- [ ] `.pre-commit-config.yaml` — covers OPS-05 local quality gate packaging.
- [ ] `.github/workflows/ci.yml` — covers OPS-05 repo CI packaging.
- [ ] An operator-doc checklist artifact or doc test plan for OPS-06 — current repo docs do not cover setup/runbook/output trust boundaries. [VERIFIED: codebase grep]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | Kalshi credentials remain env/file based, and Phase 07 docs/logging must avoid exposing keys or signed payload material. [VERIFIED: codebase grep] [CITED: https://docs.python.org/3/howto/logging-cookbook.html] |
| V3 Session Management | no | The phase is a local one-shot CLI, not a sessionful web application. [VERIFIED: codebase grep] |
| V4 Access Control | no | There is no multi-user authz surface in scope for this repo-local CLI phase. [VERIFIED: codebase grep] |
| V5 Input Validation | yes | Typer parameter parsing plus `pydantic-settings` validation and existing repo-local path guards in `Settings`. [VERIFIED: codebase grep] [CITED: https://typer.tiangolo.com/tutorial/commands/callback/] [CITED: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/] |
| V6 Cryptography | yes | Existing Kalshi signing uses `cryptography`; Phase 07 should preserve that seam and only harden surrounding ops/logging behavior. [VERIFIED: codebase grep] |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Secret leakage in logs or reports | Information Disclosure | Redact credentials, do not serialize full settings/client objects, and keep audit logs to safe identifiers/paths. [CITED: https://docs.python.org/3/howto/logging-cookbook.html] |
| Path escape through configurable output paths | Tampering | Keep all writable paths inside the repository through the existing `Settings.ensure_repo_local_paths()` validation. [VERIFIED: codebase grep] |
| Log injection from untrusted market titles or rule text | Tampering | Treat external strings as data fields, not format strings or Rich markup directives. [ASSUMED] |
| Untrusted or stale opportunity claims | Spoofing | Persist provenance, rejection reasons, and trust banners alongside accepted/rejected rows before rendering recommendations. [VERIFIED: codebase grep] |

## Sources

### Primary (HIGH confidence)

- Local codebase inspection of `src/tennisprediction/cli.py`, `src/tennisprediction/config.py`, `src/tennisprediction/logging.py`, `src/tennisprediction/monitoring/scan.py`, `src/tennisprediction/monitoring/reports.py`, `pyproject.toml`, and the Phase 06/05 summaries. [VERIFIED: codebase grep]
- Local command verification of `python -m tennisprediction.cli --help`, `uv run tennisprediction --help`, and targeted `pytest` runs. [VERIFIED: local CLI run]

### Secondary (MEDIUM confidence)

- Typer callback and multi-command docs: https://typer.tiangolo.com/tutorial/commands/callback/
- Python logging cookbook: https://docs.python.org/3/howto/logging-cookbook.html
- Python logging handlers: https://docs.python.org/3/library/logging.handlers.html
- Rich console export docs: https://rich.readthedocs.io/en/stable/console.html
- Rich tables docs: https://rich.readthedocs.io/en/stable/tables.html
- Pydantic settings docs: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/
- pre-commit docs: https://pre-commit.com/
- GitHub Actions Python guide: https://docs.github.com/en/actions/tutorials/build-and-test-code/python
- uv GitHub Actions guide: https://docs.astral.sh/uv/guides/integration/github/
- uv pre-commit guide: https://docs.astral.sh/uv/guides/integration/pre-commit/
- PyPI pages reviewed for `uv`, `typer`, `rich`, `pydantic-settings`, `pre-commit`, `pytest`, `ruff`, and `mypy`. [CITED: https://pypi.org/project/uv/] [CITED: https://pypi.org/project/typer/] [CITED: https://pypi.org/project/rich/] [CITED: https://pypi.org/project/pydantic-settings/] [CITED: https://pypi.org/project/pre-commit/] [CITED: https://pypi.org/project/pytest/] [CITED: https://pypi.org/project/ruff/] [CITED: https://pypi.org/project/mypy/]

### Tertiary (LOW confidence)

- None; remaining uncertainty is recorded explicitly in the assumptions log instead of being treated as sourced fact. [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - versions and docs were verified from official sources, but package-legitimacy telemetry remained conservative and the repo lockfile lags some latest releases. [VERIFIED: package-legitimacy check] [CITED: https://pypi.org/project/typer/] [CITED: https://pypi.org/project/rich/] [CITED: https://pypi.org/project/pydantic-settings/] [CITED: https://pypi.org/project/pre-commit/] [CITED: https://pypi.org/project/pytest/] [CITED: https://pypi.org/project/ruff/] [CITED: https://pypi.org/project/mypy/]
- Architecture: HIGH - the recommended plan mostly extends concrete existing repo seams and locked user decisions. [VERIFIED: codebase grep]
- Pitfalls: MEDIUM - the most important pitfalls are directly observed in the codebase, but a few planning-sequencing recommendations are still judgment calls. [VERIFIED: codebase grep] [ASSUMED]

**Research date:** 2026-06-24
**Valid until:** 2026-07-01
