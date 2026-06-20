# Phase 05: Kalshi Read-Only Market Integration - Pattern Map

**Mapped:** 2026-06-20  
**Files analyzed:** 8  
**Analogs found:** 8 / 8

## File Classification

| Planned File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/tennisprediction/kalshi/client.py` | service | event-driven | `src/tennisprediction/modeling/registry.py` | partial |
| `src/tennisprediction/kalshi/schemas.py` | model | transform | `src/tennisprediction/modeling/schemas.py` | exact |
| `src/tennisprediction/kalshi/storage.py` | utility | file-I/O | `src/tennisprediction/storage/duckdb.py` | exact |
| `src/tennisprediction/kalshi/jobs.py` | service | event-driven | `src/tennisprediction/features/runner.py` | data-flow-match |
| `src/tennisprediction/cli.py` | service | command dispatch | `src/tennisprediction/cli.py` | exact |
| `tests/unit/test_kalshi_client.py` | test | event-driven | `tests/unit/test_modeling_registry.py` | role-match |
| `tests/unit/test_kalshi_storage.py` | test | file-I/O | `tests/unit/test_modeling_reports.py` | role-match |
| `tests/unit/test_kalshi_jobs.py` | test | event-driven | `tests/unit/test_feature_runner.py` | role-match |

## Pattern Assignments

### `src/tennisprediction/kalshi/client.py`

**Analog:** [src/tennisprediction/modeling/registry.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/registry.py:29)

**Guarded external-access pattern** ([registry.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/registry.py:101)):
```python
artifact_dir = Settings._resolve_repo_path(Path(path))
...
if sha256_file(raw_model_path) != manifest.raw_model_sha256:
    raise ValueError("raw model checksum mismatch")
```

**Reuse for Phase 05:** keep the Kalshi client as a guarded boundary with explicit configuration validation, request-signing helpers, and no leakage of transport-specific response objects into business logic.

### `src/tennisprediction/kalshi/schemas.py`

**Analog:** [src/tennisprediction/modeling/schemas.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/schemas.py:1)

**Dataclass-first contract pattern**:
```python
@dataclass(frozen=True)
class CalibratedPredictionRow:
    ...
```

**Reuse for Phase 05:** define frozen DTOs for markets, market detail, yes/no orderbooks, page envelopes, request metadata, and snapshot records. Keep raw payload lineage explicit so later phases can prove which HTTP response generated a given snapshot row.

### `src/tennisprediction/kalshi/storage.py`

**Analog:** [src/tennisprediction/storage/duckdb.py](/Users/andrewlay/tennisprediction/src/tennisprediction/storage/duckdb.py:1)

**Whole-table replacement pattern**:
```python
def _replace_table(...):
    connection.execute(f"drop table if exists {table_name}")
    connection.execute(ddl)
    ...
```

**Reuse for Phase 05:** persist snapshot batches as explicit tabular surfaces with stable schema and repo-local paths. This keeps request metadata queryable and avoids ad hoc JSON parsing in later market-mapping code.

### `src/tennisprediction/kalshi/jobs.py`

**Analog:** [src/tennisprediction/features/runner.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/runner.py:136)

**Deterministic loop shape**:
```python
for cohort in build_match_cohorts(matches):
    for match in cohort:
        ...
```

**Reuse for Phase 05:** keep market pagination and snapshot collection deterministic and ordered. One run should consume one configured query surface, record the request metadata, and emit snapshots without hidden side effects.

### `src/tennisprediction/cli.py`

**Analog:** [src/tennisprediction/cli.py](/Users/andrewlay/tennisprediction/src/tennisprediction/cli.py:1)

**Minimal Typer command pattern**:
```python
app = typer.Typer(help="ATP-only tennis prediction project CLI.")
```

**Reuse for Phase 05:** add only the snapshot-collection command(s) needed for the read-only workflow. Do not add order-placement, order-staging, or trade-execution commands.

## Shared Patterns

### Configuration boundary
**Source:** [src/tennisprediction/config.py](/Users/andrewlay/tennisprediction/src/tennisprediction/config.py:1)
Use `BaseSettings` for Kalshi credentials, environment, and endpoint selection. Keep every filesystem path repo-local and validated through the existing settings pattern.

### Thin persistence boundary
**Source:** [src/tennisprediction/modeling/reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/reports.py:1)
Keep persistence thin: build rows in memory, then hand them to a small writer. Avoid spreading write logic across the client and job layers.

### Read-only job boundary
**Source:** [src/tennisprediction/features/runner.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/runner.py:136)
Keep one top-level orchestration loop for snapshot collection, with request/response bookkeeping attached to every iteration.

### Transport-to-domain mapping
**Source:** [src/tennisprediction/modeling/schemas.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/schemas.py:1)
Normalize external payloads immediately. Later code should depend on project DTOs, not raw response dicts.

## Planner Notes

- Prefer `src/tennisprediction/kalshi/` as the new package root.
- Keep read access explicit for `markets`, `market detail`, `orderbook`, and optional historical-market reads.
- Persist both request metadata and response provenance for every snapshot.
- Maintain a hard allowlist for read endpoints so no write path is available in Phase 05.

