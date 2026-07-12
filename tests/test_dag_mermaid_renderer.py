import os
import pytest

if not os.environ.get("RUN_INTEGRATION"):
    pytest.skip(
        "integration test — needs a live Neo4j (set RUN_INTEGRATION=1 to run)",
        allow_module_level=True,
    )

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pathlib import Path
from neo4j import GraphDatabase

from goldilocks_cli.core.dag_builder import build_dag
from goldilocks_cli.core.dag_mermaid_renderer import render_dag_mermaid


uri = os.environ["NEO4J_URI"]
user = os.environ.get("NEO4J_USER", "neo4j")
password = os.environ["NEO4J_PASSWORD"]

with GraphDatabase.driver(uri, auth=(user, password)) as driver:
    with driver.session() as session:
        dag = build_dag(
            session,
            "Dayforce to DIESE Job Titles"
        )

diagram = render_dag_mermaid(dag)

output = Path("diagrams/dayforce_traversal_dag.mmd")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(diagram, encoding="utf-8")

print(f"✅ Saved: {output}")