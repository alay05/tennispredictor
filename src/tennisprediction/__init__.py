"""Bootstrap package for the ATP tennis prediction project."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("tennisprediction")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = ["__version__"]
