# ============================================================
# 🐻 GOLDILOCKS — Pipeline Describer (Neo4j version)
# ============================================================
# Queries Neo4j graph to generate plain English pipeline
# summaries. Much richer than reading JSON directly!
#
# Run:
#   python src/describer.py
# ============================================================

import os
from neo4j import GraphDatabase


# ------------------------------------------------------------
# Lambda functions
# ------------------------------------------------------------

# Plain English description per snap type
describe_type = lambda snap_type: (
    "fetches files from SFTP"      if snap_type == "sftp_get"    else
    "sends files via SFTP"         if snap_type == "sftp_put"    else
    "sends data via HTTP"          if snap_type == "httpclient"  else
    "runs custom logic"            if snap_type == "script"      else
    "calls a child pipeline"       if snap_type == "pipeexec"    else
    "transforms data"              if snap_type == "mapper"      else
    "queries a database"           if snap_type == "db_select"   else
    "writes to a database"         if snap_type == "db_insert"   else
    "filters records"              if snap_type == "filter"      else
    None
)

# Complexity from snap count
get_complexity = lambda count: (
    "High"   if count > 10 else
    "Medium" if count > 5  else
    "Low"
)


# ------------------------------------------------------------
# Neo4j queries
# ------------------------------------------------------------

def get_pipeline_summary(session, pipeline_name: str) -> dict:
    """Query Neo4j for a single pipeline's full details."""

    # Get snaps
    snaps_result = session.run(
        """
        MATCH (p:Pipeline {name: $name})-[:HAS_SNAP]->(s:Snap)
        RETURN s.label AS label, s.type AS type, s.error AS error
        """,
        name=pipeline_name
    )
    snaps = [dict(r) for r in snaps_result]

    # Get child pipelines
    calls_result = session.run(
        """
        MATCH (p:Pipeline {name: $name})-[:CALLS]->(child:Pipeline)
        RETURN child.name AS child_name
        """,
        name=pipeline_name
    )
    calls = [r["child_name"] for r in calls_result]

    # Get parent pipelines
    called_by_result = session.run(
        """
        MATCH (parent:Pipeline)-[:CALLS]->(p:Pipeline {name: $name})
        RETURN parent.name AS parent_name
        """,
        name=pipeline_name
    )
    called_by = [r["parent_name"] for r in called_by_result]

    return {
        "name":      pipeline_name,
        "snaps":     snaps,
        "calls":     calls,
        "called_by": called_by,
    }


def get_all_pipeline_names(session) -> list:
    """Get all pipeline names from Neo4j."""
    result = session.run("MATCH (p:Pipeline) RETURN p.name AS name ORDER BY p.name")
    return [r["name"] for r in result]


# ------------------------------------------------------------
# Describer
# ------------------------------------------------------------

def describe_pipeline_from_graph(summary: dict) -> str:
    """Generate plain English description from Neo4j graph data."""

    name   = summary["name"]
    snaps  = summary["snaps"]
    calls  = summary["calls"]
    called_by = summary["called_by"]

    # What it does — deduplicated step descriptions
    steps = list(dict.fromkeys(
    desc for snap in snaps
    if (desc := describe_type(snap.get("type", "")))
    ))

    # Complexity and error handling
    snap_count = len(snaps)
    complexity = get_complexity(snap_count)

    errors = [s.get("error", "") for s in snaps if s.get("error")]
    all_fail = all(e == "fail" for e in errors) if errors else False
    error_summary = "All snaps stop on error ⛔" if all_fail else "Mixed error handling ⚠️"

    # Build output
    lines = [
        f"🐻 Pipeline: {name}",
        "━" * 40,
        "",
    ]

    if steps:
        lines.append("What it does:")
        for step in steps:
            lines.append(f"  - {step}")

    lines += [
        "",
        f"Complexity:      {complexity} ({snap_count} snaps)",
        f"Error handling:  {error_summary}",
    ]

    if calls:
        lines.append("")
        lines.append("Relationships:")
        lines += [f"  - Calls:     {child}" for child in calls]

    if called_by:
        if not calls:
            lines.append("")
            lines.append("Relationships:")
        lines += [f"  - Called by: {parent}" for parent in called_by]

    return "\n".join(lines)


def describe_all_from_graph(session) -> str:
    """Describe all pipelines in Neo4j."""
    names     = get_all_pipeline_names(session)
    divider   = "\n" + "═" * 40 + "\n"
    
    summaries = [
    describe_pipeline_from_graph(get_pipeline_summary(session, name))
    for name in names
    ]

    return divider.join(summaries)


def describe_token_risks(pipeline_name: str, pipeline: dict) -> str:
    """Describe token risks for a pipeline using token_analyser."""
    from token_analyser import find_token_references, format_token_report
    findings = find_token_references(pipeline)
    return format_token_report(pipeline_name, findings)

# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    uri      = os.environ["NEO4J_URI"]
    user     = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        driver.verify_connectivity()
        with driver.session() as session:
            print(describe_all_from_graph(session))


if __name__ == "__main__":
    main()


# ------------------------------------------------------------
# Public function for pie.py ask command
# ------------------------------------------------------------

def describe_from_neo4j() -> str:
    """Called by pie.py ask command — returns full description."""
    uri      = os.environ["NEO4J_URI"]
    user     = os.environ.get("NEO4J_USER", "neo4j")
    password = os.environ["NEO4J_PASSWORD"]

    with GraphDatabase.driver(uri, auth=(user, password)) as driver:
        with driver.session() as session:
            return describe_all_from_graph(session)