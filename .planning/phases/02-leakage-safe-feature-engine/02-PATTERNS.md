# Phase 02: leakage-safe-feature-engine - Pattern Map

**Mapped:** 2026-06-16
**Files analyzed:** 13
**Analogs found:** 13 / 13

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/tennisprediction/features/__init__.py` | config | transform | `src/tennisprediction/domain/__init__.py` | exact |
| `src/tennisprediction/features/schemas.py` | model | transform | `src/tennisprediction/domain/models.py` | exact |
| `src/tennisprediction/features/ordering.py` | utility | transform | `src/tennisprediction/domain/normalization.py` | role-match |
| `src/tennisprediction/features/rankings.py` | utility | request-response | `src/tennisprediction/ingestion/schemas.py` | role-match |
| `src/tennisprediction/features/state.py` | utility | event-driven | `src/tennisprediction/domain/normalization.py` | data-flow-match |
| `src/tennisprediction/features/runner.py` | service | event-driven | `src/tennisprediction/domain/normalization.py` | data-flow-match |
| `src/tennisprediction/features/differential.py` | utility | transform | `src/tennisprediction/domain/normalization.py` | role-match |
| `src/tennisprediction/features/persistence.py` | utility | file-I/O | `src/tennisprediction/storage/duckdb.py` | exact |
| `tests/unit/test_feature_runner.py` | test | event-driven | `tests/unit/test_quarantine.py` | role-match |
| `tests/unit/test_feature_ordering.py` | test | transform | `tests/unit/test_validation.py` | role-match |
| `tests/unit/test_feature_rankings.py` | test | request-response | `tests/unit/test_validation.py` | role-match |
| `tests/unit/test_feature_state.py` | test | event-driven | `tests/unit/test_quarantine.py` | role-match |
| `tests/unit/test_feature_differential.py` | test | transform | `tests/unit/test_validation.py` | role-match |
| `tests/unit/test_feature_leakage.py` | test | event-driven | `tests/unit/test_quarantine.py` | role-match |
| `tests/unit/test_feature_persistence.py` | test | file-I/O | `tests/unit/test_validation.py` | role-match |

## Pattern Assignments

### `src/tennisprediction/features/__init__.py` (config, transform)

**Why this file exists:** The research module split explicitly proposes a feature package export surface. Source: `.planning/phases/02-leakage-safe-feature-engine/02-RESEARCH.md:188-196`.

**Analog:** `src/tennisprediction/domain/__init__.py`

**Package export pattern** ([src/tennisprediction/domain/__init__.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/__init__.py:1)):
```python
"""Canonical ATP domain contracts and normalization helpers."""

from tennisprediction.domain.ids import CanonicalIdFactory
from tennisprediction.domain.models import (
    CanonicalMatch,
    CanonicalMatchStat,
    CanonicalPlayer,
    CanonicalRanking,
    CanonicalSnapshot,
    CanonicalTournament,
    SourceLineage,
)
from tennisprediction.domain.normalization import normalize_snapshot

__all__ = [
    "CanonicalIdFactory",
    "CanonicalPlayer",
    "CanonicalTournament",
```

**Copy from this analog:**
- Module docstring on line 1.
- Absolute package imports, not relative imports.
- Explicit `__all__` export list.

---

### `src/tennisprediction/features/schemas.py` (model, transform)

**Why this file exists:** Phase decisions lock persisted player-side snapshots plus differential rows, with lineage and availability metadata. Source: `.planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md:22-34`.

**Analog:** `src/tennisprediction/domain/models.py`

**Dataclass contract pattern** ([src/tennisprediction/domain/models.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/models.py:1)):
```python
from __future__ import annotations

from dataclasses import dataclass

from tennisprediction.ingestion.validation import FileQuarantineRecord


@dataclass(frozen=True)
class SourceLineage:
    source_repo: str
    source_commit_sha: str
    source_file_path: str
    source_row_number: int
    source_snapshot_root: str
```

**Nested lineage pattern** ([src/tennisprediction/domain/models.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/models.py:38)):
```python
@dataclass(frozen=True)
class CanonicalMatch:
    canonical_match_id: str
    canonical_tournament_id: str
    winner_canonical_player_id: str
    loser_canonical_player_id: str
    source_tourney_id: str
    surface: str
    tourney_name: str
    tourney_level: str
    tourney_date: str
    round_name: str
    best_of: int
    score: str
    lineage: SourceLineage
```

**Copy from this analog:**
- `@dataclass(frozen=True)` for immutable contracts.
- Separate lineage object instead of flattened provenance fields in the model layer.
- Simple typed fields, including `int | None` where missingness is first-class.

---

### `src/tennisprediction/features/ordering.py` (utility, transform)

**Why this file exists:** D-01 through D-04 lock deterministic chronological ordering and same-round cohort behavior. Source: `.planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md:16-20`.

**Analog:** `src/tennisprediction/domain/normalization.py`

**Helper-first transform pattern** ([src/tennisprediction/domain/normalization.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/normalization.py:19)):
```python
def _build_lineage(
    validated_snapshot: ValidatedSnapshot, *, source_file_path: str, source_row_number: int
) -> SourceLineage:
    return SourceLineage(
        source_repo=validated_snapshot.manifest.source_repo,
        source_commit_sha=validated_snapshot.manifest.commit_sha,
        source_file_path=source_file_path,
        source_row_number=source_row_number,
        source_snapshot_root=str(validated_snapshot.manifest.snapshot_root),
    )


def _iter_rows(
    rows_by_file: dict[str, list[dict[str, str]]],
) -> Iterable[tuple[str, int, dict[str, str]]]:
    for source_file_path, rows in rows_by_file.items():
        for source_row_number, row in enumerate(rows, start=2):
            yield source_file_path, source_row_number, row
```

**Central orchestrator pattern** ([src/tennisprediction/domain/normalization.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/normalization.py:213)):
```python
def normalize_snapshot(validated_snapshot: ValidatedSnapshot) -> CanonicalSnapshot:
    partitioned = split_validated_snapshot(validated_snapshot)
    accepted_rows = partitioned.accepted_rows

    return CanonicalSnapshot(
        players=_normalize_players(validated_snapshot, accepted_rows),
        tournaments=_normalize_tournaments(validated_snapshot, accepted_rows),
        matches=_normalize_matches(validated_snapshot, accepted_rows),
        rankings=_normalize_rankings(validated_snapshot, accepted_rows),
        match_stats=_normalize_match_stats(validated_snapshot, accepted_rows),
        quarantined_rows=partitioned.quarantined_rows,
        quarantined_files=partitioned.quarantined_files,
    )
```

**Copy from this analog:**
- Keep ordering/cohort helpers private until a stable public API emerges.
- Derive deterministic outputs from explicitly passed input collections.
- Put the top-level orchestration function at the bottom after helper definitions.

---

### `src/tennisprediction/features/rankings.py` (utility, request-response)

**Why this file exists:** D-02 locks backward-looking ranking lookup only. Source: `.planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md:18`.

**Analog:** `src/tennisprediction/ingestion/schemas.py`

**Small pure-function utility pattern** ([src/tennisprediction/ingestion/schemas.py](/Users/andrewlay/tennisprediction/src/tennisprediction/ingestion/schemas.py:58)):
```python
def schema_for_file(relative_path: str | Path) -> RawSchema:
    name = Path(relative_path).name
    if name == "atp_players.csv":
        return RawPlayerSchema
    if name.startswith("atp_rankings"):
        return RawRankingSchema
    if name.startswith("atp_matches_"):
        return RawMatchSchema
    if name.startswith("atp_matchstats_"):
        return RawMatchStatSchema
    msg = f"no schema registered for {name}"
    raise KeyError(msg)
```

**Validation/error pattern** ([src/tennisprediction/ingestion/schemas.py](/Users/andrewlay/tennisprediction/src/tennisprediction/ingestion/schemas.py:72)):
```python
def validate_date_value(value: str, *, file_name: str, column: str) -> None:
    try:
        datetime.strptime(value, "%Y%m%d")
    except ValueError as exc:
        msg = f"{file_name}: column {column} must parse as YYYYMMDD date"
        raise ValueError(msg) from exc
```

**Copy from this analog:**
- Keep the module mostly pure functions with narrow typed arguments.
- Raise precise `KeyError` or `ValueError` with context-rich messages.
- Normalize lookup inputs at the top of each function before branching.

---

### `src/tennisprediction/features/state.py` (utility, event-driven)

**Why this file exists:** D-01, D-04, and D-11 require pre-match emission before updates plus auditable state transitions. Source: `.planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md:17-20,32-34`.

**Analog:** `src/tennisprediction/domain/normalization.py`

**Per-row builder pattern** ([src/tennisprediction/domain/normalization.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/normalization.py:105)):
```python
def _normalize_matches(
    validated_snapshot: ValidatedSnapshot, rows: dict[str, list[dict[str, str]]]
) -> list[CanonicalMatch]:
    matches: list[CanonicalMatch] = []
    for source_file_path, source_row_number, row in _iter_rows(rows):
        if not source_file_path.startswith("atp_matches_"):
            continue

        canonical_tournament_id = CanonicalIdFactory.tournament_id(
            source_tourney_id=row["tourney_id"],
            tourney_name=row["tourney_name"],
            tourney_date=row["tourney_date"],
        )
        winner_source_player_id = int(row["winner_id"])
        loser_source_player_id = int(row["loser_id"])
        matches.append(
```

**Optional/missing-value handling** ([src/tennisprediction/domain/normalization.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/normalization.py:188)):
```python
        def _optional_int(value: str) -> int | None:
            stripped = value.strip()
            return int(stripped) if stripped else None
```

**Copy from this analog:**
- Model state updates as explicit per-match transitions, not hidden vectorized side effects.
- Keep missingness explicit with helper coercers instead of defaulting to zero.
- Build typed output records inside the loop rather than mutating dicts in-place.

---

### `src/tennisprediction/features/runner.py` (service, event-driven)

**Why this file exists:** The phase boundary defines a chronological feature runner as the single source of truth for stateful tennis features. Source: `.planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md:9,33-34`.

**Analog:** `src/tennisprediction/domain/normalization.py`

**Top-level pipeline function pattern** ([src/tennisprediction/domain/normalization.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/normalization.py:213)):
```python
def normalize_snapshot(validated_snapshot: ValidatedSnapshot) -> CanonicalSnapshot:
    partitioned = split_validated_snapshot(validated_snapshot)
    accepted_rows = partitioned.accepted_rows

    return CanonicalSnapshot(
        players=_normalize_players(validated_snapshot, accepted_rows),
        tournaments=_normalize_tournaments(validated_snapshot, accepted_rows),
        matches=_normalize_matches(validated_snapshot, accepted_rows),
        rankings=_normalize_rankings(validated_snapshot, accepted_rows),
        match_stats=_normalize_match_stats(validated_snapshot, accepted_rows),
        quarantined_rows=partitioned.quarantined_rows,
        quarantined_files=partitioned.quarantined_files,
    )
```

**Input contract import pattern** ([src/tennisprediction/domain/normalization.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/normalization.py:5)):
```python
from tennisprediction.domain.ids import CanonicalIdFactory
from tennisprediction.domain.models import (
    CanonicalMatch,
    CanonicalMatchStat,
    CanonicalPlayer,
    CanonicalRanking,
    CanonicalSnapshot,
    CanonicalTournament,
    SourceLineage,
)
from tennisprediction.ingestion.quarantine import split_validated_snapshot
from tennisprediction.ingestion.validation import ValidatedSnapshot
```

**Copy from this analog:**
- Accept a single upstream contract and return a single downstream contract.
- Keep orchestration in one public function; delegate details to helpers/modules.
- Import typed dependencies from the package boundary rather than re-parsing raw input.

---

### `src/tennisprediction/features/differential.py` (utility, transform)

**Why this file exists:** D-06 requires persisted player-side snapshots and persisted differential rows, with the latter derived reproducibly from the former. Source: `.planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md:24`.

**Analog:** `src/tennisprediction/domain/normalization.py`

**Typed row-derivation pattern** ([src/tennisprediction/domain/normalization.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/normalization.py:151)):
```python
def _normalize_rankings(
    validated_snapshot: ValidatedSnapshot, rows: dict[str, list[dict[str, str]]]
) -> list[CanonicalRanking]:
    rankings: list[CanonicalRanking] = []
    for source_file_path, source_row_number, row in _iter_rows(rows):
        if not source_file_path.startswith("atp_rankings"):
            continue

        source_player_id = int(row["player"])
        rankings.append(
            CanonicalRanking(
```

**Copy from this analog:**
- Build derived rows in a dedicated function that returns typed objects.
- Use narrow loops over already-normalized inputs instead of mixing raw and derived concerns.
- Keep A/B orientation logic explicit in constructor fields.

---

### `src/tennisprediction/features/persistence.py` (utility, file-I/O)

**Why this file exists:** D-05 through D-07 and D-11 require persisted snapshots plus audit state history. Source: `.planning/phases/02-leakage-safe-feature-engine/02-CONTEXT.md:22-34`.

**Analog:** `src/tennisprediction/storage/duckdb.py`

**Flatten helper pattern** ([src/tennisprediction/storage/duckdb.py](/Users/andrewlay/tennisprediction/src/tennisprediction/storage/duckdb.py:12)):
```python
def _flatten(value: Any) -> Any:
    if is_dataclass(value):
        flattened: dict[str, Any] = {}
        for key, nested_value in asdict(value).items():
            if isinstance(nested_value, dict):
                for nested_key, nested_item in nested_value.items():
                    flattened[f"{key}_{nested_key}"] = nested_item
            else:
                flattened[key] = nested_value
        return flattened
    return value
```

**Replace-table write pattern** ([src/tennisprediction/storage/duckdb.py](/Users/andrewlay/tennisprediction/src/tennisprediction/storage/duckdb.py:25)):
```python
def _replace_table(
    connection: duckdb.DuckDBPyConnection,
    *,
    table_name: str,
    rows: list[dict[str, Any]],
    ddl: str,
) -> None:
    connection.execute(f"drop table if exists {table_name}")
    connection.execute(ddl)
    if not rows:
        return

    columns = list(rows[0].keys())
    placeholders = ", ".join(["?"] * len(columns))
    column_list = ", ".join(columns)
    values = [tuple(row[column] for column in columns) for row in rows]
    connection.executemany(
        f"insert into {table_name} ({column_list}) values ({placeholders})",
        values,
    )
```

**Connection lifecycle pattern** ([src/tennisprediction/storage/duckdb.py](/Users/andrewlay/tennisprediction/src/tennisprediction/storage/duckdb.py:47)):
```python
def persist_canonical_snapshot(
    canonical_snapshot: CanonicalSnapshot,
    *,
    database_path: str | Path,
) -> Path:
    database_file = Path(database_path)
    database_file.parent.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(str(database_file))
    try:
        ...
    finally:
        connection.close()

    return database_file
```

**Copy from this analog:**
- Reuse `_flatten` for nested dataclass lineage/metadata.
- Use explicit table DDL inside the persistence module.
- Always manage DuckDB connection lifecycle with `try/finally`.

---

### `tests/unit/test_feature_runner.py` (test, event-driven)

**Why this file exists:** Explicit Wave 0 gap for snapshot-before-update and same-round cohort cases. Source: `.planning/phases/02-leakage-safe-feature-engine/02-RESEARCH.md:444`.

**Analog:** `tests/unit/test_quarantine.py`

**Fixture builder pattern** ([tests/unit/test_quarantine.py](/Users/andrewlay/tennisprediction/tests/unit/test_quarantine.py:11)):
```python
def _validated_matches_snapshot(tmp_path: Path, file_name: str, content: str):
    layout = RawSnapshotLayout(tmp_path / "raw")
    client = SackmannSourceClient(layout=layout)
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / file_name
    source_file.write_text(content, encoding="utf-8")
    manifest = client.materialize_local_snapshot(
        commit_sha="abcdef1",
        source_files={file_name: source_file},
```

**Behavior-first test naming** ([tests/unit/test_quarantine.py](/Users/andrewlay/tennisprediction/tests/unit/test_quarantine.py:28)):
```python
def test_non_atp_file_patterns_are_rejected_before_candidates_are_produced(tmp_path: Path) -> None:
```

**Copy from this analog:**
- Build compact synthetic histories inline with helper functions.
- Name tests by invariant, not by method name.
- Keep assertions focused on one leakage behavior per test.

---

### `tests/unit/test_feature_ordering.py` (test, transform)

**Why this file exists:** The proposed module split includes dedicated ordering tests for round precedence and rest/context rules. Source: `.planning/phases/02-leakage-safe-feature-engine/02-RESEARCH.md:199-203,432`.

**Analog:** `tests/unit/test_validation.py`

**Simple failing-case pattern** ([tests/unit/test_validation.py](/Users/andrewlay/tennisprediction/tests/unit/test_validation.py:28)):
```python
def test_validation_fails_on_missing_required_columns(tmp_path: Path) -> None:
    manifest = _build_manifest(
        tmp_path,
        "atp_matches_2024.csv",
        (
            "tourney_id,surface,tourney_name,tourney_date,tourney_level,winner_id,score,best_of,round\n"
            "2024-001,Hard,Example,20240115,A,1,6-4 6-4,3,R32\n"
        ),
    )

    with pytest.raises(ValueError, match="missing required columns"):
        validate_snapshot(manifest)
```

**Success-case pattern** ([tests/unit/test_validation.py](/Users/andrewlay/tennisprediction/tests/unit/test_validation.py:53)):
```python
def test_validation_returns_validated_snapshot_before_downstream_use(tmp_path: Path) -> None:
    manifest = _build_manifest(
        tmp_path,
        "atp_players.csv",
        "player_id,name_first,name_last\n1,Roger,Federer\n",
    )

    validated = validate_snapshot(manifest)

    assert isinstance(validated, ValidatedSnapshot)
```

**Copy from this analog:**
- Use one compact builder helper at the top of the file.
- Mix failing-case and success-case tests in the same module.
- Prefer direct assertions over parametrization unless repetition becomes heavy.

---

### `tests/unit/test_feature_rankings.py` (test, request-response)

**Why this file exists:** FEAT-03 explicitly requires prior-only ranking lookup tests. Source: `.planning/phases/02-leakage-safe-feature-engine/02-RESEARCH.md:428,445`.

**Analog:** `tests/unit/test_validation.py`

**Error-message assertion pattern** ([tests/unit/test_validation.py](/Users/andrewlay/tennisprediction/tests/unit/test_validation.py:42)):
```python
def test_validation_fails_when_parse_rules_drift(tmp_path: Path) -> None:
    manifest = _build_manifest(
        tmp_path,
        "atp_rankings_2024.csv",
        "ranking_date,rank,player,points\n2024-01-15,1,1,1000\n",
    )

    with pytest.raises(ValueError, match="must parse as YYYYMMDD date"):
        validate_snapshot(manifest)
```

**Copy from this analog:**
- Test lookup-edge failures with exact message matches where helpful.
- Use minimal synthetic ranking histories.
- Separate cutoff-date behavior from ranking-change behavior into distinct tests.

---

### `tests/unit/test_feature_state.py` (test, event-driven)

**Why this file exists:** FEAT-02, FEAT-04, FEAT-05, and FEAT-06 all land in state-transition coverage. Source: `.planning/phases/02-leakage-safe-feature-engine/02-RESEARCH.md:427,429-431,446`.

**Analog:** `tests/unit/test_quarantine.py`

**Multi-case synthetic-history pattern** ([tests/unit/test_quarantine.py](/Users/andrewlay/tennisprediction/tests/unit/test_quarantine.py:46)):
```python
def test_excluded_match_types_are_quarantined_with_reason_codes(tmp_path: Path) -> None:
    validated = _validated_matches_snapshot(
        tmp_path,
        "atp_matches_2024.csv",
        (
            "tourney_id,surface,tourney_name,tourney_date,tourney_level,winner_id,loser_id,score,best_of,round,comment\n"
            "2024-001,Hard,Example,20240115,A,1,2,6-4 6-4,3,Q1,\n"
            "2024-002,Clay,Example 2,20240116,A,3,4,6-0 1-0 ret,3,R32,Retired\n"
        ),
    )
```

**Copy from this analog:**
- Use tiny multi-match histories to expose transition behavior.
- Assert on both positive state fields and retained missingness.
- Prefer separate tests for Elo, form, stats, H2H, and rest rather than one mega-test.

---

### `tests/unit/test_feature_differential.py` (test, transform)

**Why this file exists:** FEAT-08 requires differential rows to be reproducible from persisted player-side snapshots. Source: `.planning/phases/02-leakage-safe-feature-engine/02-RESEARCH.md:433,447`.

**Analog:** `tests/unit/test_validation.py`

**Type/assertion pattern** ([tests/unit/test_validation.py](/Users/andrewlay/tennisprediction/tests/unit/test_validation.py:60)):
```python
validated = validate_snapshot(manifest)

assert isinstance(validated, ValidatedSnapshot)
assert validated.rows_by_file["atp_players.csv"][0]["name_last"] == "Federer"
```

**Copy from this analog:**
- Assert exact oriented field values for player A vs player B.
- Keep fixture setup minimal and deterministic.
- Validate reproducibility by rebuilding the row from persisted player-side inputs twice.

---

### `tests/unit/test_feature_leakage.py` (test, event-driven)

**Why this file exists:** FEAT-09 requires future-row deletion and same-cohort reorder invariants. Source: `.planning/phases/02-leakage-safe-feature-engine/02-RESEARCH.md:434,448`.

**Analog:** `tests/unit/test_quarantine.py`

**Invariant-style assertion pattern** ([tests/unit/test_quarantine.py](/Users/andrewlay/tennisprediction/tests/unit/test_quarantine.py:41)):
```python
partitioned = split_validated_snapshot(validated)
assert len(partitioned.accepted_rows["atp_matches_2024.csv"]) == 1
assert partitioned.quarantined_rows == {}
```

**Copy from this analog:**
- Assert invariant preservation after mutating the input history in a controlled way.
- Compare outputs directly, not just counts, for historical snapshot stability.
- Keep each test centered on one leakage dimension.

## Shared Patterns

### Typed Immutable Contracts
**Source:** [src/tennisprediction/domain/models.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/models.py:8)
**Apply to:** `features/schemas.py`, any persisted feature snapshot/state models
```python
@dataclass(frozen=True)
class SourceLineage:
    source_repo: str
    source_commit_sha: str
    source_file_path: str
    source_row_number: int
    source_snapshot_root: str
```

### Lineage Construction
**Source:** [src/tennisprediction/domain/normalization.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/normalization.py:19)
**Apply to:** any feature snapshot builder that needs provenance fields
```python
def _build_lineage(
    validated_snapshot: ValidatedSnapshot, *, source_file_path: str, source_row_number: int
) -> SourceLineage:
    return SourceLineage(
        source_repo=validated_snapshot.manifest.source_repo,
        source_commit_sha=validated_snapshot.manifest.commit_sha,
        source_file_path=source_file_path,
        source_row_number=source_row_number,
        source_snapshot_root=str(validated_snapshot.manifest.snapshot_root),
    )
```

### Explicit Missingness
**Source:** [src/tennisprediction/domain/normalization.py](/Users/andrewlay/tennisprediction/src/tennisprediction/domain/normalization.py:188)
**Apply to:** state aggregation, sparse stats, ranking availability fields
```python
def _optional_int(value: str) -> int | None:
    stripped = value.strip()
    return int(stripped) if stripped else None
```

### DuckDB Persistence
**Source:** [src/tennisprediction/storage/duckdb.py](/Users/andrewlay/tennisprediction/src/tennisprediction/storage/duckdb.py:25)
**Apply to:** feature snapshot tables, audit-state tables
```python
def _replace_table(
    connection: duckdb.DuckDBPyConnection,
    *,
    table_name: str,
    rows: list[dict[str, Any]],
    ddl: str,
) -> None:
    connection.execute(f"drop table if exists {table_name}")
    connection.execute(ddl)
    if not rows:
        return
```

### Test Fixture Style
**Source:** [tests/unit/test_quarantine.py](/Users/andrewlay/tennisprediction/tests/unit/test_quarantine.py:11)
**Apply to:** all `tests/unit/test_feature_*.py`
```python
def _validated_matches_snapshot(tmp_path: Path, file_name: str, content: str):
    layout = RawSnapshotLayout(tmp_path / "raw")
    client = SackmannSourceClient(layout=layout)
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_file = source_dir / file_name
    source_file.write_text(content, encoding="utf-8")
```

## No Analog Found

No exact in-repo analog exists yet for:

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `src/tennisprediction/features/state.py` | utility | event-driven | No Phase 1 module maintains long-lived per-player state across chronological events. |
| `src/tennisprediction/features/runner.py` | service | event-driven | No existing module implements cohort-baseline emit-then-update logic. |
| `tests/unit/test_feature_leakage.py` | test | event-driven | Existing tests validate ingestion and quarantine invariants, not historical snapshot stability. |

Planner should use the Phase 2 research patterns for these gaps, especially the cohort-baseline runner and backward-only ranking lookup from `.planning/phases/02-leakage-safe-feature-engine/02-RESEARCH.md:206-230`.

## Metadata

**Analog search scope:** `src/tennisprediction/`, `tests/unit/`, `docs/`, phase context/research files  
**Files scanned:** 12 code/docs files + 2 phase files  
**Pattern extraction date:** 2026-06-16
