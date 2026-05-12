import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from neo4j import GraphDatabase
from dag_builder import build_dag

uri = os.environ["NEO4J_URI"]
user = os.environ.get("NEO4J_USER", "neo4j")
password = os.environ["NEO4J_PASSWORD"]

with GraphDatabase.driver(uri, auth=(user, password)) as driver:
    with driver.session() as session:
        dag = build_dag(session, "Dayforce Job Titles to DynamoDB")

print(dag.model_dump_json(indent=2))