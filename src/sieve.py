# ============================================================
# src/sieve.py — Sieve module
# ============================================================
# Composes sanitise + anonymise into a single operation.
# The "T" of Goldilocks's ETL: fetch → sieve → seed.
# ============================================================

from sanitiser import sanitise_export
from anonymiser import anonymise_pipeline


def sieve_export(
    input_path: str,
    sanitised_path: str = "export_clean.json",
    anonymised_path: str = "export_anonymised.json",
) -> str:
    """
    Sieve a raw SnapLogic export — sanitise then anonymise.

    Args:
        input_path:      Path to the raw export.json from SnapLogic fetch
        sanitised_path:  Path for the sanitised intermediate file
        anonymised_path: Path for the final anonymised output

    Returns:
        The path to the final anonymised file.
    """
    sanitise_export(input_path, sanitised_path)
    anonymise_pipeline(sanitised_path, anonymised_path)
    return anonymised_path