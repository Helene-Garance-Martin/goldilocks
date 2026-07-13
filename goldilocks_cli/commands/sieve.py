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
        # honest fallback — no animation; the command renders the facts
        try:
            san = sanitise_export(input, sanitised)
            anon = anonymise_pipeline(sanitised, anonymised)
        except Exception as e:
            typer.echo(f"{RED}❌ Sieve failed: {e}{RESET}\n")
            raise typer.Exit(1)
        typer.echo(
            f"🧹 Sanitised {len(san['pipelines'])} pipeline(s) → {san['output']}"
        )
        typer.echo(
            f"🔒 Anonymised — orgs: {anon['orgs']}, urls: {anon['urls']}, "
            f"emails: {anon['emails']}, credentials: {anon['credentials']}, guids: {anon['guids']}"
        )
        from goldilocks_cli.core.anonymiser import print_leak_report
        print_leak_report(anon["leak_findings"])
        typer.echo(f"{GREEN}🫧 Sieve complete — data ready to seed.{RESET}\n")
        return

    from goldilocks_cli.core.sieveDemo import SieveAnimation

    anim = SieveAnimation()
    anim.start()

    try:
        sanitise_export(input, sanitised, on_progress=anim.update)
        anon = anonymise_pipeline(sanitised, anonymised, on_progress=anim.update)
    except Exception as e:
        anim.abort()  # joins the thread AND restores the terminal
        typer.echo(f"\n{RED}❌ Sieve failed: {e}{RESET}\n")
        raise typer.Exit(1)

    anim.finish()
    # the summary the alternate screen used to swallow — now it lands
    # in scrollback where it belongs
    from goldilocks_cli.commands.anonymise import render_anonymise_summary
    render_anonymise_summary(anon)
    typer.echo(f"\n{GOLD}{BOLD}   data ready to seed — fetch → sieve → seed{RESET}\n")