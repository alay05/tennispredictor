# Phase 7: Alerts and Operational Hardening - Context

**Gathered:** 2026-06-24
**Status:** Ready for planning

<domain>
## Phase Boundary

This phase turns the completed read-only ATP-to-Kalshi monitor into an operator-ready v1 surface: polished terminal and file-based opportunity reports, configurable alert/report settings, auditable operational commands, hardened quality gates, and documentation that explains how to run and trust the workflow. It does not add trade execution, non-Kalshi venues, non-ATP scope, external notification infrastructure, or continuous polling/orchestration beyond one-shot commands.

</domain>

<decisions>
## Implementation Decisions

### Alert delivery scope
- **D-01:** v1 alert delivery remains terminal/file-only. Phase 7 must not add email, SMS, Slack, push, webhook, or other external notification channels.
- **D-02:** The operator-facing alert/report layer should build on the existing persisted monitoring outputs from Phase 06 rather than inventing a parallel storage path.

### Report presentation and operator UX
- **D-03:** The primary operator surface should be a polished human-facing report on top of the existing Phase 06 machine-readable artifacts: easy to scan, focused on actionable accepted opportunities, and explicit about rejected/excluded counts and health warnings.
- **D-04:** Exact report layout, wording, and Rich presentation details are delegated to the agent, provided the output stays concise, operator-friendly, and evidence-forward.
- **D-05:** Recommendation language should stay read-only and advisory. The surface may rank, label, and summarize opportunities, but it must not imply or trigger automated execution.

### Operational command model
- **D-06:** Phase 7 should expose one-shot operator commands only. Continuous polling, daemonized scanning, schedulers, and long-running workflows are deferred to later work.
- **D-07:** Operator-tunable settings for this phase should at minimum cover thresholds, artifact/report selection, and storage paths. Polling/continuous-run controls are out of scope for now.

### Hardening and documentation bar
- **D-08:** Phase 7 should harden the workflow with strong local quality gates and repository-level CI expectations, not just ad hoc commands.
- **D-09:** Documentation should be good enough for a developer/operator to set up the project, run the main CLI flows, understand the outputs, and understand the scope boundaries and trust limitations of the signals.

### the agent's Discretion
- Choose the exact Rich report composition, CLI subcommand split, and documentation file structure as long as they preserve the read-only, terminal/file-first v1 boundary.
- Choose the exact quality-gate packaging (for example local commands, helper targets, pre-commit wiring, CI workflow shape) as long as tests, linting, formatting, and typing are clearly runnable and documented.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and phase contract
- `.planning/PROJECT.md` — durable ATP-only / Kalshi-only / read-only v1 constraints
- `.planning/REQUIREMENTS.md` — Phase 7 requirement IDs `OPS-01` through `OPS-06`
- `.planning/ROADMAP.md` — Phase 7 goal, dependency on Phase 6, and success criteria
- `.planning/STATE.md` — current project position and the locked decision to keep v1 alerts terminal/file-only
- `AGENTS.md` — repository workflow rules and constraints

### Prior phase contracts that Phase 7 inherits
- `.planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-CONTEXT.md` — read-only monitor boundaries, ranking semantics, and accepted/rejected output expectations
- `.planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor/06-04-SUMMARY.md` — shipped monitoring surface, CLI entrypoint, and replay-backed monitor contract
- `.planning/phases/05-kalshi-read-only-market-integration/05-03-SUMMARY.md` — read-only Kalshi snapshot collection/job guardrails that operator flows must preserve

### Existing implementation files and contracts
- `src/tennisprediction/monitoring/reports.py` — current accepted/rejected persistence and Rich console rendering seam
- `src/tennisprediction/monitoring/scan.py` — read-only live/shadow scan orchestration and matched-only scoring flow
- `src/tennisprediction/cli.py` — single Typer app and current operator command registration pattern
- `src/tennisprediction/config.py` — repo-local settings boundary and configurable runtime paths
- `src/tennisprediction/logging.py` — current logging bootstrap surface to extend for operational auditability
- `pyproject.toml` — existing pytest, Ruff, mypy, and pre-commit configuration surface

### Existing tests and validation surfaces
- `tests/unit/test_live_monitor_reports.py` — current report ordering and persistence contract
- `tests/unit/test_live_scan_orchestration.py` — current scan orchestration contract
- `tests/unit/test_cli_smoke.py` — baseline CLI bootstrap pattern

### Research and stack guidance
- `.planning/research/STACK.md` — quality tooling and CI recommendations, including terminal/file-first alerting guidance
- `.planning/research/ARCHITECTURE.md` — roadmap-level expectation that alerts remain a final assembly layer on top of validated model/EV outputs
- `.planning/research/PITFALLS.md` — guidance to suppress alerts when mapping confidence, freshness, or liquidity checks fail

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/tennisprediction/monitoring/reports.py`: already writes `summary.json`, accepted/rejected parquet outputs, ranked CSV, and a basic Rich terminal view.
- `src/tennisprediction/monitoring/scan.py`: already produces the accepted/rejected record sets that Phase 7 can promote into nicer operator-facing reports and CLI commands.
- `src/tennisprediction/cli.py`: already centralizes commands in one Typer app, including `scan-kalshi-ev`.
- `src/tennisprediction/logging.py`: already provides one project logger/bootstrap seam for broader audit logging.
- `pyproject.toml`: already defines pytest, Ruff, mypy, and pre-commit surfaces that Phase 7 can consolidate into a hardened quality story.

### Established Patterns
- Machine-readable artifacts and human-readable Rich output are paired rather than merged into one opaque format.
- The project favors read-only, evidence-preserving flows over “smart” automation that hides provenance.
- CLI behavior is repo-local and settings-driven, with paths constrained through `Settings`.

### Integration Points
- Opportunity-report commands should layer on top of the Phase 06 monitoring outputs rather than duplicate scan logic.
- Audit logging should connect ingestion, monitoring, and report generation through the existing logging/bootstrap path.
- Quality gates and docs should cover the full operator workflow from snapshot collection through live scan and final report review.

</code_context>

<specifics>
## Specific Ideas

- The operator report should probably lead with a concise “what matters now” summary and only then expand into the ranked accepted opportunities and rejection/health context.
- One-shot command flows should feel operationally clean: collect if needed, scan, render, persist, inspect.
- Documentation should clearly separate “how to run it” from “why to trust or distrust the output.”

</specifics>

<deferred>
## Deferred Ideas

- External notification channels (email, Slack, SMS, webhooks, push) are deferred beyond v1.
- Continuous polling, schedulers, and long-running scan services are deferred to later phases.

</deferred>

---
*Phase: 7-Alerts and Operational Hardening*
*Context gathered: 2026-06-24*
