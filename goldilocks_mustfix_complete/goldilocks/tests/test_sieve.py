# tests/test_sieve.py
# ============================================================
# 🫧 GOLDILOCKS — sieve chaining tests
# ============================================================
# NOTE: the brief asked for "sieve (src-level)" tests, but the
# sanitise→anonymise chaining does not live in src/ — it lives in
# commands/sieve.py (src/sieveDemo.py is only the animation).
# These tests therefore exercise the command through Typer's
# CliRunner in --plain mode, which is the honest unit-testable
# path: no alternate screen, no threads, no animation.
#
# The animated path (SieveAnimation + threads + terminal control)
# is NOT unit-testable in any meaningful way — it needs a TTY and
# wall-clock time. Keep it covered by the standalone demo
# (python src/sieveDemo.py) as a manual smoke test.
# ============================================================

import json

import typer
from typer.testing import CliRunner

from conftest import TEST_ORG

runner = CliRunner()


def make_app():
    from goldilocks_cli.commands.sieve import sieve
    app = typer.Typer()
    app.command()(sieve)
    return app


def test_plain_sieve_chains_sanitise_then_anonymise(export_file, tmp_path, clean_anonymiser):
    sanitised = tmp_path / "clean.json"
    anonymised = tmp_path / "anon.json"

    result = runner.invoke(
        make_app(),
        [
            "--input", str(export_file),
            "--sanitised", str(sanitised),
            "--anonymised", str(anonymised),
            "--plain",
        ],
    )

    assert result.exit_code == 0
    # both intermediate and final files exist at the requested paths
    assert sanitised.exists()
    assert anonymised.exists()

    # the intermediate really is the sanitised form (noise stripped,
    # org names still present)…
    clean = json.loads(sanitised.read_text(encoding="utf-8"))
    assert "render_map" not in clean["entries"][0]
    assert TEST_ORG in sanitised.read_text(encoding="utf-8")

    # …and the final really is the anonymised form of that intermediate
    final_text = anonymised.read_text(encoding="utf-8")
    assert TEST_ORG not in final_text
    assert "ORG_1" in final_text
    assert "Sieve complete" in result.output


def test_plain_sieve_missing_input_fails_honestly(tmp_path, clean_anonymiser):
    # REGRESSION GUARD (was E1): a missing input now raises in the core
    # functions, the plain sieve path catches it, reports the failure,
    # and exits non-zero. No false "Sieve complete".
    sanitised = tmp_path / "clean.json"
    anonymised = tmp_path / "anon.json"

    result = runner.invoke(
        make_app(),
        [
            "--input", str(tmp_path / "does-not-exist.json"),
            "--sanitised", str(sanitised),
            "--anonymised", str(anonymised),
            "--plain",
        ],
    )

    assert result.exit_code == 1
    assert "Sieve failed" in result.output
    assert "Sieve complete" not in result.output
    assert not anonymised.exists()


def test_sieve_animation_update_maps_phases_to_halves():
    # The one genuinely unit-testable piece of the animation: the
    # on_progress → progress-target mapping. sanitising fills 0→0.5,
    # anonymising fills 0.5→1.0.
    from goldilocks_cli.core.sieveDemo import SieveAnimation

    anim = SieveAnimation()
    anim.update("sanitising", 1, 2, "halfway")
    assert anim.target == 0.25
    anim.update("sanitising", 2, 2, "done")
    assert anim.target == 0.5
    anim.update("anonymising", 1, 2, "creds")
    assert anim.target == 0.75
    anim.update("anonymising", 2, 2, "orgs")
    assert anim.target == 1.0
    # zero-total guard
    anim.update("anonymising", 0, 0, "empty")
    assert anim.target == 0.5
