# commands/sieve.py
import typer
from goldilocks_cli.colours import CYAN, GREEN, RED, GOLD, BOLD, RESET


def sieve(
    input: str = typer.Option(..., help="Path to raw export.json"),
    sanitised: str = typer.Option("export_clean.json", help="Sanitised intermediate"),
    anonymised: str = typer.Option("export_anonymised.json", help="Final anonymised output"),
    plain: bool = typer.Option(False, "--plain", help="Skip animation (CI/logs)"),
):
    """
    🫧 Sieve a raw pipeline export — sanitise and anonymise in one pass.

    fetch → sieve → seed
    """
    typer.echo(f"{GOLD}🫧 Sieving pipeline export...{RESET}")
    typer.echo(f"   Input:       {input}")
    typer.echo(f"   Anonymised:  {anonymised}\n")

    from goldilocks_cli.core.sanitiser import sanitise_export
    from goldilocks_cli.core.anonymiser import anonymise_pipeline

    if plain:
        # honest fallback — no animation, plain prints from the modules
        try:
            sanitise_export(input, sanitised)
            anonymise_pipeline(sanitised, anonymised)
        except Exception as e:
            typer.echo(f"{RED}❌ Sieve failed: {e}{RESET}\n")
            raise typer.Exit(1)
        typer.echo(f"{GREEN}🫧 Sieve complete — data ready to seed.{RESET}\n")
        return

    from goldilocks_cli.core.sieveDemo import SieveAnimation

    anim = SieveAnimation()
    anim.start()

    try:
        sanitise_export(input, sanitised, on_progress=anim.update)
        anonymise_pipeline(sanitised, anonymised, on_progress=anim.update)
    except Exception as e:
        anim.abort()  # joins the thread AND restores the terminal
        typer.echo(f"\n{RED}❌ Sieve failed: {e}{RESET}\n")
        raise typer.Exit(1)

    anim.finish()
    typer.echo(f"{GOLD}{BOLD}   data ready to seed — fetch → sieve → seed{RESET}\n")