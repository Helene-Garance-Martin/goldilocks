# tests/test_agent_helpers.py
# ============================================================
# 🫧 GOLDILOCKS — agent helper + security guard tests
# ============================================================
# clean_answer / clean_cypher / validate_query are pure functions.
# No network, no Neo4j, no LLM calls anywhere in this module.
#
# NOTE (review finding, testability): agent.py creates
# `client = anthropic.Anthropic()` at import time and imports the
# neo4j driver at module level. The current SDK tolerates a missing
# API key at construction, so this import works today — but the
# coupling means these three pure functions drag the Anthropic SDK
# and Neo4j driver into every test run. Consider moving them (and
# lazy-initialising the client) so the pure logic is importable
# alone.
# ============================================================

import pytest

from goldilocks_cli.core.agent import clean_answer, clean_cypher
from goldilocks_cli.core.security import validate_query, safe_query, wipes_context


# ------------------------------------------------------------
# clean_answer — stop-marker stripping
# ------------------------------------------------------------

@pytest.mark.parametrize("marker", [
    "µEnd File",
    "# EdwardDali",
    '{"my_key"',
    '{"my key"',
])
def test_clean_answer_strips_each_stop_marker(marker):
    text = f"A useful answer.\n{marker} trailing hallucination"
    assert clean_answer(text) == "A useful answer."


def test_clean_answer_strips_only_after_first_marker():
    text = 'Real answer µEnd File junk # EdwardDali more junk'
    assert clean_answer(text) == "Real answer"


def test_clean_answer_passes_clean_text_through():
    assert clean_answer("  Just an answer.  ") == "Just an answer."


def test_clean_answer_marker_at_start_yields_empty():
    # Pins the edge: if the model output is *only* hallucinated tail,
    # the caller receives an empty string. Worth a guard upstream.
    assert clean_answer('{"my_key": 1}') == ""


# ------------------------------------------------------------
# clean_cypher — fence stripping
# ------------------------------------------------------------

def test_clean_cypher_strips_cypher_fence():
    fenced = "```cypher\nMATCH (p:Pipeline) RETURN p.name\n```"
    assert clean_cypher(fenced) == "MATCH (p:Pipeline) RETURN p.name"


def test_clean_cypher_strips_bare_fence():
    fenced = "```\nMATCH (n) RETURN n\n```"
    assert clean_cypher(fenced) == "MATCH (n) RETURN n"


def test_clean_cypher_leaves_plain_query_untouched():
    q = "MATCH (p:Pipeline) RETURN p.name"
    assert clean_cypher(q) == q


def test_clean_cypher_ignores_fence_after_preamble():
    # PINS CURRENT BEHAVIOUR: fences are only stripped when the text
    # *starts* with ``` — a "Here's your query:\n```cypher..." reply
    # keeps its fences and will then fail in Neo4j. The prompt forbids
    # fences, so this is defence-in-depth worth tightening.
    text = "Here is the query:\n```cypher\nMATCH (n) RETURN n\n```"
    assert "```" in clean_cypher(text)


# ------------------------------------------------------------
# validate_query — allow/deny
# ------------------------------------------------------------

@pytest.mark.parametrize("query", [
    "MATCH (p:Pipeline) RETURN p.name",
    "MATCH (p:Pipeline) WHERE p.name CONTAINS 'X' RETURN p.name AS n ORDER BY n LIMIT 5",
    "MATCH (p)-[:HAS_SNAP]->(s) WITH p, count(s) AS c RETURN p.name, c",
    "OPTIONAL MATCH (a)-[:CALLS]->(b) RETURN a.name, collect(DISTINCT b.name)",
    "UNWIND [1,2,3] AS x RETURN x",
])
def test_validate_allows_read_queries(query):
    validate_query(query)  # must not raise


@pytest.mark.parametrize("query", [
    "CREATE (n:Evil) RETURN n",
    "MATCH (n) DELETE n",
    "MATCH (n) DETACH DELETE n",
    "MERGE (n:Sneaky {id: 1}) RETURN n",
    "MATCH (n) SET n.pwned = true RETURN n",
    "MATCH (n) REMOVE n.name RETURN n",
    "DROP INDEX whatever",
    "CALL db.labels()",
    "LOAD CSV FROM 'file:///etc/passwd' AS row RETURN row",
    "MATCH (n) RETURN apoc.text.join(['a'],'')",   # APOC
    "FOREACH (x IN [1] | CREATE (:N))",
    "match (n) delete n",                          # case-insensitivity
])
def test_validate_rejects_write_and_procedure_queries(query):
    with pytest.raises(ValueError):
        validate_query(query)


def test_validate_allows_properties_containing_forbidden_words():
    # REGRESSION GUARD (was S1): word-boundary matching means reads of
    # p.created, created_pipelines, n.dataset are legitimate again.
    validate_query("MATCH (p:Pipeline) RETURN p.name AS created_pipelines")
    validate_query("MATCH (p:Pipeline) RETURN p.created")
    validate_query("MATCH (n) RETURN n.dataset")


def test_validate_blocks_call_in_all_spellings():
    # REGRESSION GUARD (was S1): "CALL{...}" (Neo4j 5 subquery syntax,
    # no space) used to slip past the "CALL " deny entry.
    with pytest.raises(ValueError):
        validate_query("CALL{MATCH (n) RETURN n} RETURN 1")


def test_url_literals_in_read_queries_are_allowed_by_design():
    # DESIGN CONTRACT: the old FORBIDDEN_PATTERNS (file://, http://)
    # constant was never enforced and has been deleted — URL string
    # literals are harmless in read-only Cypher once CALL, LOAD CSV
    # and APOC are word-boundary blocked. The graph legitimately
    # stores (anonymised) URLs users will query against.
    validate_query("MATCH (s) WHERE s.url = 'https://api.org-1.com/endpoint-1' RETURN s")


# ------------------------------------------------------------
# safe_query — validates before touching the session
# ------------------------------------------------------------

def test_safe_query_validates_before_running():
    class ExplodingSession:
        def run(self, *a, **k):
            raise AssertionError("session.run must not be reached for a forbidden query")

    with pytest.raises(ValueError):
        safe_query(ExplodingSession(), "CREATE (n) RETURN n")


def test_safe_query_passes_params_through():
    class FakeResult(list):
        pass

    class FakeSession:
        def run(self, query, **params):
            assert params == {"name": "Demo"}
            return FakeResult([{"n": 1}])

    rows = safe_query(FakeSession(), "MATCH (p {name: $name}) RETURN p", name="Demo")
    assert rows == [{"n": 1}]


# ------------------------------------------------------------
# wipes_context
# ------------------------------------------------------------

@pytest.mark.parametrize("snap_type,expected", [
    ("httpclient", True),
    ("SFTP_GET", True),      # case-insensitive
    ("mapper", False),
    ("pipeexec", False),
])
def test_wipes_context(snap_type, expected):
    assert wipes_context(snap_type) is expected
