from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from tennisprediction import __version__, operations
from tennisprediction.config import get_settings
from tennisprediction.kalshi.client import AllowedMarketStatus
from tennisprediction.logging import configure_logging

app = typer.Typer(help="ATP-only tennis prediction project CLI.")


@app.callback()
def main() -> None:
    """Initialize config and logging for every CLI invocation."""
    settings = get_settings()
    configure_logging(settings)


@app.command()
def version() -> None:
    typer.echo(__version__)


@app.command()
def health() -> None:
    typer.echo("ok")


@app.command("ingest-snapshot")
def ingest_snapshot(
    source_commit_sha: Annotated[
        str,
        typer.Option(help="Pinned Jeff Sackmann source commit SHA already materialized locally."),
    ],
    database_path: Annotated[
        Path | None,
        typer.Option(help="Optional DuckDB path for persisted canonical ATP tables."),
    ] = None,
) -> None:
    persisted_path = operations.ingest_snapshot(
        source_commit_sha=source_commit_sha,
        database_path=database_path,
    )
    typer.echo(str(persisted_path))


@app.command("build-features")
def build_features(
    feature_version: Annotated[
        str,
        typer.Option(help="Feature version label written to persisted feature tables."),
    ] = get_settings().default_feature_version,
    database_path: Annotated[
        Path | None,
        typer.Option(help="Optional DuckDB path containing canonical ATP tables."),
    ] = None,
) -> None:
    persisted_path = operations.build_features(
        feature_version=feature_version,
        database_path=database_path,
    )
    typer.echo(str(persisted_path))


@app.command("train-artifact-bundle")
def train_artifact_bundle(
    run_id: Annotated[
        str,
        typer.Option(help="Artifact bundle run id written under models/runs/<run_id>."),
    ],
    feature_version: Annotated[
        str,
        typer.Option(help="Feature version to materialize into the training dataset."),
    ] = get_settings().default_feature_version,
    train_end_date: Annotated[
        str,
        typer.Option(help="Inclusive train split end date in YYYYMMDD format."),
    ] = ...,
    validation_end_date: Annotated[
        str,
        typer.Option(help="Inclusive validation split end date in YYYYMMDD format."),
    ] = ...,
    test_end_date: Annotated[
        str,
        typer.Option(help="Inclusive test split end date in YYYYMMDD format."),
    ] = ...,
    database_path: Annotated[
        Path | None,
        typer.Option(help="Optional DuckDB path containing canonical and feature tables."),
    ] = None,
    model_family: Annotated[
        str | None,
        typer.Option(
            help="Optional model family override: logistic_regression, random_forest, or xgboost."
        ),
    ] = None,
    calibration_method: Annotated[
        str | None,
        typer.Option(help="Optional calibration method override: sigmoid or isotonic."),
    ] = None,
) -> None:
    artifact_dir = operations.train_artifact_bundle(
        run_id=run_id,
        feature_version=feature_version,
        train_end_date=train_end_date,
        validation_end_date=validation_end_date,
        test_end_date=test_end_date,
        database_path=database_path,
        model_family=model_family,
        calibration_method=calibration_method,
    )
    typer.echo(str(artifact_dir))


@app.command("evaluate-artifact")
def evaluate_artifact(
    artifact_dir: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            help="Trusted model artifact bundle directory.",
        ),
    ],
    expected_feature_version: Annotated[
        str,
        typer.Option(help="Expected feature version for the trusted artifact bundle."),
    ],
    expected_split_manifest_id: Annotated[
        str,
        typer.Option(help="Expected split manifest id for the trusted artifact bundle."),
    ],
    database_path: Annotated[
        Path | None,
        typer.Option(help="Optional DuckDB path used for replay parity verification."),
    ] = None,
) -> None:
    evaluation_path = operations.evaluate_artifact(
        artifact_dir=artifact_dir,
        expected_feature_version=expected_feature_version,
        expected_split_manifest_id=expected_split_manifest_id,
        database_path=database_path,
    )
    typer.echo(str(evaluation_path))


@app.command("run-backtest")
def run_backtest(
    artifact_dir: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            help="Trusted model artifact bundle directory.",
        ),
    ],
    expected_feature_version: Annotated[
        str,
        typer.Option(help="Expected feature version for the trusted artifact bundle."),
    ],
    expected_split_manifest_id: Annotated[
        str,
        typer.Option(help="Expected split manifest id for the trusted artifact bundle."),
    ],
    run_id: Annotated[
        str,
        typer.Option(help="Backtest report run id written under reports/backtesting/<run_id>."),
    ],
    database_path: Annotated[
        Path | None,
        typer.Option(help="Optional DuckDB path containing historical ATP feature data."),
    ] = None,
    min_edge: Annotated[
        float | None,
        typer.Option(help="Optional minimum edge threshold override."),
    ] = None,
    min_confidence: Annotated[
        float | None,
        typer.Option(help="Optional minimum confidence threshold override."),
    ] = None,
    min_liquidity: Annotated[
        float | None,
        typer.Option(help="Optional minimum liquidity threshold override."),
    ] = None,
    fee_per_contract: Annotated[
        float,
        typer.Option(help="Fee per contract used in the proxy backtest."),
    ] = 0.0,
    slippage_per_contract: Annotated[
        float,
        typer.Option(help="Slippage per contract used in the proxy backtest."),
    ] = 0.0,
) -> None:
    report_dir = operations.run_backtest(
        artifact_dir=artifact_dir,
        expected_feature_version=expected_feature_version,
        expected_split_manifest_id=expected_split_manifest_id,
        run_id=run_id,
        database_path=database_path,
        min_edge=min_edge,
        min_confidence=min_confidence,
        min_liquidity=min_liquidity,
        fee_per_contract=fee_per_contract,
        slippage_per_contract=slippage_per_contract,
    )
    typer.echo(str(report_dir))


@app.command("collect-kalshi-snapshots")
def collect_kalshi_snapshots(
    access_key: Annotated[str, typer.Option(help="Kalshi access key.")],
    private_key: Annotated[
        Path,
        typer.Option(
            exists=True,
            dir_okay=False,
            help="Path to the Kalshi RSA private key.",
        ),
    ],
    database_path: Annotated[
        Path | None,
        typer.Option(help="Optional DuckDB path for persisted snapshots."),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option(help="Optional Kalshi base URL override."),
    ] = None,
    page_limit: Annotated[
        int,
        typer.Option(min=1, help="Page size used for cursor pagination."),
    ] = 100,
    status: Annotated[
        AllowedMarketStatus | None,
        typer.Option(help="Optional market status filter."),
    ] = None,
) -> None:
    persisted_path = operations.collect_kalshi_snapshots(
        access_key=access_key,
        private_key=private_key,
        database_path=database_path,
        base_url=base_url,
        page_limit=page_limit,
        status=status,
    )
    typer.echo(str(persisted_path))


@app.command("scan-kalshi-ev")
def scan_kalshi_ev(
    artifact_dir: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            help="Trusted model artifact bundle directory.",
        ),
    ],
    expected_feature_version: Annotated[
        str,
        typer.Option(help="Expected feature version for the trusted artifact bundle."),
    ],
    expected_split_manifest_id: Annotated[
        str,
        typer.Option(help="Expected split manifest id for the trusted artifact bundle."),
    ],
    database_path: Annotated[
        Path | None,
        typer.Option(help="DuckDB path for persisted Kalshi snapshots and modeling data."),
    ] = None,
    collect_fresh: Annotated[
        bool,
        typer.Option(
            help="Collect fresh read-only Kalshi snapshots before scoring instead of shadow mode.",
        ),
    ] = False,
    access_key: Annotated[
        str | None,
        typer.Option(help="Kalshi access key used only with --collect-fresh."),
    ] = None,
    private_key: Annotated[
        Path | None,
        typer.Option(
            exists=True,
            dir_okay=False,
            help="Kalshi RSA private key used only with --collect-fresh.",
        ),
    ] = None,
    base_url: Annotated[
        str | None,
        typer.Option(help="Optional Kalshi base URL override for live read-only collection."),
    ] = None,
    run_id: Annotated[
        str,
        typer.Option(help="Report run id written under reports/monitoring/<run_id>."),
    ] = get_settings().default_monitoring_run_id,
    min_edge: Annotated[
        float,
        typer.Option(help="Minimum edge threshold for accepted opportunities."),
    ] = get_settings().default_min_edge,
    min_confidence: Annotated[
        float,
        typer.Option(help="Minimum confidence threshold for accepted opportunities."),
    ] = get_settings().default_min_confidence,
    min_liquidity: Annotated[
        float,
        typer.Option(help="Minimum executable liquidity threshold."),
    ] = get_settings().default_min_liquidity,
    fee_per_contract: Annotated[
        float,
        typer.Option(help="Fee per contract used in EV scoring."),
    ] = 0.0,
    slippage_per_contract: Annotated[
        float,
        typer.Option(help="Slippage per contract used in EV scoring."),
    ] = 0.0,
) -> None:
    report_dir = operations.scan_kalshi_ev(
        artifact_dir=artifact_dir,
        database_path=database_path,
        expected_feature_version=expected_feature_version,
        expected_split_manifest_id=expected_split_manifest_id,
        run_id=run_id,
        min_edge=min_edge,
        min_confidence=min_confidence,
        min_liquidity=min_liquidity,
        fee_per_contract=fee_per_contract,
        slippage_per_contract=slippage_per_contract,
        collect_fresh=collect_fresh,
        access_key=access_key,
        private_key=private_key,
        base_url=base_url,
    )
    typer.echo(str(report_dir))


@app.command("review-monitoring-report")
def review_monitoring_report(
    run_id: Annotated[
        str,
        typer.Option(help="Monitoring run id written under reports/monitoring/<run_id>."),
    ] = get_settings().default_monitoring_report_run_id,
) -> None:
    report_dir = operations.report_monitoring_run(run_id=run_id)
    typer.echo(str(report_dir))


if __name__ == "__main__":
    app()
