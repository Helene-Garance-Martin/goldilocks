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

from rich.console import Console
from neo4j import GraphDatabase

from goldilocks_cli.core.dag_builder import build_dag
from goldilocks_cli.core.dag_ascii_renderer import render_dag_ascii


console = Console()

uri = os.environ["NEO4J_URI"]
user = os.environ.get("NEO4J_USER", "neo4j")
password = os.environ["NEO4J_PASSWORD"]

with GraphDatabase.driver(uri, auth=(user, password)) as driver:
    with driver.session() as session:

        dag = build_dag(
            session,
            "Dayforce to DIESE Job Titles"
        )

        tree = render_dag_ascii(dag)

        console.print(tree)
        console.print()
        console.print()
        