# src/security.py
# ------------------------------------------------------------
# GOLDILOCKS — Security & Query Guard Rails
# ------------------------------------------------------------
# Protects Neo4j from injection attacks and enforces
# read-only access for the AI agent layer.
# ------------------------------------------------------------

import re
from typing import Any

# ------------------------------------------------------------
# READ-ONLY GUARD — allowed/forbidden Cypher operations
# ------------------------------------------------------------

# Design note: this is a deny-list, deliberately. A true allow-list
# breaks on every function, label and alias the LLM legitimately uses;
# the read-only guarantee is enforced in layers — prompt rules, this
# guard, and (recommended) a read-only Neo4j credential underneath.
# URL literals inside read-only queries are harmless once CALL /
# LOAD CSV / APOC are blocked, so the old FORBIDDEN_PATTERNS
# (file://, http://) list is gone rather than half-enforced.

FORBIDDEN_OPERATIONS = [
    "CREATE", "DELETE", "MERGE", "DROP",
    "SET", "REMOVE", "DETACH", "CALL",
    "APOC", "FOREACH",
]

# ------------------------------------------------------------
# VALIDATE QUERY — reject writes, enforce read-only
# ------------------------------------------------------------

def validate_query(query: str) -> None:
    """
    Raise ValueError if query contains forbidden write operations.
    The AI agent must never modify the graph.
    """
    query_upper = query.upper()
    for op in FORBIDDEN_OPERATIONS:
        # word boundaries: block the operation CREATE without rejecting
        # legitimate reads of properties like p.created or n.dataset
        if re.search(rf"\b{op}\b", query_upper):
            raise ValueError(
                f"❌ Forbidden operation '{op}' in query — "
                f"Goldilocks agent is read-only."
            )
    if re.search(r"\bLOAD\s+CSV\b", query_upper):
        raise ValueError(
            "❌ Forbidden operation 'LOAD CSV' in query — "
            "Goldilocks agent is read-only."
        )

# ------------------------------------------------------------
# SAFE QUERY — parameterised query runner
# ------------------------------------------------------------

def safe_query(session: Any, query: str, **params) -> list:
    """
    Run a parameterised Cypher query safely.
    Always validate before executing.
    
    Usage:
        results = safe_query(session, 
            "MATCH (p:Pipeline) WHERE p.name = $name RETURN p",
            name="DEMO-PIPELINE"
        )
    """
    validate_query(query)
    result = session.run(query, **params)
    return [record for record in result]

# ------------------------------------------------------------
# MEMORY WIPE SNAPS — snaps that erase document context
# ------------------------------------------------------------

WIPES_CONTEXT = [
    "httpclient",
    "script",
    "sftp_get",
    "sftp_put",
    "binarytodocument",
    "filereader",
]

def wipes_context(snap_type: str) -> bool:
    """Returns True if this snap type wipes document context."""
    return snap_type.lower() in WIPES_CONTEXT