# Phase 04: Backtesting and EV Decision Core - Pattern Map

**Mapped:** 2026-06-19
**Files analyzed:** 8
**Analogs found:** 8 / 8

## File Classification

| Planned File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/tennisprediction/backtesting/replay.py` | service | event-driven | `src/tennisprediction/features/runner.py` | data-flow-match |
| `src/tennisprediction/ev/pricing.py` | utility | transform | `src/tennisprediction/features/differential.py` | data-flow-match |
| `src/tennisprediction/ev/opportunity.py` | model | transform | `src/tennisprediction/modeling/metrics.py` | partial |
| `src/tennisprediction/backtesting/metrics.py` | utility | transform | `src/tennisprediction/modeling/metrics.py` | role-match |
| `src/tennisprediction/backtesting/reports.py` | utility | file-I/O | `src/tennisprediction/modeling/reports.py` | exact |
| `src/tennisprediction/backtesting/registry.py` | service | file-I/O | `src/tennisprediction/modeling/registry.py` | exact |
| `tests/unit/test_backtesting_replay.py` | test | event-driven | `tests/unit/test_modeling_registry.py` | role-match |
| `tests/unit/test_backtesting_reports.py` | test | file-I/O | `tests/unit/test_modeling_metrics.py` | role-match |

## Pattern Assignments

### `src/tennisprediction/backtesting/replay.py`

**Analog:** [src/tennisprediction/features/runner.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/runner.py:136)

**Imports and orchestrator shape** ([runner.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/runner.py:3)):
```python
from tennisprediction.domain.models import CanonicalMatch, CanonicalMatchStat, CanonicalRanking
from tennisprediction.features.differential import build_differential_row
from tennisprediction.features.ordering import build_match_cohorts
```

**Replay loop shape** ([runner.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/runner.py:136)):
```python
def build_feature_snapshots(...):
    player_snapshots: list[PlayerFeatureSnapshot] = []
    differential_rows = []
    state_audit_records = []
    ...
    for cohort in build_match_cohorts(matches):
        for match in cohort:
            ...
        (...) = apply_match_result_batch(...)
```

**Reuse for Phase 04:** keep replay as one deterministic public entrypoint that iterates ordered prediction rows/artifacts, emits decision records before mutating cumulative bankroll or curve state, and returns one typed aggregate result.

### `src/tennisprediction/ev/pricing.py`

**Analog:** [src/tennisprediction/features/differential.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/differential.py:6)

**Small helper pattern** ([differential.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/differential.py:6)):
```python
def _diff(left: int | None, right: int | None) -> int | None:
    if left is None or right is None:
        return None
    return left - right
```

**Single row builder pattern** ([differential.py](/Users/andrewlay/tennisprediction/src/tennisprediction/features/differential.py:18)):
```python
def build_differential_row(...) -> FeatureDifferentialRow:
    return FeatureDifferentialRow(
        feature_version=player_a_snapshot.feature_version,
        canonical_match_id=player_a_snapshot.canonical_match_id,
        ...
    )
```

**Reuse for Phase 04:** keep pricing logic as pure helpers plus one builder that computes implied probability, edge, EV, and liquidity-derived fields from one market/prediction input row. Avoid hidden state.

### `src/tennisprediction/ev/opportunity.py`

**Analog:** [src/tennisprediction/modeling/metrics.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/metrics.py:142)

**Reason-bucket grouping pattern** ([metrics.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/metrics.py:142)):
```python
def build_segment_diagnostics(
    calibrated_predictions: list[CalibratedPredictionRow],
) -> list[SegmentDiagnosticRow]:
    segment_rows: list[SegmentDiagnosticRow] = []
    segment_groups: dict[tuple[str, str], list[CalibratedPredictionRow]] = defaultdict(list)
```

**Explicit bucket helpers** ([metrics.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/metrics.py:181)):
```python
def _calendar_year(as_of_date: str) -> str:
    ...

def _ranking_band(prediction: CalibratedPredictionRow) -> str:
    ...

def _confidence_bucket(favored_probability: float) -> str:
    ...
```

**Reuse for Phase 04:** define accepted/rejected opportunity records with explicit reason codes and explicit provenance labels, then use small classifier helpers for threshold failures like price missing, liquidity too low, edge below threshold, confidence too low, or synthetic/proxy-only evidence.

### `src/tennisprediction/backtesting/metrics.py`

**Analog:** [src/tennisprediction/modeling/metrics.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/metrics.py:17)

**Top-level metric aggregator** ([metrics.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/metrics.py:17)):
```python
def evaluate_probability_predictions(
    y_true: list[int],
    probabilities: list[float],
) -> ProbabilityMetrics:
    ...
    return ProbabilityMetrics(...)
```

**Explicit bin math pattern** ([metrics.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/metrics.py:46)):
```python
for bin_index in range(10):
    ...
    if bucket:
        sample_count = len(bucket)
        ...
```

**Reuse for Phase 04:** compute ROI, profit curve, win rate, average edge, max drawdown, and sample size in one pure aggregator. Keep every derived field explicit and reproducible from accepted decision rows only.

### `src/tennisprediction/backtesting/reports.py`

**Analog:** [src/tennisprediction/modeling/reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/reports.py:14)

**Report directory and payload pattern** ([reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/reports.py:14)):
```python
def write_model_reports(... ) -> Path:
    report_dir = settings.reports_dir / "modeling" / run_id
    report_dir.mkdir(parents=True, exist_ok=False)
    metrics_payload = {
        "model_family": metrics_result.model_family,
        ...
    }
```

**CSV and parquet writer helpers** ([reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/reports.py:37)):
```python
_write_csv(report_dir / "calibration_curve.csv", ...)
_write_csv(report_dir / "segment_diagnostics.csv", ...)
_write_parquet(report_dir / "test_predictions.parquet", ...)
```

**Reuse for Phase 04:** write `reports/backtesting/<run_id>/...` with separate artifacts for summary metrics, profit curve, accepted decisions, rejected decisions, and provenance metadata. Keep the report writer thin; all calculations should arrive precomputed.

### `src/tennisprediction/backtesting/registry.py`

**Analog:** [src/tennisprediction/modeling/registry.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/registry.py:29)

**Immutable bundle pattern** ([registry.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/registry.py:29)):
```python
def write_model_artifact_bundle(... ) -> Path:
    artifact_dir = settings.models_dir / "runs" / run_id
    artifact_dir.mkdir(parents=True, exist_ok=False)
    report_dir = write_model_reports(run_id, calibrated_result, metrics_result, settings)
```

**Manifest-rich provenance pattern** ([registry.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/registry.py:60)):
```python
manifest = ModelArtifactManifest(
    run_id=run_id,
    model_family=raw_fit_result.model_family,
    source_repo=split_manifest.source_repo,
    source_commit_sha=split_manifest.source_commit_sha,
    feature_version=split_manifest.feature_version,
    split_manifest_id=split_manifest.split_id,
    ...
)
```

**Trusted load guard pattern** ([registry.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/registry.py:101)):
```python
artifact_dir = Settings._resolve_repo_path(Path(path))
...
manifest = ModelArtifactManifest.model_validate_json(...)
_validate_manifest(...)
...
for required_path in required_paths:
    if not required_path.is_file():
        raise FileNotFoundError(required_path)
```

**Reuse for Phase 04:** if backtests get their own persisted bundle, keep the same append-only directory rule, repo-local load validation, and manifest-first reads before touching any saved parquet or decision artifacts.

## Shared Patterns

### Provenance-first manifests
**Source:** [src/tennisprediction/ingestion/manifests.py](/Users/andrewlay/tennisprediction/src/tennisprediction/ingestion/manifests.py:10)
```python
def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()
```
Apply to backtest manifests and any persisted accepted/rejected opportunity dataset.

### Guard before deserialize/read
**Source:** [src/tennisprediction/modeling/registry.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/registry.py:101)
Use repo-local path validation, expected feature/split checks, required-file checks, and checksum checks before reading replay inputs.

### Thin file writers
**Source:** [src/tennisprediction/modeling/reports.py](/Users/andrewlay/tennisprediction/src/tennisprediction/modeling/reports.py:57)
```python
def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    pd.DataFrame.from_records(rows).to_csv(path, index=False)
```
Use the same split between pure calculation modules and thin persistence modules.

### Tests should lock outputs, not just behavior
**Source:** [tests/unit/test_modeling_registry.py](/Users/andrewlay/tennisprediction/tests/unit/test_modeling_registry.py:42), [tests/unit/test_modeling_metrics.py](/Users/andrewlay/tennisprediction/tests/unit/test_modeling_metrics.py:193)
Lock exact persisted filenames, manifest keys, and bucket/reason-code semantics.

## Planner Notes

- Prefer Phase 04 modules under `src/tennisprediction/backtesting/` and `src/tennisprediction/ev/`; that matches the repo’s architecture notes in `.planning/research/STACK.md` and `.planning/research/ARCHITECTURE.md`.
- Reuse Phase 03 calibrated prediction parquet plus trusted artifact manifests as replay inputs; do not rebuild model provenance ad hoc.
- Keep accepted and rejected opportunity records in the same schema family, with a required `reason_code` or `acceptance_reason` field so reports can summarize both paths consistently.
- Profitability reports should carry an explicit provenance label field from the start: `actual_kalshi_history`, `collected_snapshot_replay`, or `synthetic_proxy`.

## No Analog Found

| File | Gap |
|---|---|
| None | Existing modeling/reporting/runner code is sufficient to seed all planned Phase 04 artifacts. |

## Metadata

**Analog search scope:** `src/tennisprediction/features`, `src/tennisprediction/modeling`, `src/tennisprediction/ingestion`, `tests/unit`, `.planning`
**Pattern extraction date:** 2026-06-19
