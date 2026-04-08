import os
from neo4j import GraphDatabase

def verify(driver) -> None:
    driver.verify_connectivity()
    print("✅ Connectivity verified")

def seed_pipeline(tx, pipeline_id: str):
    """
    Write transaction function:
    - MERGE one Pipeline
    - MERGE three Snaps (Extract/Transform/Load)
    - MERGE two CONNECTS_TO relationships
    Returns a small, fully-materialised summary (not a Neo4j result cursor).
    """
    # Pipeline node
    tx.run(
        "MERGE (p:Pipeline {id: $id}) "
        "SET p.name = $name",
        id=pipeline_id,
        name="Demo Pipeline 001"
    )

    # Snaps
    snaps = [
        {"id": "snap_extract_1", "name": "Extract Customers", "kind": "Extract"},
        {"id": "snap_transform_1", "name": "Clean & Map", "kind": "Transform"},
        {"id": "snap_load_1", "name": "Load to SQL", "kind": "Load"},
    ]
    tx.run(
        """
        UNWIND $snaps AS s
        MERGE (n:Snap {id: s.id})
        SET n.name = s.name, n.kind = s.kind
        """,
        snaps=snaps
    )

    # Connect snaps
    edges = [
        {"from": "snap_extract_1", "to": "snap_transform_1"},
        {"from": "snap_transform_1", "to": "snap_load_1"},
    ]
    tx.run(
        """
        UNWIND $edges AS e
        MATCH (a:Snap {id: e.from})
        MATCH (b:Snap {id: e.to})
        MERGE (a)-[:CONNECTS_TO]->(b)
        """,
        edges=edges
    )

    # Attach snaps to pipeline (optional but useful for scoping queries)
    tx.run(
        """
        MATCH (p:Pipeline {id: $pid})
        MATCH (n:Snap)
        WHERE n.id IN $snap_ids
        MERGE (p)-[:HAS_SNAP]->(n)
        """,
        pid=pipeline_id,
        snap_ids=[s["id"] for s in snaps]
    )

    # Return a materialised summary
    return {
        "pipeline_id": pipeline_id,
        "snaps": [s["name"] for s in snaps],
        "edges": [(e["from"], e["to"]) for e in edges],
    }

def count_nodes(tx):
    rec = tx.run("MATCH (n) RETURN count(n) AS total").single()
    return rec["total"]

def main():
    uri = os.environ["NEO4J_URI"]
    user = os.environ.get("NEO4J_USER", "neo4j")
    pwd = os.environ["NEO4J_PASSWORD"]

    print("🔗 Using URI:", uri)

    with GraphDatabase.driver(uri, auth=(user, pwd)) as driver:
        verify(driver)

        with driver.session(database="neo4j") as session:
            summary = session.execute_write(seed_pipeline, "pipeline_demo_001")
            total = session.execute_read(count_nodes)

        print("🌱 Seeded:", summary)
        print(f"📊 Total nodes now: {total}")

if __name__ == "__main__":
    main()
