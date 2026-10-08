"""Send ``python -m omids_validator`` to the command-line interface.

The installed ``omids_validator`` command points directly to ``cli.main``.
This small adapter gives module execution the same behavior.
"""

from omids_validator.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
