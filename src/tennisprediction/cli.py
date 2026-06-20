from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from tennisprediction import __version__
from tennisprediction.config import get_settings
from tennisprediction.kalshi.client import AllowedMarketStatus, KalshiReadClient
from tennisprediction.kalshi.jobs import (
    collect_kalshi_snapshots as collect_kalshi_snapshot_job,
)
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


if __name__ == "__main__":
    app()
