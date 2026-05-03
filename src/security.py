# src/security.py
# ------------------------------------------------------------
# GOLDILOCKS — Security & Query Guard Rails
# ------------------------------------------------------------
# Protects Neo4j from injection attacks and enforces
# read-only access for the AI agent layer.
# ------------------------------------------------------------

from typing import Any

# ------------------------------------------------------------
# READ-ONLY GUARD — allowed/forbidden Cypher operations
# ------------------------------------------------------------

ALLOWED_OPERATIONS = [
    "MATCH", "RETURN", "WHERE", "WITH",
    "ORDER BY", "LIMIT", "SKIP", "COUNT",
    "COLLECT", "DISTINCT", "AS", "AND", "OR"
]

FORBIDDEN_OPERATIONS = [
    "CREATE", "DELETE", "MERGE", "DROP",
    "SET", "REMOVE", "DETACH", "CALL"
]

# security.py — add these:
SENSITIVE_KEYS = [
    "password", "token", "secret", "api_key", "apikey",
    "client_secret", "bearer", "Authorization",
    "access_token", "refresh_token", "private_key",
]

SENSITIVE_INDICATORS = [
    "bearer", "password", "secret",
    "token", "credential", "api_key",
    "authorization", "access_token",
]

# ------------------------------------------------------------
# REDACT sensitive values 
# ------------------------------------------------------------

def redact_sensitive_value(value: str) -> str:
    """Replace sensitive values with redacted placeholder."""
    if any(ind in value.lower() for ind in SENSITIVE_INDICATORS):
        return "***REDACTED***"
    return value

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
        if op in query_upper:
            raise ValueError(
                f"❌ Forbidden operation '{op}' in query — "
                f"Goldilocks agent is read-only."
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
            name="DIESE-SHAREPOINT"
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