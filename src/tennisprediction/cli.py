from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from tennisprediction import __version__
from tennisprediction.backtesting.schemas import DecisionThresholds
from tennisprediction.config import get_settings
from tennisprediction.kalshi.client import AllowedMarketStatus, KalshiReadClient
from tennisprediction.kalshi.jobs import (
    collect_kalshi_snapshots as collect_kalshi_snapshot_job,
)
from tennisprediction.logging import configure_logging
from tennisprediction.monitoring.reports import (
    render_live_monitor_console,
    write_live_monitor_reports,
)
from tennisprediction.monitoring.scan import run_kalshi_ev_scan

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
    client = KalshiReadClient(
        access_key=access_key,
        private_key=private_key,
        base_url=base_url,
    )
    try:
        persisted_path = collect_kalshi_snapshot_job(
            client,
            database_path=database_path,
            page_limit=page_limit,
            status=status,
        )
    finally:
        client.close()

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
    ] = "live-monitor",
    min_edge: Annotated[
        float,
        typer.Option(help="Minimum edge threshold for accepted opportunities."),
    ] = 0.05,
    min_confidence: Annotated[
        float,
        typer.Option(help="Minimum confidence threshold for accepted opportunities."),
    ] = 0.35,
    min_liquidity: Annotated[
        float,
        typer.Option(help="Minimum executable liquidity threshold."),
    ] = 5.0,
    fee_per_contract: Annotated[
        float,
        typer.Option(help="Fee per contract used in EV scoring."),
    ] = 0.0,
    slippage_per_contract: Annotated[
        float,
        typer.Option(help="Slippage per contract used in EV scoring."),
    ] = 0.0,
) -> None:
    settings = get_settings()
    result = run_kalshi_ev_scan(
        artifact_dir=artifact_dir,
        database_path=database_path,
        expected_feature_version=expected_feature_version,
        expected_split_manifest_id=expected_split_manifest_id,
        thresholds=DecisionThresholds(
            min_edge=min_edge,
            min_confidence=min_confidence,
            min_liquidity=min_liquidity,
            fee_per_contract=fee_per_contract,
            slippage_per_contract=slippage_per_contract,
            assumption_notes="read-only live monitor thresholds",
        ),
        run_id=run_id,
        collect_fresh=collect_fresh,
        access_key=access_key,
        private_key=private_key,
        base_url=base_url,
    )
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


if __name__ == "__main__":
    app()
