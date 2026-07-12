"""Allow `python -m goldilocks_cli` alongside the `goldilocks` script."""
from goldilocks_cli.cli import app

if __name__ == "__main__":
    app()
