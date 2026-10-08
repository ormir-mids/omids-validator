"""Validate MIDS-formatted musculoskeletal imaging datasets."""

from importlib.metadata import PackageNotFoundError, version


try:
    __version__ = version("omids-validator")
except PackageNotFoundError:
    # Source-only use has no installed distribution metadata. Release versions
    # are defined only in pyproject.toml.
    __version__ = "0+unknown"
