# Phase 06: Market Mapping, Executable Pricing, and Live EV Monitor - Pattern Map

**Mapped:** 2026-06-20
**Files analyzed:** 10
**Analogs found:** 10 / 10

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/tennisprediction/market_mapping/schemas.py` | model | request-response | `src/tennisprediction/backtesting/schemas.py` | exact |
| `src/tennisprediction/market_mapping/aliases.py` | service | file-I/O | `src/tennisprediction/modeling/registry.py` | data-flow-match |
| `src/tennisprediction/market_mapping/normalization.py` | utility | transform | `src/tennisprediction/domain/normalization.py` | exact |
| `src/tennisprediction/market_mapping/resolver.py` | service | request-response | `src/tennisprediction/backtesting/replay.py` | role-match |
| `src/tennisprediction/kalshi/executable.py` | utility | transform | `src/tennisprediction/ev/opportunity.py` | data-flow-match |
| `src/tennisprediction/monitoring/scan.py` | service | batch | `src/tennisprediction/kalshi/jobs.py` | role-match |
| `src/tennisprediction/monitoring/reports.py` | service | file-I/O | `src/tennisprediction/backtesting/reports.py` | exact |
| `src/tennisprediction/cli.py` | cli | request-response | `src/tennisprediction/cli.py` | exact |
| `tests/unit/test_market_mapping.py` | test | request-response | `tests/unit/test_backtesting_decisions.py` | role-match |
| `tests/unit/test_monitoring_scan.py` | test | batch | `tests/unit/test_kalshi_storage.py` | role-match |

## Pattern Assignments

### `src/tennisprediction/market_mapping/schemas.py` (model, request-response)

**Analog:** `src/tennisprediction/backtesting/schemas.py`

**Imports and enum/dataclass pattern** (`src/tennisprediction/backtesting/schemas.py:1`):
```python
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal
```

**Frozen DTO pattern** (`src/tennisprediction/backtesting/schemas.py:22`):
```python
@dataclass(frozen=True)
class ReplayPredictionRow:
    artifact_run_id: str
    model_name: str
    model_family: str
    canonical_match_id: str
```

**Enum source-label pattern** (`src/tennisprediction/backtesting/schemas.py:15`):
```python
class MarketProbabilitySource(StrEnum):
    normalized_positive_side = "normalized_positive_side"
    normalized_negative_side = "normalized_negative_side"
    normalized_midpoint = "normalized_midpoint"
    manual_fixture = "manual_fixture"
```

**Audit snapshot helper pattern** (`src/tennisprediction/backtesting/schemas.py:59`):
```python
@dataclass(frozen=True)
class DecisionThresholds:
    min_edge: float
    min_confidence: float
    min_liquidity: float

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
```

Use this shape for Phase 06 mapping enums like `matched|ambiguous|unmatched|excluded`, alias records, mapping evidence rows, executable pricing inputs, and scan result DTOs.

---

### `src/tennisprediction/market_mapping/aliases.py` (service, file-I/O)

**Analog:** `src/tennisprediction/modeling/registry.py`

**Repo-local path resolution pattern** (`src/tennisprediction/modeling/registry.py:101`):
```python
artifact_dir = Settings._resolve_repo_path(Path(path))
if not artifact_dir.exists():
    raise FileNotFoundError(artifact_dir)
if not artifact_dir.is_dir():
    msg = "artifact bundle path must be a directory"
    raise ValueError(msg)
```

**JSON write pattern** (`src/tennisprediction/modeling/registry.py:41`):
```python
feature_columns_path.write_text(
    json.dumps(raw_fit_result.feature_columns, indent=2),
    encoding="utf-8",
)
```

**Manifest validation pattern** (`src/tennisprediction/modeling/registry.py:114`):
```python
manifest_path = artifact_dir / "manifest.json"
if not manifest_path.is_file():
    raise FileNotFoundError(manifest_path)
manifest = ModelArtifactManifest.model_validate_json(
    manifest_path.read_text(encoding="utf-8")
)
```

Use this for auditable alias override artifacts: resolve the path through `Settings._resolve_repo_path`, store JSON with stable formatting, and fail loudly on missing or malformed files.

---

### `src/tennisprediction/market_mapping/normalization.py` (utility, transform)

**Analog:** `src/tennisprediction/domain/normalization.py`

**Import and helper layout pattern** (`src/tennisprediction/domain/normalization.py:1`):
```python
from collections.abc import Iterable

from tennisprediction.domain.ids import CanonicalIdFactory
from tennisprediction.domain.models import (
    CanonicalMatch,
    CanonicalMatchStat,
    CanonicalPlayer,
```

**Small private helper pattern** (`src/tennisprediction/domain/normalization.py:19`):
```python
def _build_lineage(
    validated_snapshot: ValidatedSnapshot, *, source_file_path: str, source_row_number: int
) -> SourceLineage:
    return SourceLineage(
        source_repo=validated_snapshot.manifest.source_repo,
        source_commit_sha=validated_snapshot.manifest.commit_sha,
```

**Deterministic normalization loop pattern** (`src/tennisprediction/domain/normalization.py:39`):
```python
def _normalize_players(...):
    players: list[CanonicalPlayer] = []
    seen_ids: set[int] = set()
    for source_file_path, source_row_number, row in _iter_rows(rows):
        if source_file_path != "atp_players.csv":
            continue
```

**Public wrapper pattern** (`src/tennisprediction/domain/normalization.py:213`):
```python
def normalize_snapshot(validated_snapshot: ValidatedSnapshot) -> CanonicalSnapshot:
    partitioned = split_validated_snapshot(validated_snapshot)
    accepted_rows = partitioned.accepted_rows
```

Use the same style for `normalize_market_player_name()` and related helpers: small pure functions, deterministic filtering, explicit intermediate variables, and no fuzzy auto-resolution inside the normalizer.

---

### `src/tennisprediction/market_mapping/resolver.py` (service, request-response)

**Analog:** `src/tennisprediction/backtesting/replay.py`

**Dependency-loading seam pattern** (`src/tennisprediction/backtesting/replay.py:15`):
```python
def replay_model_predictions(
    artifact_dir: str | Path,
    database_path: str | Path,
    *,
    expected_feature_version: str,
    expected_split_manifest_id: str,
) -> ReplayRunResult:
```

**Canonical ID lookup pattern** (`src/tennisprediction/backtesting/replay.py:32`):
```python
row_lookup = {row.canonical_match_id: row for row in dataset.rows}
ordered_rows = [
    row_lookup[canonical_match_id]
    for canonical_match_id in bundle.split_manifest.test.canonical_match_ids
]
```

**Typed row construction pattern** (`src/tennisprediction/backtesting/replay.py:49`):
```python
replay_rows = [
    ReplayPredictionRow(
        artifact_run_id=bundle.manifest.run_id,
        model_name=bundle.manifest.model_name,
        ...
    )
]
```

**Type-guard helper pattern** (`src/tennisprediction/backtesting/replay.py:112`):
```python
def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    raise TypeError("expected integer feature value")
```

Use this structure for resolver entrypoints that load alias artifacts, canonical player/match rows, and persisted Kalshi snapshots, then return typed `MappingEvidenceRow` results keyed by `canonical_match_id` and market ticker.

---

### `src/tennisprediction/kalshi/executable.py` (utility, transform)

**Analog:** `src/tennisprediction/ev/opportunity.py`

**Import and typed evaluation seam** (`src/tennisprediction/ev/opportunity.py:6`):
```python
from tennisprediction.backtesting.schemas import (
    BacktestProvenanceLabel,
    DecisionThresholds,
    MarketProbabilitySource,
    NormalizedMarketInput,
```

**Single-row adapter pattern** (`src/tennisprediction/ev/opportunity.py:61`):
```python
def _evaluate_single_row(
    *,
    replay_row: ReplayPredictionRow,
    market_input: NormalizedMarketInput,
    thresholds: DecisionThresholds,
) -> list[OpportunityDecisionRecord]:
```

**Explicit positive/negative side handling** (`src/tennisprediction/ev/opportunity.py:68`):
```python
market_probability_positive = _coerce_market_probability(market_input.market_probability)
positive_evaluation = evaluate_candidate_side(...)
negative_evaluation = evaluate_candidate_side(
    side="negative",
    model_probability=1.0 - replay_row.calibrated_probability,
    market_probability=(
        None
        if market_probability_positive is None
        else 1.0 - market_probability_positive
    ),
)
```

**Threshold snapshot evidence pattern** (`src/tennisprediction/ev/opportunity.py:161`):
```python
def market_input_threshold_snapshot(...):
    return {
        "market_probability_source": ...,
        "liquidity_source": market_input.liquidity_source,
        "provenance_label": ...,
        "assumption_notes": market_input.assumption_notes,
```

Keep this module as a pure adapter: input `KalshiOrderbookSnapshotRow`, output side-specific executable price/liquidity/freshness DTOs with explicit `price_source`, `liquidity_source`, `freshness_age_seconds`, and rejection codes.

---

### `src/tennisprediction/monitoring/scan.py` (service, batch)

**Analog:** `src/tennisprediction/kalshi/jobs.py`

**Batch orchestration signature pattern** (`src/tennisprediction/kalshi/jobs.py:40`):
```python
def collect_kalshi_snapshots(
    client: KalshiReadClient,
    *,
    database_path: str | Path | None = None,
    page_limit: int = 100,
    status: AllowedMarketStatus | None = None,
```

**Accumulator pattern** (`src/tennisprediction/kalshi/jobs.py:54`):
```python
request_logs: list[KalshiRequestLogRow] = []
market_snapshots: list[KalshiMarketSnapshotRow] = []
market_detail_snapshots: list[KalshiMarketDetailSnapshotRow] = []
orderbook_snapshots: list[KalshiOrderbookSnapshotRow] = []
```

**Explicit fail-closed branching pattern** (`src/tennisprediction/kalshi/jobs.py:96`):
```python
collection_action = _market_collection_action(market.status)
if not collection_action.collect_detail:
    continue
...
if not collection_action.collect_orderbook:
    continue
```

**Final batch-return pattern** (`src/tennisprediction/kalshi/jobs.py:141`):
```python
batch = KalshiSnapshotBatch(
    request_logs=tuple(request_logs),
    market_snapshots=tuple(market_snapshots),
    market_detail_snapshots=tuple(market_detail_snapshots),
    orderbook_snapshots=tuple(orderbook_snapshots),
)
```

Use the same orchestration style for shadow/live-readonly scans: load or collect snapshots, resolve mappings, derive executable inputs, evaluate EV, then persist accepted and rejected outputs in one typed batch.

---

### `src/tennisprediction/monitoring/reports.py` (service, file-I/O)

**Analog:** `src/tennisprediction/backtesting/reports.py`

**Report directory pattern** (`src/tennisprediction/backtesting/reports.py:22`):
```python
report_dir = settings.reports_dir / "backtesting" / run_id
report_dir.mkdir(parents=True, exist_ok=False)
```

**Accepted/rejected dual-write pattern** (`src/tennisprediction/backtesting/reports.py:50`):
```python
_write_parquet(
    report_dir / "accepted_opportunities.parquet",
    [_serializable_record(record) for record in batch.accepted_records],
)
_write_parquet(
    report_dir / "rejected_opportunities.parquet",
```

**Summary counts pattern** (`src/tennisprediction/backtesting/reports.py:98`):
```python
def _reason_counts(batch: OpportunityDecisionBatch) -> list[dict[str, object]]:
    counts: dict[str, int] = {}
    for record in batch.rejected_records:
        for reason_code in record.rejection_reason_codes:
            counts[reason_code] = counts.get(reason_code, 0) + 1
```

**Serializable DTO pattern** (`src/tennisprediction/backtesting/reports.py:81`):
```python
def _serializable_record(record: OpportunityDecisionRecord) -> dict[str, object]:
    payload = asdict(record)
    ...
    if isinstance(threshold_snapshot, dict):
        payload["threshold_snapshot"] = json.dumps(threshold_snapshot, sort_keys=True)
```

Mirror this for Phase 06 scan output: one machine-readable accepted table, one rejected/excluded table, plus summary CSV/JSON for reason counts and scan metadata.

---

### `src/tennisprediction/cli.py` (cli, request-response)

**Analog:** `src/tennisprediction/cli.py`

**Top-level app and callback pattern** (`src/tennisprediction/cli.py:16`):
```python
app = typer.Typer(help="ATP-only tennis prediction project CLI.")

@app.callback()
def main() -> None:
    settings = get_settings()
    configure_logging(settings)
```

**Command registration pattern** (`src/tennisprediction/cli.py:36`):
```python
@app.command("collect-kalshi-snapshots")
def collect_kalshi_snapshots(
    access_key: Annotated[str, typer.Option(help="Kalshi access key.")],
    private_key: Annotated[Path, typer.Option(exists=True, dir_okay=False, ...)],
```

**Client lifecycle pattern** (`src/tennisprediction/cli.py:64`):
```python
client = KalshiReadClient(...)
try:
    persisted_path = collect_kalshi_snapshot_job(...)
finally:
    client.close()
```

Extend `cli.py` in-place rather than creating a second entrypoint. Phase 06 commands should follow the same callback bootstrap, typed options, and explicit resource cleanup.

---

### `tests/unit/test_market_mapping.py` (test, request-response)

**Analog:** `tests/unit/test_backtesting_decisions.py`

**Direct constructor fixture pattern** (`tests/unit/test_backtesting_decisions.py:15`):
```python
def test_evaluate_opportunities_chooses_higher_ev_side_and_keeps_threshold_snapshot() -> None:
    replay_row = _replay_row(calibrated_probability=0.35, target=1)
    market_input = NormalizedMarketInput(...)
```

**Reason-code assertions pattern** (`tests/unit/test_backtesting_decisions.py:121`):
```python
reason_sets = {
    record.canonical_match_id: set(record.rejection_reason_codes)
    for record in batch.rejected_records
}
assert reason_sets["match:missing-prob"] == {"missing_market_probability"}
```

**Private helper builder pattern** (`tests/unit/test_backtesting_decisions.py:132`):
```python
def _replay_row(... ) -> ReplayPredictionRow:
    return ReplayPredictionRow(...)
```

Use this structure for deterministic mapping tests: exact-match resolution, alias override resolution, ambiguous-name rejection, out-of-scope exclusion, and persisted reason-code coverage.

---

### `tests/unit/test_monitoring_scan.py` (test, batch)

**Analog:** `tests/unit/test_kalshi_storage.py`

**Round-trip batch test pattern** (`tests/unit/test_kalshi_storage.py:37`):
```python
def test_persist_and_load_kalshi_snapshot_batch_round_trips_metadata_timestamps_and_payload_lineage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
```

**Monkeypatch repo-root discipline pattern** (`tests/unit/test_kalshi_storage.py:41`):
```python
monkeypatch.setattr(config_module, "REPO_ROOT", tmp_path)
database_path = tmp_path / "data" / "kalshi" / "snapshots.duckdb"
```

**Stable schema assertion pattern** (`tests/unit/test_kalshi_storage.py:155`):
```python
assert tables == {
    "kalshi_request_logs",
    "kalshi_market_snapshots",
    "kalshi_market_detail_snapshots",
    "kalshi_orderbook_snapshots",
}
```

**Repo-local path rejection pattern** (`tests/unit/test_kalshi_storage.py:198`):
```python
with pytest.raises(ValueError, match="repository"):
    persist_kalshi_snapshot_batch(batch, database_path=outside_path)
```

Use this for scan persistence and report tests: verify accepted/rejected outputs are both written, schema stays stable, timestamps/freshness are preserved, and paths cannot escape the repo.

## Shared Patterns

### Repository-local path enforcement
**Source:** `src/tennisprediction/config.py:14`
**Apply to:** Alias artifacts, mapping evidence storage, scan reports, optional database overrides
```python
class Settings(BaseSettings):
    data_dir: Path = Path("data")
    models_dir: Path = Path("models")
    reports_dir: Path = Path("reports")
    duckdb_path: Path = Path("data/duckdb/tennisprediction.duckdb")

    @staticmethod
    def _resolve_repo_path(value: Path) -> Path:
        candidate = value if value.is_absolute() else REPO_ROOT / value
        resolved = candidate.resolve(strict=False)
        if resolved != REPO_ROOT and REPO_ROOT not in resolved.parents:
            raise ValueError(f"{value} must stay within the repository")
```

### Canonical match join pattern
**Source:** `src/tennisprediction/modeling/datasets.py:28`
**Apply to:** Market resolver joins, scan-time prediction lookup, evidence generation
```python
query = """
    select
        d.*,
        case
            when d.player_a_id = m.winner_canonical_player_id then 1
            else 0
        end as target
    from feature_differential_rows as d
    join canonical_matches as m using (canonical_match_id)
    where d.feature_version = ?
"""
```

### Kalshi snapshot audit lineage
**Source:** `src/tennisprediction/kalshi/snapshots.py:17`
**Apply to:** Mapping evidence rows and executable pricing evidence
```python
SNAPSHOT_LINEAGE_COLUMNS = (
    "request_id",
    "collected_at_utc",
    "request_method",
    "request_path",
    "request_base_url",
    "request_timestamp_ms",
    "request_signed_payload",
```

### Request-log construction and checksum pattern
**Source:** `src/tennisprediction/kalshi/snapshots.py:203`
**Apply to:** Any persisted evidence payload derived from live Kalshi data
```python
payload_json = _canonical_payload_json(
    payload=response_payload,
    payload_json=response_payload_json,
)
checksum = _sha256_hex(payload_json)
normalized_collected_at = _normalize_utc_naive(collected_at_utc)
```

### Accepted/rejected EV audit symmetry
**Source:** `src/tennisprediction/ev/opportunity.py:47`
**Apply to:** Phase 06 ranked monitor and unscorable market handling
```python
return OpportunityDecisionBatch(
    run_id=run_id,
    ...
    accepted_records=accepted_records,
    rejected_records=rejected_records,
)
```

### Threshold snapshot provenance
**Source:** `src/tennisprediction/ev/opportunity.py:167`
**Apply to:** Executable pricing normalization and live/shadow scan outputs
```python
return {
    "market_probability_source": ...,
    "liquidity_source": market_input.liquidity_source,
    "provenance_label": ...,
    "assumption_notes": market_input.assumption_notes,
    "selected_side": selected_side,
```

### CLI smoke-test pattern
**Source:** `tests/unit/test_cli_smoke.py:55`
**Apply to:** Any new `map-*` or `scan-*` commands
```python
result = runner.invoke(app, ["version"])
assert result.exit_code == 0
```

## No Analog Found

None. Every likely Phase 06 file has at least a role-match or data-flow-match analog in the current repo.

## Metadata

**Analog search scope:** `src/tennisprediction`, `tests/unit`, `.planning/phases/06-market-mapping-executable-pricing-and-live-ev-monitor`
**Files scanned:** 14
**Pattern extraction date:** 2026-06-20
