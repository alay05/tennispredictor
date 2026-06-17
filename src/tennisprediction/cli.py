from __future__ import annotations

import typer

from tennisprediction import __version__
from tennisprediction.config import get_settings
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


if __name__ == "__main__":
    app()
