# Phase 03: Modeling, Calibration, and Artifact Registry - Pattern Map

**Mapped:** 2026-06-18
**Files analyzed:** 17
**Analogs found:** 17 / 17

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `pyproject.toml` | config | request-response | `pyproject.toml` | exact |
| `src/tennisprediction/cli.py` | config | request-response | `src/tennisprediction/cli.py` | exact |
| `src/tennisprediction/modeling/__init__.py` | utility | transform | `src/tennisprediction/features/__init__.py` | role-match |
| `src/tennisprediction/modeling/schemas.py` | model | transform | `src/tennisprediction/features/schemas.py` | exact |
| `src/tennisprediction/modeling/datasets.py` | utility | transform | `src/tennisprediction/features/persistence.py` | data-flow-match |
| `src/tennisprediction/modeling/splits.py` | utility | transform | `src/tennisprediction/ingestion/manifests.py` | data-flow-match |
| `src/tennisprediction/modeling/baselines.py` | service | request-response | `src/tennisprediction/features/runner.py` | role-match |
| `src/tennisprediction/modeling/xgboost_model.py` | service | request-response | `src/tennisprediction/features/runner.py` | role-match |
| `src/tennisprediction/modeling/calibration.py` | service | transform | `src/tennisprediction/features/runner.py` | role-match |
| `src/tennisprediction/modeling/metrics.py` | utility | transform | `src/tennisprediction/features/differential.py` | partial |
| `src/tennisprediction/modeling/registry.py` | service | file-I/O | `src/tennisprediction/features/persistence.py` | data-flow-match |
| `src/tennisprediction/modeling/reports.py` | utility | file-I/O | `src/tennisprediction/ingestion/manifests.py` | partial |
| `tests/unit/test_modeling_datasets.py` | test | transform | `tests/unit/test_feature_persistence.py` | exact |
| `tests/unit/test_modeling_splits.py` | test | transform | `tests/unit/test_manifests.py` | exact |
| `tests/unit/test_modeling_baselines.py` | test | request-response | `tests/unit/test_feature_persistence.py` | role-match |
| `tests/unit/test_modeling_xgboost.py` | test | request-response | `tests/unit/test_feature_persistence.py` | role-match |
| `tests/unit/test_modeling_calibration.py` | test | transform | `tests/unit/test_feature_persistence.py` | role-match |
| `tests/unit/test_modeling_metrics.py` | test | transform | `tests/unit/test_feature_persistence.py` | role-match |
| `tests/unit/test_modeling_registry.py` | test | file-I/O | `tests/unit/test_manifests.py` | exact |

## Pattern Assignments

### `pyproject.toml` (config, request-response)

**Analog:** `pyproject.toml`

**Dependency-group pattern** ([pyproject.toml](/Users/andrewlay/tennisprediction/pyproject.toml:20)):
```toml
[dependency-groups]
dev = [
  "mypy>=1.18,<1.19",
  "pre-commit>=4.3,<4.4",
  "pytest>=9.1,<9.2",
  "ruff>=0.15,<0.16",
]
```

**Tooling pattern** ([pyproject.toml](/Users/andrewlay/tennisprediction/pyproject.toml:34)):
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
```

### `src/tennisprediction/cli.py` (config, request-response)

**Analog:** `src/tennisprediction/cli.py`

**CLI bootstrap pattern** ([src/tennisprediction/cli.py](/Users/andrewlay/tennisprediction/src/tennisprediction/cli.py:3)):
```python
import typer

from tennisprediction import __version__
from tennisprediction.config import get_settings
from tennisprediction.logging import configure_logging

app = typer.Typer(help="ATP-only tennis prediction project CLI.")
```

**Callback + command pattern** ([src/tennisprediction/cli.py](/Users/andrewlay/tennisprediction/src/tennisprediction/cli.py:12)):
```python
@app.callback()
def main() -> None:
    """Initialize config and logging for every CLI invocation."""
    settings = get_settings()
    configure_logging(settings)

@app.command()
def version() -> None:
    typer.echo(__version__)
```

### `src/tennisprediction/modeling/__init__.py` (utility, transform)

**Analog:** `src/tennisprediction/features/__init__.py`

**Package-export pattern** ([src/tennisprediction/features/__init__.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/__init__.py:1)):
```python
"""Leakage-safe feature contracts and chronological runner helpers."""

from tennisprediction.features.persistence import persist_feature_build
from tennisprediction.features.runner import build_feature_snapshots
from tennisprediction.features.schemas import (
    FeatureBuildResult,
    FeatureDifferentialRow,
    PlayerFeatureSnapshot,
)

__all__ = [
    "PlayerFeatureSnapshot",
    "FeatureDifferentialRow",
    "FeatureBuildResult",
    "build_feature_snapshots",
    "persist_feature_build",
]
```

### `src/tennisprediction/modeling/schemas.py` (model, transform)

**Analog:** `src/tennisprediction/features/schemas.py`

**Internal contract pattern** ([src/tennisprediction/features/schemas.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/schemas.py:3)):
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class PlayerFeatureSnapshot:
    feature_version: str
    canonical_match_id: str
    canonical_player_id: str
    opponent_canonical_player_id: str
```

**Aggregate result pattern** ([src/tennisprediction/features/schemas.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/schemas.py:87)):
```python
@dataclass(frozen=True)
class FeatureBuildResult:
    player_snapshots: list[PlayerFeatureSnapshot]
    differential_rows: list[FeatureDifferentialRow]
    state_audit_records: list[PlayerStateAuditRecord]
```

**Manifest-style contract pattern** ([src/tennisprediction/ingestion/manifests.py](/Users/andrewlay/tennisprediction/src/tennisprediction/ingestion/manifests.py:18)):
```python
class SourceFileEntry(BaseModel):
    relative_path: Path
    sha256: str = Field(min_length=64, max_length=64)
    source_url: str
    source_path: str
    size_bytes: int = Field(ge=0)

    model_config = ConfigDict(frozen=True)
```

### `src/tennisprediction/modeling/datasets.py` (utility, transform)

**Analog:** `src/tennisprediction/features/persistence.py`

**Column-building pattern** ([src/tennisprediction/features/persistence.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/persistence.py:100)):
```python
def _prefixed_snapshot_columns(
    *,
    prefix: str,
    snapshot: PlayerFeatureSnapshot,
) -> dict[str, Any]:
    flattened_snapshot = _flatten(snapshot)
    return {
        f"{prefix}_{column_name}": value
        for column_name, value in flattened_snapshot.items()
        if column_name not in _SNAPSHOT_BASE_COLUMNS
    }
```

**Deterministic dataset-row pattern** ([src/tennisprediction/features/persistence.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/persistence.py:113)):
```python
def _build_differential_rows(feature_build: FeatureBuildResult) -> list[dict[str, Any]]:
    snapshots_by_match_and_side = _snapshot_lookup(feature_build.player_snapshots)
    persisted_rows: list[dict[str, Any]] = []
    for differential_row in feature_build.differential_rows:
        player_a_snapshot = snapshots_by_match_and_side[
            (differential_row.canonical_match_id, differential_row.player_a_side)
        ]
        player_b_snapshot = snapshots_by_match_and_side[
            (differential_row.canonical_match_id, differential_row.player_b_side)
        ]
        row = {
            "feature_version": differential_row.feature_version,
            "canonical_match_id": differential_row.canonical_match_id,
            "player_a_id": differential_row.player_a_id,
            "player_b_id": differential_row.player_b_id,
            "as_of_date": differential_row.as_of_date,
        }
```

**Recommended adaptation:** keep dataset materialization deterministic, using ordered rows and explicit label joins against `canonical_matches`, rather than hidden pandas transforms.

### `src/tennisprediction/modeling/splits.py` (utility, transform)

**Analog:** `src/tennisprediction/ingestion/manifests.py`

**Frozen manifest pattern** ([src/tennisprediction/ingestion/manifests.py](/Users/andrewlay/tennisprediction/src/tennisprediction/ingestion/manifests.py:28)):
```python
class SourceManifest(BaseModel):
    source_repo: str
    commit_sha: str
    acquired_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    snapshot_root: Path
    attribution_text: str
    license_name: str
    license_text: str
    files: list[SourceFileEntry]

    model_config = ConfigDict(frozen=True)
```

**Checksum helper pattern** ([src/tennisprediction/ingestion/manifests.py](/Users/andrewlay/tennisprediction/src/tennisprediction/ingestion/manifests.py:10)):
```python
def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
```

**Recommended adaptation:** use the same frozen Pydantic style for split manifests, but hash train/validation/test match memberships and boundary metadata instead of raw source files.

### `src/tennisprediction/modeling/baselines.py` (service, request-response)

**Analog:** `src/tennisprediction/features/runner.py`

**Orchestration pattern** ([src/tennisprediction/features/runner.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/runner.py:136)):
```python
def build_feature_snapshots(
    *,
    matches: list[CanonicalMatch],
    rankings: list[CanonicalRanking],
    match_stats: list[CanonicalMatchStat] | None = None,
    feature_version: str = "02-04",
) -> FeatureBuildResult:
    player_snapshots: list[PlayerFeatureSnapshot] = []
    differential_rows = []
    state_audit_records = []
```

**Stepwise runner pattern** ([src/tennisprediction/features/runner.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/runner.py:150)):
```python
for cohort in build_match_cohorts(matches):
    for match in cohort:
        player_a_snapshot = _build_player_snapshot(...)
        player_b_snapshot = _build_player_snapshot(...)
        player_snapshots.extend([player_a_snapshot, player_b_snapshot])
        differential_rows.append(build_differential_row(player_a_snapshot, player_b_snapshot))
```

**Recommended adaptation:** make baseline trainers pure orchestrators around a typed dataset contract, returning structured fit results instead of ad hoc dictionaries.

### `src/tennisprediction/modeling/xgboost_model.py` (service, request-response)

**Analog:** `src/tennisprediction/features/runner.py`

**Stateful-but-contained runner pattern** ([src/tennisprediction/features/runner.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/runner.py:146)):
```python
player_states: dict[str, PlayerFeatureState] = {}
match_stat_states: dict[str, MatchStatAggregateState] = {}
head_to_head_states: dict[tuple[str, str], HeadToHeadState] = {}
match_stats_by_source_key = _index_match_stats(match_stats or [])
```

**Recommended adaptation:** keep XGBoost-specific early-stopping state inside one module, but expose the same typed fit result shape used by `baselines.py`.

### `src/tennisprediction/modeling/calibration.py` (service, transform)

**Analog:** `src/tennisprediction/features/runner.py`

**Two-phase transform pattern** ([src/tennisprediction/features/runner.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/runner.py:152)):
```python
player_a_snapshot = _build_player_snapshot(...)
player_b_snapshot = _build_player_snapshot(...)
player_snapshots.extend([player_a_snapshot, player_b_snapshot])
differential_rows.append(build_differential_row(player_a_snapshot, player_b_snapshot))
```

**Recommended adaptation:** follow the repo’s “derive outputs from an already-frozen input contract” pattern; calibration should consume frozen train/validation partitions and emit a separate calibrated artifact, not mutate raw fit state in place.

### `src/tennisprediction/modeling/metrics.py` (utility, transform)

**Analog:** `src/tennisprediction/features/persistence.py`

**Explicit derived-field pattern** ([src/tennisprediction/features/persistence.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/persistence.py:137)):
```python
"rank_diff": differential_row.rank_diff,
"rank_points_diff": differential_row.rank_points_diff,
"ranking_change_diff": differential_row.ranking_change_diff,
"elo_diff": differential_row.elo_diff,
"surface_elo_diff": differential_row.surface_elo_diff,
"rest_days_diff": differential_row.rest_days_diff,
```

**Recommended adaptation:** compute scalar metrics, calibration bins, ECE, and segments explicitly from named columns; avoid opaque “metrics blobs” whose inputs are not obvious from the code.

### `src/tennisprediction/modeling/registry.py` (service, file-I/O)

**Analog:** `src/tennisprediction/features/persistence.py`

**Filesystem prep + durable write pattern** ([src/tennisprediction/features/persistence.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/persistence.py:202)):
```python
def persist_feature_build(
    feature_build: FeatureBuildResult,
    *,
    database_path: str | Path,
) -> Path:
    database_file = Path(database_path)
    database_file.parent.mkdir(parents=True, exist_ok=True)
```

**Table-write helper pattern** ([src/tennisprediction/storage/duckdb.py](/Users/andrewlay/tennisprediction/src/tennisprediction/storage/duckdb.py:25)):
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
```

**Recommended adaptation:** create immutable run directories under `settings.models_dir`, write manifest/metrics/feature-column sidecars explicitly, and keep save/load helpers small and deterministic.

### `src/tennisprediction/modeling/reports.py` (utility, file-I/O)

**Analog:** `src/tennisprediction/ingestion/manifests.py`

**Path-oriented helper pattern** ([src/tennisprediction/ingestion/manifests.py](/Users/andrewlay/tennisprediction/src/tennisprediction/ingestion/manifests.py:40)):
```python
def file_path(self, entry: SourceFileEntry) -> Path:
    return self.snapshot_root / entry.relative_path
```

**Recommended adaptation:** keep report writers path-first and deterministic, with artifact manifests referencing generated CSV/JSON/PNG paths rather than embedding bulky payloads.

### `tests/unit/test_modeling_datasets.py` (test, transform)

**Analog:** `tests/unit/test_feature_persistence.py`

**Synthetic fixture style** ([tests/unit/test_feature_persistence.py](/Users/andrewlay/tennisprediction/tests/unit/test_feature_persistence.py:18)):
```python
def _lineage(*, file_name: str, row_number: int) -> SourceLineage:
    return SourceLineage(
        source_repo="JeffSackmann/tennis_atp",
        source_commit_sha="abcdef1",
        source_file_path=file_name,
        source_row_number=row_number,
        source_snapshot_root="/tmp/raw-snapshot",
    )
```

**Direct assertion style** ([tests/unit/test_feature_persistence.py](/Users/andrewlay/tennisprediction/tests/unit/test_feature_persistence.py:214)):
```python
def test_persist_feature_build_writes_snapshot_row_and_audit_tables(tmp_path: Path) -> None:
    matches, rankings, match_stats = _synthetic_history()
    feature_build = build_feature_snapshots(...)
    persisted_path = persist_feature_build(feature_build, database_path=database_path)
```

### `tests/unit/test_modeling_splits.py` (test, transform)

**Analog:** `tests/unit/test_manifests.py`

**Frozen-manifest validation pattern** ([tests/unit/test_manifests.py](/Users/andrewlay/tennisprediction/tests/unit/test_manifests.py:10)):
```python
def test_manifest_records_commit_checksum_attribution_and_license(tmp_path: Path) -> None:
    snapshot_root = tmp_path / "data" / "raw" / "tennis_atp" / "abcdef1"
    snapshot_root.mkdir(parents=True)
    source_file = snapshot_root / "atp_matches_2024.csv"
```

**Immutability assertion pattern** ([tests/unit/test_manifests.py](/Users/andrewlay/tennisprediction/tests/unit/test_manifests.py:46)):
```python
def test_raw_snapshot_layout_is_deterministic_and_immutable(tmp_path: Path) -> None:
    layout = RawSnapshotLayout(tmp_path / "data" / "raw" / "tennis_atp")
    snapshot_dir = layout.ensure_new_snapshot_dir("abcdef1")
```

### `tests/unit/test_modeling_baselines.py` (test, request-response)

**Analog:** `tests/unit/test_feature_persistence.py`

**Column-surface assertion pattern** ([tests/unit/test_feature_persistence.py](/Users/andrewlay/tennisprediction/tests/unit/test_feature_persistence.py:238)):
```python
snapshot_columns = _columns(connection, table_name="feature_player_snapshots")
assert {
    "feature_version",
    "canonical_match_id",
    "canonical_player_id",
    "opponent_canonical_player_id",
} <= snapshot_columns
```

**Recommended adaptation:** assert trainer outputs expose stable metric keys, selected feature columns, and artifact references rather than only “fit succeeded”.

### `tests/unit/test_modeling_calibration.py` (test, transform)

**Analog:** `tests/unit/test_feature_persistence.py`

**Chronological-history fixture pattern** ([tests/unit/test_feature_persistence.py](/Users/andrewlay/tennisprediction/tests/unit/test_feature_persistence.py:97)):
```python
def _synthetic_history(*, include_cross_file_collision: bool = False) -> tuple[
    list[CanonicalMatch],
    list[CanonicalRanking],
    list[CanonicalMatchStat],
]:
```

**Recommended adaptation:** build calibration tests from a tiny ordered match history with explicit train/validation boundaries, then assert validation-only calibration behavior.

### `tests/unit/test_modeling_registry.py` (test, file-I/O)

**Analog:** `tests/unit/test_manifests.py`

**Round-trip manifest assertion pattern** ([tests/unit/test_manifests.py](/Users/andrewlay/tennisprediction/tests/unit/test_manifests.py:17)):
```python
manifest = SourceManifest.model_validate(
    {
        "source_repo": "JeffSackmann/tennis_atp",
        "commit_sha": "abcdef1",
        "acquired_at": acquired_at,
    }
)
```

**Recommended adaptation:** validate registry manifests via `model_validate`, assert expected files exist in the run directory, and verify immutable directory creation semantics.

## Shared Patterns

### Typed Runtime Config
**Source:** [src/tennisprediction/config.py](/Users/andrewlay/tennisprediction/src/tennisprediction/config.py:14)
**Apply to:** `registry.py`, `reports.py`, `cli.py`, optional modeling path additions in `config.py`
```python
class Settings(BaseSettings):
    """Typed runtime configuration constrained to repository-local paths."""

    environment: Literal["dev", "test", "prod"] = "dev"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    data_dir: Path = Path("data")
    models_dir: Path = Path("models")
    reports_dir: Path = Path("reports")
```

### Repo-Local Path Guard
**Source:** [src/tennisprediction/config.py](/Users/andrewlay/tennisprediction/src/tennisprediction/config.py:34)
**Apply to:** Any new artifact/report directory config
```python
@staticmethod
def _resolve_repo_path(value: Path) -> Path:
    candidate = value if value.is_absolute() else REPO_ROOT / value
    resolved = candidate.resolve(strict=False)

    if resolved != REPO_ROOT and REPO_ROOT not in resolved.parents:
        msg = f"{value} must stay within the repository"
        raise ValueError(msg)
```

### Frozen Manifest Style
**Source:** [src/tennisprediction/ingestion/manifests.py](/Users/andrewlay/tennisprediction/src/tennisprediction/ingestion/manifests.py:18)
**Apply to:** split manifests, artifact manifests, environment manifests
```python
class SourceManifest(BaseModel):
    source_repo: str
    commit_sha: str
    acquired_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    snapshot_root: Path

    model_config = ConfigDict(frozen=True)
```

### Frozen Internal Dataclasses
**Source:** [src/tennisprediction/features/schemas.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/schemas.py:9)
**Apply to:** dataset rows, split results, fit results, metric payloads
```python
@dataclass(frozen=True)
class PlayerFeatureSnapshot:
    feature_version: str
    canonical_match_id: str
    canonical_player_id: str
```

### DuckDB Materialization Helpers
**Source:** [src/tennisprediction/storage/duckdb.py](/Users/andrewlay/tennisprediction/src/tennisprediction/storage/duckdb.py:12)
**Apply to:** dataset materialization or persisted split tables if added
```python
def _flatten(value: Any) -> Any:
    if is_dataclass(value):
        flattened: dict[str, Any] = {}
        for key, nested_value in asdict(value).items():
            if isinstance(nested_value, dict):
                for nested_key, nested_item in nested_value.items():
                    flattened[f"{key}_{nested_key}"] = nested_item
```

### CLI Bootstrapping
**Source:** [src/tennisprediction/cli.py](/Users/andrewlay/tennisprediction/src/tennisprediction/cli.py:12)
**Apply to:** any new `train`, `evaluate`, or `registry` commands
```python
@app.callback()
def main() -> None:
    """Initialize config and logging for every CLI invocation."""
    settings = get_settings()
    configure_logging(settings)
```

### Test Style
**Source:** [tests/unit/test_feature_persistence.py](/Users/andrewlay/tennisprediction/tests/unit/test_feature_persistence.py:214)
**Apply to:** all new modeling unit tests
```python
def test_persist_feature_build_writes_snapshot_row_and_audit_tables(tmp_path: Path) -> None:
    matches, rankings, match_stats = _synthetic_history()
    feature_build = build_feature_snapshots(...)
    persisted_path = persist_feature_build(feature_build, database_path=database_path)
```

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `src/tennisprediction/modeling/metrics.py` | utility | transform | No existing evaluation/metrics module yet; use explicit derived-field style from feature code. |
| `src/tennisprediction/modeling/reports.py` | utility | file-I/O | No existing report writer module yet; closest pattern is manifest path handling plus config-backed directories. |

## Metadata

**Analog search scope:** `src/tennisprediction/`, `tests/unit/`, `pyproject.toml`  
**Files scanned:** 12 primary analog files plus phase research  
**Pattern extraction date:** 2026-06-18
