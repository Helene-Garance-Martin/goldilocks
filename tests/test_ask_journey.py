# tests/test_ask_journey.py
# ============================================================
# 🫧 GOLDILOCKS — ask routing, transparency and egress (F4–F6)
# ============================================================
# Three small promises:
#   - easter eggs delight without hijacking real questions (F6)
#   - the user is told when data leaves the machine (F5)
#   - the generated Cypher is shown, but printed by the command
#     layer rather than by core (F4)
# ============================================================

import typer
from typer.testing import CliRunner

from goldilocks_cli.core.agent import is_fun_trigger

runner = CliRunner()


def make_app():
    from goldilocks_cli.commands.ask import ask
    app = typer.Typer()
    app.command()(ask)
    return app


# ------------------------------------------------------------
# F6 — easter eggs are eggs, not keywords
# ------------------------------------------------------------

import pytest


@pytest.mark.parametrize("question", [
    "how do I install goldilocks-curls?",
    "is this sizing just right for prod?",
    "which pipeline has the most curls of logic?",
    "what does the just right threshold mean for large projects?",
])
def test_real_questions_do_not_hit_the_fun_path(question):
    # REGRESSION GUARD (F6): substring matching used to send genuine
    # questions to a temperature-1.0 joke — and spend an API call.
    assert is_fun_trigger(question) is False


@pytest.mark.parametrize("question", [
    "rags to dags",
    "rags to dags?",
    "hey, rags to dags!",
    "boucles d'or",
    "Boucles d'Or!",
    "is it just right?",
])
def test_the_eggs_still_hatch(question):
    assert is_fun_trigger(question) is True


def test_curls_is_no_longer_a_trigger():
    # it became the package name — goldilocks-curls
    from goldilocks_cli.core.agent import FUN_TRIGGERS
    assert "curls" not in FUN_TRIGGERS


# ------------------------------------------------------------
# F5 — say when data leaves the machine
# ------------------------------------------------------------

def test_agent_path_announces_the_egress(monkeypatch, tmp_path):
    import goldilocks_cli.commands.ask as ask_module

    monkeypatch.setattr(
        ask_module, "_read_current_graph_state", lambda: {"pipeline_count": 3}
    )

    import goldilocks_cli.core.agent as agent
    monkeypatch.setattr(agent, "ask_goldilocks", lambda *a, **k: "an answer")

    result = runner.invoke(make_app(), ["how many pipelines are there?"])

    assert "sending anonymised graph results to Anthropic" in result.output


def test_local_path_says_nothing_leaves(monkeypatch, tmp_path):
    # the token-risk path reads the file on disk and contacts nobody
    export = tmp_path / "export_anonymised.json"
    export.write_text('{"name": "ORG_1 pipeline", "snap_map": {}}', encoding="utf-8")

    result = runner.invoke(
        make_app(),
        ["which snaps are a token risk?", "--input", str(export)],
    )

    assert "nothing leaves this machine" in result.output
    assert "Anthropic" not in result.output


# ------------------------------------------------------------
# F4 — transparency, printed by the command layer
# ------------------------------------------------------------

def test_core_does_not_print_the_generated_cypher():
    # REGRESSION GUARD (F4): core stays silent; the callback carries it.
    import inspect
    from goldilocks_cli.core import agent

    source = inspect.getsource(agent.ask_goldilocks)
    assert "print(" not in source
    assert "on_query" in source


def test_on_query_callback_receives_the_cypher(monkeypatch):
    from goldilocks_cli.core import agent

    monkeypatch.setenv("NEO4J_URI", "neo4j+s://fake.invalid")
    monkeypatch.setenv("NEO4J_PASSWORD", "pw")

    seen = []
    cypher = "MATCH (p:Pipeline) RETURN p.name"

    class FakeSession:
        def run(self, query, **params):
            return [{"p.name": "ORG_1 pipeline"}]

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    class FakeDriver:
        def session(self):
            return FakeSession()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(
        agent, "GraphDatabase", type("D", (), {"driver": staticmethod(lambda *a, **k: FakeDriver())})
    )
    monkeypatch.setattr(agent, "generate_cypher", lambda q, s: cypher)
    monkeypatch.setattr(agent, "explain_results", lambda q, r: "plain english answer")

    answer = agent.ask_goldilocks(
        "how many pipelines?", graph_checked=True, on_query=seen.append
    )

    assert seen == [cypher]
    assert answer == "plain english answer"


def test_command_renders_the_query_to_the_user(monkeypatch):
    import goldilocks_cli.commands.ask as ask_module
    import goldilocks_cli.core.agent as agent

    monkeypatch.setattr(
        ask_module, "_read_current_graph_state", lambda: {"pipeline_count": 2}
    )

    def fake_ask(question, graph_checked=False, on_query=None):
        if on_query:
            on_query("MATCH (p:Pipeline) RETURN count(p)")
        return "there are two"

    monkeypatch.setattr(agent, "ask_goldilocks", fake_ask)

    result = runner.invoke(make_app(), ["how many pipelines?"])

    assert "Generated query" in result.output
    assert "MATCH (p:Pipeline) RETURN count(p)" in result.output
    assert "there are two" in result.output
