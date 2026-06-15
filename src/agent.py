# ============================================================
# 🫧 GOLDILOCKS — Pipeline Intelligence Agent
# ============================================================
# Natural language interface to the Neo4j pipeline graph.
# Uses Anthropic API for development, swappable to Ollama.
#
# Two temperatures:
#   0.1 → precise Cypher generation
#   0.5 → warm plain English explanation
# ============================================================

import os
import sys
sys.path.insert(0, os.path.dirname(__file__))

import anthropic
from neo4j import GraphDatabase
from security import validate_query, safe_query

# ------------------------------------------------------------
# CLIENT
# ------------------------------------------------------------

client = anthropic.Anthropic()
# 👆 Swap to ollama.Client() when running locally

# ------------------------------------------------------------
# CYPHER GENERATOR — temperature 0.1 (precise)
# ------------------------------------------------------------

def generate_cypher(question: str, schema: str) -> str:
    """Convert natural language question to Cypher query."""
    
    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=500,
        temperature=0.1,
        messages=[{
            "role": "user",
            "content": f"""You are a Neo4j Cypher expert for a pipeline intelligence platform.

Graph schema:
{schema}

Rules:
- Only use MATCH and RETURN — no CREATE, DELETE, MERGE or SET
- Always return meaningful field names
- Keep queries simple and efficient

Convert this question to Cypher:
{question}

Return ONLY the Cypher query, nothing else."""
        }]
    )
    return response.content[0].text.strip()


# ------------------------------------------------------------
# EXPLAINER — temperature 0.5 (warm)
# ------------------------------------------------------------

def explain_results(question: str, results: list) -> str:
    """Convert Neo4j results to plain English explanation."""

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=500,
        temperature=0.5,
        system="""You are Goldilocks — a pipeline intelligence assistant for arts organisations.
You explain technical pipeline data in plain, friendly English.
Never use jargon without explaining it.
Be concise but warm.
IMPORTANT: Give a complete answer. Never ask follow-up questions.
Never offer to dig deeper. The user will ask another question if needed.""",
        messages=[{
            "role": "user",
            "content": f"""Question: {question}

Data from the graph:
{results}

Answer the question based on this data."""
        }]
    )
    return response.content[0].text.strip()

# ------------------------------------------------------------
# SCHEMA — what Goldilocks knows about the graph
# ------------------------------------------------------------

GRAPH_SCHEMA = """
Nodes:
- Pipeline {id, name, path, complexity}
- Snap {id, label, type, wipes_context, error}

Relationships:
- (Pipeline)-[:HAS_SNAP]->(Snap)
- (Pipeline)-[:CALLS]->(Pipeline)
- (Snap)-[:CONNECTS_TO]->(Snap)

Snap types: httpclient, script, pipeexec, sftp_get, mapper, filter, trigger, default

Important notes:
- Pipeline names may use > as separator e.g. 'DayforceReports>Sharepoint'
- Always use CONTAINS for pipeline name matching, never exact match
- wipes_context = true means the snap clears document context
"""

# ------------------------------------------------------------
# FUN TRIGGERS — temperature 1.0 (creative!)
# ------------------------------------------------------------

FUN_TRIGGERS = ["rags to dags", "boucles d'or", "curls", "just right"]

# ------------------------------------------------------------
# MAIN AGENT FUNCTION
# ------------------------------------------------------------

def ask_goldilocks(question: str) -> str:
    """
    Ask Goldilocks a natural language question about your pipelines.
    
    Flow:
    1. Check for fun triggers (temperature 1.0)
    2. Generate Cypher from question (temperature 0.1)
    3. Run Cypher against Neo4j safely
    4. Explain results in plain English (temperature 0.5)
    """

    # ── Fun triggers ───────────────────────────────────────
    if any(trigger in question.lower() for trigger in FUN_TRIGGERS):
        response = client.messages.create(
            model="claude-opus-4-5",
            max_tokens=200,
            temperature=1.0,
            messages=[{
                "role": "user",
                "content": f"You are Goldilocks, a witty pipeline intelligence platform. Respond playfully to: {question}"
            }]
        )
        return response.content[0].text.strip()

    uri      = os.environ["NEO4J_URI"]
    user     = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]

    try:
        with GraphDatabase.driver(uri, auth=(user, password)) as driver:
            with driver.session() as session:

                # ── Empty graph guard ──────────────────────
                total = session.run("MATCH (n) RETURN count(n) AS total").single()["total"]
                if total == 0:
                    return (
                        "⚠️  Your graph is empty!\n\n"
                        "💡 Run the full flow first:\n"
                        "   goldilocks fetch\n"
                        "   goldilocks sanitise\n"
                        "   goldilocks anonymise\n"
                        "   goldilocks seed\n\n"
                        "Or run everything at once:\n"
                        "   goldilocks run"
                    )

                # ── Generate Cypher ────────────────────────
                cypher = generate_cypher(question, GRAPH_SCHEMA)
                print(f"\n🔍 Generated query: {cypher}\n")

                # ── Validate and run safely ────────────────
                validate_query(cypher)
                results = safe_query(session, cypher)

                if not results:
                    return "🤷 No data found for that question. Try seeding more pipelines first!"

                # ── Explain in plain English ───────────────
                return explain_results(question, results)

    except Exception as e:
        return f"❌ {e}"