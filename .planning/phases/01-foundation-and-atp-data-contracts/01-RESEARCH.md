# Phase 1: Foundation and ATP Data Contracts - Research

**Researched:** 2026-06-16  
**Domain:** Python project foundation, ATP-only historical data contracts, and canonical source normalization  
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
- **D-01:** Pin the Jeff Sackmann `tennis_atp` source by commit SHA, not by branch.
- **D-02:** Keep raw source snapshots immutable and record checksums plus attribution/license metadata alongside them.
- **D-03:** Normalize into derived canonical tables only after source validation passes.
- **D-04:** Exclude qualifiers, retirements, walkovers, and incomplete matches from the canonical Phase 1 dataset.
- **D-05:** Preserve those rows only as raw source material or quarantine data if needed for audit, but do not include them in the Phase 1 canonical store.
- **D-06:** Use stable source-derived IDs where Sackmann provides them.
- **D-07:** Introduce synthetic canonical IDs only where needed for matches, tournaments, or derived records.
- **D-08:** Preserve source-lineage fields on canonical tables.
- **D-09:** Do not introduce manual player-merge logic in Phase 1.
- **D-10:** Phase 1 stops at the data foundation: ingestion, validation, normalization, and data-rule documentation.
- **D-11:** Do not add a walking skeleton or end-to-end feature slice in Phase 1.

### the agent's Discretion [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
- Use the standard project stack from the research summary for the phase 1 implementation plan.
- Choose the exact packaging, validation, and storage layout details during planning as long as they preserve the locked data rules above.

### Deferred Ideas (OUT OF SCOPE) [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
None - discussion stayed within Phase 1 scope.
</user_constraints>

<phase_requirements>
## Phase Requirements [CITED: .planning/REQUIREMENTS.md]

| ID | Description | Research Support |
|----|-------------|------------------|
| FND-01 | Developer can run a Python project with pinned dependencies, typed source layout, linting, formatting, tests, logging, and configuration. | Use `uv`, `pyproject.toml`, `pydantic-settings`, `pytest`, `ruff`, and `mypy`; bootstrap Python 3.12 because the target interpreter exists locally while the toolchain does not. [CITED: AGENTS.md] [VERIFIED: local env] [VERIFIED: PyPI] |
| FND-02 | Developer can fetch or load Jeff Sackmann `tennis_atp` ATP source files with source commit, checksum, and license/attribution metadata recorded. | Pin the upstream repo by commit SHA and persist immutable raw snapshots plus a manifest table with checksum, source URL, commit, and attribution fields. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md] [CITED: https://github.com/JeffSackmann/tennis_atp] |
| FND-03 | System validates expected Sackmann match, ranking, player, tournament, and match-stat schemas before deriving data. | Use schema-first ingestion with Polars CSV/Parquet support and an explicit quarantine path when file family or column contracts fail. [CITED: https://docs.pola.rs/] [CITED: https://github.com/JeffSackmann/tennis_atp] |
| FND-04 | System creates canonical ATP-only player, tournament, match, ranking, and match-stat tables with stable IDs and source lineage. | Canonical tables should sit above immutable raw files, reuse source player IDs, add synthetic IDs only for tournaments/matches, and preserve lineage columns on every derived row. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md] [CITED: .planning/research/ARCHITECTURE.md] |
| FND-05 | System rejects, ignores, or quarantines out-of-scope tours and match types according to documented ATP-only v1 rules. | Sackmann publishes main-draw, qual/challenger, futures, and doubles-adjacent files, so Phase 1 needs file-family filters and row-level quarantine reason codes. [CITED: https://github.com/JeffSackmann/tennis_atp] |
| FND-06 | System documents v1 handling of retirements, walkovers, missing stats, qualifiers, and incomplete matches. | Planning must produce a durable data-rules document tied to canonical inclusion/exclusion and quarantine behavior, not just code comments. [CITED: .planning/ROADMAP.md] [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md] |
</phase_requirements>

## Project Constraints (from AGENTS.md) [CITED: AGENTS.md]

- Keep Phase 1 ATP-only; do not broaden scope to WTA, Challenger, ITF, doubles, or other tours in canonical tables. [CITED: AGENTS.md]
- Keep Kalshi-only market scope as a global project boundary even though this phase does not integrate Kalshi yet. [CITED: AGENTS.md]
- Design ingestion around Jeff Sackmann `tennis_atp` CSV files and expected schema drift. [CITED: AGENTS.md]
- Preserve leakage-safe future phases by keeping chronology, provenance, and reproducibility explicit in data contracts. [CITED: AGENTS.md]
- Treat calibrated probabilities and backtesting evidence as downstream hard gates; Phase 1 must not undermine them with weak lineage or ambiguous schemas. [CITED: AGENTS.md]
- Use modular, typed, logged, configurable, reproducible code with focused unit tests for critical logic. [CITED: AGENTS.md]
- The repository has no established project skills, conventions, or existing application architecture yet, so Phase 1 sets the initial patterns. [CITED: AGENTS.md] [VERIFIED: repository scan]

## Summary

Phase 1 is a contracts-and-lineage phase, not a modeling phase. The plan should prioritize four outcomes: a reproducible Python toolchain, immutable Sackmann raw snapshots, schema validation plus quarantine rules, and ATP-only canonical tables with explicit lineage columns. If those contracts are weak, every later feature, model, and Kalshi decision will inherit ambiguity. [CITED: .planning/ROADMAP.md] [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]

The most important upstream facts are concrete. Sackmann’s repo publishes player, ranking, results, and MatchStats data; rankings are mostly complete from 1985 onward, 1982 is missing, 1973-1984 are intermittent, and each season can include main-draw, qual/challenger, and futures files. MatchStats are integer totals rather than ready-made percentages, and some tour-level rows lack stats. Those details should drive Phase 1 filters, manifests, and documentation. [CITED: https://github.com/JeffSackmann/tennis_atp]

The local environment is close but not ready: `python3.12` exists, while `uv`, `pytest`, `ruff`, and `mypy` are not installed. That means the plan should start with environment bootstrap instead of assuming the standard stack is already active. Package verification succeeded against PyPI, but the legitimacy seam still marked all candidate packages `SUS` because download telemetry was unavailable and several latest releases are very recent; planner tasks should add a human checkpoint before the first install group. [VERIFIED: local env] [VERIFIED: PyPI] [VERIFIED: package-legitimacy]

**Primary recommendation:** Plan Phase 1 as four implementation slices that match the roadmap: `01-01` toolchain bootstrap, `01-02` Sackmann manifest/raw snapshot ingestion, `01-03` schema validation plus quarantine rules, and `01-04` canonical ATP tables plus a durable v1 data-rules document. [CITED: .planning/ROADMAP.md]

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Python project skeleton, CLI entrypoints, logging, settings, and quality tooling | API / Backend | — | This is application-runtime behavior, not storage logic; the backend tier owns execution commands and typed boundaries. [CITED: .planning/ROADMAP.md] [CITED: AGENTS.md] |
| Sackmann source acquisition, commit pinning, checksum manifests, and attribution capture | API / Backend | Database / Storage | Fetching and manifest generation are backend concerns, but the manifest itself must persist in a durable store. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md] |
| Schema validation, ATP-only scope filters, and quarantine reason codes | API / Backend | Database / Storage | Validation runs in ingestion code, while accepted and rejected records need durable persistence for audit. [CITED: .planning/REQUIREMENTS.md] [CITED: https://github.com/JeffSackmann/tennis_atp] |
| Canonical player, tournament, match, ranking, and match-stat tables | Database / Storage | API / Backend | The core product of Phase 1 is a normalized, queryable storage contract that later backend logic consumes. [CITED: .planning/REQUIREMENTS.md] [CITED: .planning/research/ARCHITECTURE.md] |
| V1 data rules documentation for exclusions and edge cases | API / Backend | — | The backend tier owns the rule definitions because code, tests, and docs must agree on one source of truth. [CITED: .planning/ROADMAP.md] |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.x target; `python3.12` 3.12.4 available locally. [CITED: AGENTS.md] [VERIFIED: local env] | Phase 1 runtime | Matches the project’s locked runtime target and is already present on this machine, so Phase 1 can pin 3.12 immediately without waiting on a new interpreter install. [CITED: AGENTS.md] [VERIFIED: local env] |
| `uv` | 0.11.21. [VERIFIED: PyPI] | Dependency locking, env creation, command runner | Official docs position `uv` as a single tool replacing `pip`, `pip-tools`, `pipx`, `poetry`, `pyenv`, `twine`, and `virtualenv`, with a universal lockfile and project init flow. [CITED: https://docs.astral.sh/uv/] |
| `polars` | 1.41.2. [VERIFIED: PyPI] | CSV ingestion, schema enforcement, derived-table transforms | The docs expose lazy execution, schema, CSV, and Parquet workflows, which aligns with Phase 1’s need for large-file ingestion plus explicit contracts. [CITED: https://docs.pola.rs/] |
| `pyarrow` | 24.0.0. [VERIFIED: PyPI] | Parquet interoperability | The project stack already treats Parquet as the intermediate contract, and Arrow is the standard Python bridge for that format. [CITED: AGENTS.md] |
| `duckdb` | 1.5.3. [VERIFIED: PyPI] | Local analytical storage/query engine | DuckDB 1.5 documents direct Parquet read/write support, which lets Phase 1 persist canonical tables in Parquet while querying them locally without adding a server. [CITED: https://duckdb.org/docs/current/data/parquet/overview.html] |
| `pydantic` | 2.13.4. [VERIFIED: PyPI] | Typed DTOs for manifests, canonical IDs, and config boundaries | The project stack already standardizes on Pydantic for typed validation, which is the right place to freeze manifest and table contracts early. [CITED: AGENTS.md] |
| `pydantic-settings` | 2.14.1. [VERIFIED: PyPI] | Config loading from env and `pyproject.toml` | Official docs show `BaseSettings` plus `PyprojectTomlConfigSettingsSource`, which is a good fit for default project config without hand-rolled loaders. [CITED: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typer` | 0.26.7. [VERIFIED: PyPI] | CLI commands like `ingest`, `validate`, and `build-canonical` | Use for Phase 1 operator workflows once the package skeleton exists; the project stack already chose Typer for CLI surfaces. [CITED: AGENTS.md] |
| `rich` | 15.0.0. [VERIFIED: PyPI] | Inspectable terminal tables for manifests/quarantine summaries | Use for local audit outputs and phase diagnostics; it is helpful but not a blocker for the first schema pass. [CITED: AGENTS.md] |
| `pytest` | 9.1.0. [VERIFIED: PyPI] | Unit and integration tests | Use from Wave 0 onward because Phase 1 has critical logic around schema validation, filters, and stable IDs. [CITED: AGENTS.md] [CITED: https://docs.pytest.org/en/stable/] |
| `ruff` | 0.15.17. [VERIFIED: PyPI] | Linting and formatting | Use as the single fast lint/format gate; Ruff describes itself as an extremely fast Python linter and formatter. [CITED: https://docs.astral.sh/ruff/] |
| `mypy` | 2.1.0. [VERIFIED: PyPI] | Static typing enforcement | Use for manifests, DTOs, and repository interfaces once the source tree exists; the project stack requires strict typing for project code. [CITED: AGENTS.md] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `uv` | `venv` + `pip` + `pip-tools` | This works, but it recreates the multi-tool workflow that the project has already standardized away from. [CITED: AGENTS.md] [CITED: https://docs.astral.sh/uv/] |
| `polars` | `pandas`-only ingestion | `pandas` is still useful later at the edges, but Phase 1 benefits from Polars’ lazy and schema-oriented ingestion model. [CITED: AGENTS.md] [CITED: https://docs.pola.rs/] |
| `duckdb` | PostgreSQL from day one | PostgreSQL adds operational work before the project has any serving workload; local analytical storage is enough for the canonical layer. [CITED: AGENTS.md] |
| `pydantic-settings` | Ad hoc `os.environ` parsing | Manual parsing scatters config rules across modules and weakens type guarantees. [CITED: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/] |

**Installation:**
```bash
python3.12 -m pip install uv
uv python pin 3.12
uv init --package
uv add polars pyarrow duckdb pydantic pydantic-settings typer rich
uv add --dev pytest ruff mypy
```

**Version verification:** Verified against the live PyPI index on 2026-06-16 with `python3 -m pip index versions <package>`. [VERIFIED: PyPI]

## Package Legitimacy Audit

> Required because Phase 1 installs external packages. The seam was run on 2026-06-16. Every package remained `SUS` because download telemetry was unavailable, and several latest releases are very recent; none were removed as `SLOP`. Registry existence and current versions were still verified independently against PyPI. [VERIFIED: package-legitimacy] [VERIFIED: PyPI]

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| `uv` | PyPI [VERIFIED: PyPI] | latest release 5d ago. [VERIFIED: package-legitimacy] | unknown in seam. [VERIFIED: package-legitimacy] | `https://pypi.org/project/uv/` [VERIFIED: package-legitimacy] | `SUS` [VERIFIED: package-legitimacy] | Flagged: add `checkpoint:human-verify` before the first toolchain install. |
| `polars` | PyPI [VERIFIED: PyPI] | latest release 18d ago. [VERIFIED: package-legitimacy] | unknown in seam. [VERIFIED: package-legitimacy] | `https://www.pola.rs/` [VERIFIED: package-legitimacy] | `SUS` [VERIFIED: package-legitimacy] | Flagged: install only after the same human checkpoint. |
| `pyarrow` | PyPI [VERIFIED: PyPI] | latest release 56d ago. [VERIFIED: package-legitimacy] | unknown in seam. [VERIFIED: package-legitimacy] | `https://arrow.apache.org/` [VERIFIED: package-legitimacy] | `SUS` [VERIFIED: package-legitimacy] | Flagged: install only after the same human checkpoint. |
| `duckdb` | PyPI [VERIFIED: PyPI] | latest release 27d ago. [VERIFIED: package-legitimacy] | unknown in seam. [VERIFIED: package-legitimacy] | `https://github.com/duckdb/duckdb-python` [VERIFIED: package-legitimacy] | `SUS` [VERIFIED: package-legitimacy] | Flagged: install only after the same human checkpoint. |
| `pydantic` | PyPI [VERIFIED: PyPI] | latest release 41d ago. [VERIFIED: package-legitimacy] | unknown in seam. [VERIFIED: package-legitimacy] | `https://github.com/pydantic/pydantic` [VERIFIED: package-legitimacy] | `SUS` [VERIFIED: package-legitimacy] | Flagged: install only after the same human checkpoint. |
| `pydantic-settings` | PyPI [VERIFIED: PyPI] | latest release 39d ago. [VERIFIED: package-legitimacy] | unknown in seam. [VERIFIED: package-legitimacy] | `https://github.com/pydantic/pydantic-settings` [VERIFIED: package-legitimacy] | `SUS` [VERIFIED: package-legitimacy] | Flagged: install only after the same human checkpoint. |
| `typer` | PyPI [VERIFIED: PyPI] | latest release 13d ago. [VERIFIED: package-legitimacy] | unknown in seam. [VERIFIED: package-legitimacy] | `https://github.com/fastapi/typer` [VERIFIED: package-legitimacy] | `SUS` [VERIFIED: package-legitimacy] | Flagged: install only after the same human checkpoint. |
| `rich` | PyPI [VERIFIED: PyPI] | latest release 65d ago. [VERIFIED: package-legitimacy] | unknown in seam. [VERIFIED: package-legitimacy] | `https://github.com/Textualize/rich` [VERIFIED: package-legitimacy] | `SUS` [VERIFIED: package-legitimacy] | Flagged: install only after the same human checkpoint. |
| `pytest` | PyPI [VERIFIED: PyPI] | latest release 3d ago. [VERIFIED: package-legitimacy] | unknown in seam. [VERIFIED: package-legitimacy] | `https://github.com/pytest-dev/pytest` [VERIFIED: package-legitimacy] | `SUS` [VERIFIED: package-legitimacy] | Flagged: install only after the same human checkpoint. |
| `ruff` | PyPI [VERIFIED: PyPI] | latest release 5d ago. [VERIFIED: package-legitimacy] | unknown in seam. [VERIFIED: package-legitimacy] | `https://docs.astral.sh/ruff` [VERIFIED: package-legitimacy] | `SUS` [VERIFIED: package-legitimacy] | Flagged: install only after the same human checkpoint. |
| `mypy` | PyPI [VERIFIED: PyPI] | latest release 36d ago. [VERIFIED: package-legitimacy] | unknown in seam. [VERIFIED: package-legitimacy] | `https://www.mypy-lang.org/` [VERIFIED: package-legitimacy] | `SUS` [VERIFIED: package-legitimacy] | Flagged: install only after the same human checkpoint. |

**Packages removed due to `SLOP` verdict:** none. [VERIFIED: package-legitimacy]
**Packages flagged as suspicious `SUS`:** `uv`, `polars`, `pyarrow`, `duckdb`, `pydantic`, `pydantic-settings`, `typer`, `rich`, `pytest`, `ruff`, `mypy`. The planner should add one explicit `checkpoint:human-verify` task before the first dependency installation step. [VERIFIED: package-legitimacy]

## Architecture Patterns

### System Architecture Diagram

```text
Jeff Sackmann repo @ pinned commit
        |
        v
immutable raw snapshot directory
        |
        v
source manifest + checksums + attribution
        |
        v
schema validators
        |
        +--> quarantine tables/files (qual/chall, futures, doubles, failed schema, excluded match types)
        |
        v
ATP-only normalization
        |
        v
canonical players / tournaments / matches / rankings / match_stats
        |
        v
v1 data-rules document + test suite
```

The key planning rule is that raw data and canonical data are separate persistence layers, and quarantine is a first-class output rather than an exception path. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md] [CITED: .planning/research/ARCHITECTURE.md]

### Recommended Project Structure

```text
src/tennisprediction/
├── cli.py                    # Typer commands for ingest/validate/build
├── config/
│   └── settings.py           # Pydantic settings and path/config contracts
├── ingest/
│   ├── sackmann.py           # source fetch/load entrypoints
│   ├── manifests.py          # commit/checksum/license metadata
│   ├── schemas.py            # expected raw column contracts
│   └── scope_rules.py        # ATP-only filters and quarantine reasons
├── domain/
│   ├── players.py            # canonical player contracts
│   ├── tournaments.py        # canonical tournament contracts
│   ├── matches.py            # canonical match contracts
│   ├── rankings.py           # canonical ranking contracts
│   └── match_stats.py        # canonical stat contracts
└── storage/
    ├── duckdb.py             # local analytical connection helpers
    └── parquet.py            # canonical path conventions
tests/
├── unit/
└── integration/
docs/
└── phase1-data-rules.md
```

This structure is a phase-specific reduction of the project’s broader recommended layout and keeps Phase 1 responsibilities isolated from later feature/model code. [CITED: .planning/research/STACK.md] [ASSUMED]

### Pattern 1: Immutable Raw Snapshot + Manifest
**What:** Fetch or load Sackmann files into a commit-scoped raw directory, then record checksum, file path, commit SHA, and attribution before any normalization runs. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
**When to use:** Every time upstream data enters the project, including local file loads that bypass a network fetch. [CITED: .planning/REQUIREMENTS.md]
**Example:**
```python
manifest = SourceSnapshot(
    source_repo="JeffSackmann/tennis_atp",
    commit_sha=commit_sha,
    file_name=file_name,
    sha256=file_sha256,
    license_name="CC BY-NC-SA 4.0",
)
```

### Pattern 2: Validate, Then Normalize
**What:** Separate raw-file acceptance from canonical table construction. Schema checks and scope checks run first; only accepted rows reach canonical tables. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
**When to use:** For players, rankings, matches, tournaments, and MatchStats. [CITED: .planning/REQUIREMENTS.md]
**Example:**
```python
if not schema_ok or not scope_ok:
    write_quarantine(raw_row, reason_code)
else:
    write_canonical(normalize_row(raw_row))
```

### Pattern 3: Canonical Tables Preserve Lineage
**What:** Every canonical row should retain the source file, source row handle, source commit, and canonicalization rule version used to produce it. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
**When to use:** Always; lineage is not optional metadata in this project. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
**Example:**
```python
canonical_match = {
    "canonical_match_id": match_id,
    "source_file": source_file,
    "source_commit_sha": commit_sha,
    "source_row_number": row_number,
    "rule_version": "phase1-v1",
}
```

### Anti-Patterns to Avoid
- **Mutating raw snapshots in place:** Raw files should never be “cleaned” in place; write derived outputs separately. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
- **Using file globbing as scope control:** Sackmann’s repo contains futures and doubles files; file names alone are not enough without documented inclusion rules. [CITED: https://github.com/JeffSackmann/tennis_atp]
- **Treating rankings and MatchStats as downstream-ready features:** Phase 1 should store them faithfully with provenance and defer feature semantics to later phases. [CITED: https://github.com/JeffSackmann/tennis_atp]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Python env + lock management | Custom shell wrappers around `venv`, `pip`, and `requirements.txt` | `uv` | The project already standardized on `uv`, and the official docs cover project init, locking, and running commands in one tool. [CITED: AGENTS.md] [CITED: https://docs.astral.sh/uv/] |
| Config loading | Manual `os.environ` parsing scattered across modules | `pydantic-settings` | `BaseSettings` plus `PyprojectTomlConfigSettingsSource` gives typed defaults and environment overrides without bespoke parsing code. [CITED: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/] |
| CSV contract validation | Ad hoc row-by-row string checks | Polars schema-aware ingestion + typed DTO validation | Phase 1 needs structured acceptance/rejection and reproducible coercion behavior, not scattered imperative parsing. [CITED: https://docs.pola.rs/] [CITED: AGENTS.md] |
| Local analytical cache | Homemade CSV index or JSON sidecar query layer | DuckDB over Parquet | DuckDB already reads and writes Parquet efficiently, which is simpler and safer than building a custom query/cache layer. [CITED: https://duckdb.org/docs/current/data/parquet/overview.html] |

**Key insight:** Phase 1 should hand-roll domain rules, not infrastructure primitives. The project’s distinct value is ATP-only canonicalization and lineage policy, not package management, settings parsing, or local query engines. [CITED: AGENTS.md] [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]

## Common Pitfalls

### Pitfall 1: Accidentally Canonicalizing Out-of-Scope File Families
**What goes wrong:** Qual/challenger, futures, or doubles data leaks into the canonical ATP-only store because the upstream repo publishes those files alongside tour-level main draw files. [CITED: https://github.com/JeffSackmann/tennis_atp]
**Why it happens:** The repository layout is broad by design, while the project scope is narrow. [CITED: AGENTS.md] [CITED: https://github.com/JeffSackmann/tennis_atp]
**How to avoid:** Put file-family filters and row-level quarantine reason codes into Phase 1, not Phase 2. [CITED: .planning/ROADMAP.md]
**Warning signs:** Any accepted canonical row originating from `qual_chall`, `futures`, or doubles files. [CITED: https://github.com/JeffSackmann/tennis_atp]

### Pitfall 2: Treating MatchStats as Precomputed Percentages
**What goes wrong:** Downstream code assumes stat columns are percentages, then derives wrong canonical fields or silently fills missing stats with zeros. [CITED: https://github.com/JeffSackmann/tennis_atp]
**Why it happens:** Sackmann explicitly notes the stats are integer totals and some tour-level matches are missing stats. [CITED: https://github.com/JeffSackmann/tennis_atp]
**How to avoid:** Canonicalize raw stat totals plus missingness flags now; defer percentage derivations to a later feature phase. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
**Warning signs:** Canonical columns named like `first_serve_pct` in Phase 1, or missing stat rows converted to zero-valued performance metrics. [CITED: https://github.com/JeffSackmann/tennis_atp]

### Pitfall 3: Losing Reproducibility Through Weak Lineage
**What goes wrong:** Raw files are fetched from a branch tip or copied locally without a durable manifest, so later rebuilds cannot prove what data produced a canonical table. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
**Why it happens:** Teams often treat historical CSVs as static input rather than versioned upstream dependencies. [ASSUMED]
**How to avoid:** Freeze commit SHA, checksum, file path, ingest timestamp, attribution, and rule version in a manifest table before normalization. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
**Warning signs:** Canonical tables exist but no source manifest row can be joined back to them. [CITED: .planning/REQUIREMENTS.md]

### Pitfall 4: Smuggling Downstream Semantics Into Phase 1
**What goes wrong:** The phase starts deciding feature-time semantics for rankings, stats, or match ordering instead of storing faithful canonical inputs plus provenance. [CITED: .planning/ROADMAP.md]
**Why it happens:** Match rows already contain rankings and ages, which makes it tempting to treat them as feature-ready. [CITED: https://github.com/JeffSackmann/tennis_atp]
**How to avoid:** Keep Phase 1 focused on faithful raw-to-canonical contracts and documented exclusions; Phase 2 should own point-in-time feature semantics. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
**Warning signs:** Phase 1 plan items talk about Elo, recent form, rolling stats, or calibration. [CITED: .planning/ROADMAP.md]

## Code Examples

Verified patterns from official sources:

### Bootstrap `uv` and Pin Python
```bash
python3.12 -m pip install uv
uv init --package
uv python pin 3.12
```
Source: `uv` docs show project initialization, lockfile-oriented project management, and Python version management. [CITED: https://docs.astral.sh/uv/]

### Load Settings From `pyproject.toml`
```python
from pydantic_settings import (
    BaseSettings,
    PyprojectTomlConfigSettingsSource,
    PydanticBaseSettingsSource,
)


class Settings(BaseSettings):
    data_root: str

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (PyprojectTomlConfigSettingsSource(settings_cls), env_settings)
```
Source: adapted from the official `pydantic-settings` documentation for `PyprojectTomlConfigSettingsSource`. [CITED: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/]

### Write Canonical Tables to Parquet
```sql
COPY canonical_matches
TO 'data/canonical/matches.parquet'
(FORMAT parquet, COMPRESSION zstd);
```
Source: DuckDB documents `COPY ... (FORMAT parquet)` for Parquet output. [CITED: https://duckdb.org/docs/current/data/parquet/overview.html]

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `venv` + `pip` + requirements files | `uv` + lockfile-centered workflow | project stack research on 2026-06-16. [CITED: AGENTS.md] | One tool owns init, lock, install, and run flows, which simplifies Phase 1 bootstrap. [CITED: https://docs.astral.sh/uv/] |
| Pandas-first ingestion for everything | Polars lazy ingestion + Parquet + DuckDB local querying | project stack research on 2026-06-16. [CITED: AGENTS.md] | Better fit for repeatable large historical ingests with explicit schemas and rebuildable outputs. [CITED: https://docs.pola.rs/] [CITED: https://duckdb.org/docs/current/data/parquet/overview.html] |
| “Clean the CSV and move on” | immutable raw snapshots + manifests + canonical lineage | locked Phase 1 decisions on 2026-06-16. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md] | Makes every later feature/model artifact traceable to exact upstream files and rules. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md] |

**Deprecated/outdated:**
- Branch-tip source pinning is outdated for this project; the phase explicitly requires commit-SHA pinning. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
- Treating Sackmann match stats as already-derived percentages is outdated for this project’s canonical layer; keep integer totals plus flags instead. [CITED: https://github.com/JeffSackmann/tennis_atp]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The proposed on-disk project structure (`src/tennisprediction/...`, `docs/phase1-data-rules.md`) is the best fit for this repo even though no source tree exists yet. [ASSUMED] | Architecture Patterns | Low: planner may choose different file paths, but responsibility boundaries should remain the same. |
| A2 | Same human verification checkpoint can cover the whole first dependency install group instead of one checkpoint per package. [ASSUMED] | Package Legitimacy Audit | Medium: if the workflow requires per-package approval, the plan will need finer-grained checkpoints. |
| A3 | Phase 1 should quarantine Davis Cup rows unless the planner/user explicitly reclassifies them. [ASSUMED] | Open Questions | Medium: a different inclusion rule changes scope filters and canonical counts. |

## Open Questions

1. **How should tour-level Davis Cup rows be treated in the ATP-only canonical store?**
   - What we know: Sackmann states that Davis Cup matches are included in tour-level files, and many older Davis Cup rows lack stats. [CITED: https://github.com/JeffSackmann/tennis_atp]
   - What's unclear: The Phase 1 context locks qualifiers, retirements, walkovers, and incomplete matches, but it does not explicitly classify Davis Cup. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
   - Recommendation: Default to quarantine in `01-03` and require an explicit rule in the Phase 1 data-rules document. [ASSUMED]

2. **Should Phase 1 expose a modern-era readiness flag for downstream modeling?**
   - What we know: Rankings are mostly complete from 1985 onward, 1982 is missing, and 1973-1984 are intermittent. [CITED: https://github.com/JeffSackmann/tennis_atp]
   - What's unclear: Whether later phases will train on all history or only on eras with acceptable ranking/stat coverage. [CITED: .planning/STATE.md]
   - Recommendation: Store coverage flags in canonical tables now, then let Phase 2/3 decide the modeling cutoff. [ASSUMED]

3. **What deterministic synthetic ID contract should canonical tournaments and matches use?**
   - What we know: Source-derived IDs should be reused where available, and synthetic IDs are allowed for tournaments, matches, and derived records. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]
   - What's unclear: Whether the planner wants hash-based IDs, compound natural keys, or generated surrogate keys persisted in DuckDB/Parquet. [ASSUMED]
   - Recommendation: Freeze one deterministic format in `01-04` and make it part of the canonical contract tests. [ASSUMED]

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `python3.12` | runtime target, `uv` bootstrap | ✓ [VERIFIED: local env] | 3.12.4 [VERIFIED: local env] | — |
| `python3` | host Python | ✓ [VERIFIED: local env] | 3.14.0 [VERIFIED: local env] | do not target 3.14 for project pinning; use `python3.12`. [CITED: AGENTS.md] |
| `uv` | env creation, lockfile, command runner | ✗ [VERIFIED: local env] | — | bootstrap with `python3.12 -m pip install uv`. [CITED: https://docs.astral.sh/uv/] |
| `pytest` | validation architecture | ✗ [VERIFIED: local env] | — | install via `uv add --dev pytest`. [CITED: AGENTS.md] |
| `ruff` | lint/format gate | ✗ [VERIFIED: local env] | — | install via `uv add --dev ruff`. [CITED: AGENTS.md] |
| `mypy` | static typing gate | ✗ [VERIFIED: local env] | — | install via `uv add --dev mypy`. [CITED: AGENTS.md] |
| `git` | commit pinning and source manifests | ✓ [VERIFIED: local env] | 2.52.0 [VERIFIED: local env] | — |

**Missing dependencies with no fallback:**
- none. [VERIFIED: local env]

**Missing dependencies with fallback:**
- `uv`, `pytest`, `ruff`, and `mypy` are absent but can be installed during `01-01`. [VERIFIED: local env] [CITED: AGENTS.md]

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` 9.1.x target. [CITED: AGENTS.md] [VERIFIED: PyPI] |
| Config file | none — create in Wave 0. [VERIFIED: repository scan] |
| Quick run command | `uv run pytest tests/unit -q` after bootstrap. [CITED: AGENTS.md] [ASSUMED] |
| Full suite command | `uv run pytest -q` after bootstrap. [CITED: AGENTS.md] [ASSUMED] |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FND-01 | toolchain boots, config loads, CLI starts | smoke | `uv run pytest tests/unit/test_bootstrap.py -q` | ❌ Wave 0 |
| FND-02 | source manifest records commit/checksum/license metadata | unit | `uv run pytest tests/unit/test_source_manifest.py -q` | ❌ Wave 0 |
| FND-03 | schema validation accepts expected files and rejects drift | unit | `uv run pytest tests/unit/test_sackmann_schema.py -q` | ❌ Wave 0 |
| FND-04 | canonical tables preserve stable IDs and lineage | integration | `uv run pytest tests/integration/test_canonical_tables.py -q` | ❌ Wave 0 |
| FND-05 | out-of-scope tours/match types are quarantined or rejected | unit | `uv run pytest tests/unit/test_scope_rules.py -q` | ❌ Wave 0 |
| FND-06 | v1 data-rules document matches implemented exclusion behavior | integration | `uv run pytest tests/integration/test_phase1_data_rules.py -q` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/unit -q` once the framework exists. [ASSUMED]
- **Per wave merge:** `uv run pytest -q` plus `uv run ruff check .` and `uv run mypy src`. [CITED: AGENTS.md] [ASSUMED]
- **Phase gate:** full suite green and the Phase 1 data-rules document reviewed for rule/code parity. [CITED: .planning/ROADMAP.md] [ASSUMED]

### Wave 0 Gaps

- [ ] `pyproject.toml` — define project metadata, tool config, and `uv` workflow. [VERIFIED: repository scan]
- [ ] `tests/unit/test_bootstrap.py` — covers FND-01. [ASSUMED]
- [ ] `tests/unit/test_source_manifest.py` — covers FND-02. [ASSUMED]
- [ ] `tests/unit/test_sackmann_schema.py` — covers FND-03. [ASSUMED]
- [ ] `tests/integration/test_canonical_tables.py` — covers FND-04. [ASSUMED]
- [ ] `tests/unit/test_scope_rules.py` — covers FND-05. [ASSUMED]
- [ ] `tests/integration/test_phase1_data_rules.py` — covers FND-06. [ASSUMED]
- [ ] Framework install: `python3.12 -m pip install uv && uv add --dev pytest ruff mypy` — current env is missing all four tools. [VERIFIED: local env] [CITED: AGENTS.md]

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Phase 1 has no user or service auth surface yet. [CITED: .planning/ROADMAP.md] |
| V3 Session Management | no | Phase 1 is batch/CLI data ingestion, not a session-based app. [CITED: .planning/ROADMAP.md] |
| V4 Access Control | no | Access-control logic is not in scope for local canonicalization work. [CITED: .planning/ROADMAP.md] |
| V5 Input Validation | yes | Use Polars schema validation, quarantine paths, and typed Pydantic DTOs at manifest/canonical boundaries. [CITED: https://docs.pola.rs/] [CITED: AGENTS.md] |
| V6 Cryptography | no | Phase 1 needs checksums for reproducibility, not an application cryptography feature. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md] [ASSUMED] |

### Known Threat Patterns for this Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Upstream schema drift or malformed CSV accepted as canonical | Tampering | Fail closed on schema mismatch and route rejected rows/files to quarantine with reason codes. [CITED: .planning/REQUIREMENTS.md] [CITED: https://docs.pola.rs/] |
| Raw snapshots overwritten or edited after ingest | Tampering | Use commit-scoped immutable raw directories and store checksums/manifests before normalization. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md] |
| Secrets accidentally embedded in committed config/manifests | Information Disclosure | Keep env-specific values in `pydantic-settings` env sources; manifests record lineage, not secrets. [CITED: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/] [ASSUMED] |
| Ambiguous source provenance prevents audit | Repudiation | Add source commit, file, row handle, and rule version to canonical tables and docs. [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md] |

## Sources

### Primary (HIGH confidence)
- `.planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md` - locked decisions and scope boundaries for Phase 1.
- `.planning/REQUIREMENTS.md` - FND-01 through FND-06 requirement text.
- `.planning/ROADMAP.md` - Phase 1 success criteria and plan decomposition.
- `AGENTS.md` - project stack, constraints, and workflow rules.
- Jeff Sackmann `tennis_atp` README - file families, ranking coverage, MatchStats semantics, and doubles/Davis Cup notes: https://github.com/JeffSackmann/tennis_atp
- `uv` docs - single-tool workflow, lockfile, and init/pin commands: https://docs.astral.sh/uv/
- Polars docs - lazy execution, schema, CSV, and Parquet coverage: https://docs.pola.rs/
- DuckDB Parquet docs - direct Parquet read/write patterns: https://duckdb.org/docs/current/data/parquet/overview.html
- `pydantic-settings` docs - `BaseSettings` and `PyprojectTomlConfigSettingsSource`: https://pydantic.dev/docs/validation/latest/concepts/pydantic_settings/

### Secondary (MEDIUM confidence)
- `.planning/research/STACK.md` - standard stack and layout recommendations.
- `.planning/research/ARCHITECTURE.md` - append-oriented persistence boundaries and build order.
- `.planning/research/PITFALLS.md` - domain-specific failure modes that reinforce Phase 1 guardrails.
- `pytest` docs - test framework reference surface: https://docs.pytest.org/en/stable/
- `Ruff` docs - lint/format tool positioning: https://docs.astral.sh/ruff/

### Tertiary (LOW confidence)
- none.

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM - versions were verified live, but the legitimacy seam conservatively flagged every package `SUS`, so the install plan needs a human checkpoint. [VERIFIED: PyPI] [VERIFIED: package-legitimacy]
- Architecture: MEDIUM - storage boundaries and phase split are well supported by local project docs, but Davis Cup handling and final synthetic ID shape still need explicit planning decisions. [CITED: .planning/ROADMAP.md] [ASSUMED]
- Pitfalls: HIGH - the major ingestion risks are directly grounded in Sackmann’s own README and the locked Phase 1 context. [CITED: https://github.com/JeffSackmann/tennis_atp] [CITED: .planning/phases/01-foundation-and-atp-data-contracts/01-CONTEXT.md]

**Research date:** 2026-06-16  
**Valid until:** 2026-06-23
