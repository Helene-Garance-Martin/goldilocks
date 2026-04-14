# ============================================================
# 🐻 GOLDILOCKS — Pipeline Seeder
# ============================================================
# Reads anonymised pipeline export JSON and seeds Neo4j
# with real Pipeline nodes, Snap nodes and relationships:
#   - Pipeline -[:HAS_SNAP]-> Snap
#   - Snap -[:CONNECTS_TO]-> Snap
#   - Pipeline -[:CALLS]-> Pipeline (parent/child)
#
# Run:
#   python src/pipeline_seeder.py
# ============================================================

import os
import json
import sys
from pathlib import Path
from neo4j import GraphDatabase


# ------------------------------------------------------------
# Lambda functions
# ------------------------------------------------------------

# Extracts date string from SnapLogic's {"$date": "..."} format
extract_date = lambda d: d.get("$date", "") if isinstance(d, dict) else str(d) if d else ""

# Resolves snap type from SnapLogic class_id
resolve_snap_type = lambda class_id: (
    "httpclient"  if "httpclient"  in class_id.lower() else
    "script"      if "script"      in class_id.lower() else
    "pipeexec"    if "pipeexec"    in class_id.lower() else
    "mapper"      if "mapper"      in class_id.lower() else
    "sftp_get"    if "sftp-get"    in class_id.lower() else
    "sftp_put"    if "sftp-put"    in class_id.lower() else
    "db_select"   if "db-select"   in class_id.lower() else
    "filter"      if "filter"      in class_id.lower() else
    "default"
)


# ------------------------------------------------------------
# Neo4j helper functions
# ------------------------------------------------------------

def verify(driver) -> None:
    driver.verify_connectivity()
    print("✅ Connectivity verified")


def count_nodes(tx):
    rec = tx.run("MATCH (n) RETURN count(n) AS total").single()
    return rec["total"]


# ------------------------------------------------------------
# Seeder functions
# ------------------------------------------------------------

def seed_pipeline(tx, pipeline: dict) -> dict:
    """
    Write transaction — seeds one pipeline into Neo4j:
    - MERGE Pipeline node
    - MERGE Snap nodes
    - MERGE CONNECTS_TO relationships between snaps
    - MERGE HAS_SNAP relationships from pipeline to snaps
    """

    pipeline_id   = pipeline["instance_id"]
    pipeline_name = pipeline["name"]
    pipeline_path = pipeline.get("path", "")

    # ── Pipeline node ──────────────────────────────────────
    tx.run(
        """
        MERGE (p:Pipeline {id: $id})
        SET p.name    = $name,
            p.path    = $path,
            p.created = $created,
            p.updated = $updated
        """,
        id      = pipeline_id,
        name    = pipeline_name,
        path    = pipeline_path,
        created = extract_date(pipeline.get("create_time")),
        updated = extract_date(pipeline.get("update_time")),
    )
    print(f"  ✅ Pipeline: {pipeline_name}")

    # ── Snap nodes (from snap_map) ─────────────────────────
    snaps = []
    snap_map = pipeline.get("snap_map", {})

    for snap_id, snap in snap_map.items():
        try:
            label = snap["property_map"]["info"]["label"]["value"]
        except (KeyError, TypeError):
            label = snap_id

        class_id  = snap.get("class_id", "unknown")
        snap_type = resolve_snap_type(class_id)

        try:
            error = snap["property_map"]["error"]["error_behavior"]["value"]
        except (KeyError, TypeError):
            error = "unknown"

        # Check if this snap calls a child pipeline
        child_pipeline = None
        if snap_type == "pipeexec":
            try:
                child_pipeline = snap["property_map"]["settings"]["pipeline"]["value"]
            except (KeyError, TypeError):
                pass

        snaps.append({
            "id":             snap_id,
            "label":          label,
            "type":           snap_type,
            "class_id":       class_id,
            "error":          error,
            "child_pipeline": child_pipeline or "",
        })

    tx.run(
        """
        UNWIND $snaps AS s
        MERGE (n:Snap {id: s.id})
        SET n.label          = s.label,
            n.type           = s.type,
            n.class_id       = s.class_id,
            n.error          = s.error,
            n.child_pipeline = s.child_pipeline
        """,
        snaps=snaps
    )
    print(f"  ✅ Snaps:    {len(snaps)} nodes seeded")

    # ── CONNECTS_TO edges (from link_map) ──────────────────
    edges = []
    link_map = pipeline.get("link_map", {})

    for link_id, link in link_map.items():
        edges.append({
            "from":    link["src_id"],
            "to":      link["dst_id"],
            "link_id": link_id,
        })

    tx.run(
        """
        UNWIND $edges AS e
        MATCH (a:Snap {id: e.from})
        MATCH (b:Snap {id: e.to})
        MERGE (a)-[:CONNECTS_TO {link_id: e.link_id}]->(b)
        """,
        edges=edges
    )
    print(f"  ✅ Links:    {len(edges)} edges seeded")

    # ── HAS_SNAP relationships ─────────────────────────────
    tx.run(
        """
        MATCH (p:Pipeline {id: $pid})
        UNWIND $snap_ids AS sid
        MATCH (n:Snap {id: sid})
        MERGE (p)-[:HAS_SNAP]->(n)
        """,
        pid      = pipeline_id,
        snap_ids = [s["id"] for s in snaps]
    )
    print(f"  ✅ Pipeline → Snap relationships created")

    return {
        "pipeline":       pipeline_name,
        "pipeline_id":    pipeline_id,
        "snaps":          [s["label"] for s in snaps],
        "edges":          [(e["from"], e["to"]) for e in edges],
        "child_pipelines": [s["child_pipeline"] for s in snaps if s["child_pipeline"]],
    }


def seed_parent_child_relationships(tx, summaries: list) -> int:
    """
    After all pipelines are seeded, create CALLS relationships
    between parent pipelines and their children.

    A Pipeline Execute snap calling "DIESE-SHAREPOINT" means:
    (SharePointToken)-[:CALLS]->(DIESE-SHAREPOINT)
    """
    count = 0
    for summary in summaries:
        for child_name in summary["child_pipelines"]:
            result = tx.run(
                """
                MATCH (parent:Pipeline {id: $parent_id})
                MATCH (child:Pipeline {name: $child_name})
                MERGE (parent)-[:CALLS]->(child)
                RETURN count(*) AS created
                """,
                parent_id  = summary["pipeline_id"],
                child_name = child_name
            )
            count += 1
            print(f"  ✅ CALLS: {summary['pipeline']} → {child_name}")
    return count


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------

def main():
    # Neo4j credentials from environment
    uri  = os.environ["NEO4J_URI"]
    user = os.environ.get("NEO4J_USER", "neo4j")
    pwd  = os.environ["NEO4J_PASSWORD"]

    # Load anonymised pipeline export
    export_path = Path("export_anonymised.json")
    if not export_path.exists():
        print(f"❌ File not found: {export_path}")
        print("   Run: python pie.py anonymise --input export.json first!")
        return

    print(f"📂 Loading: {export_path}")
    with open(export_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle project export (entries[]) or single pipeline
    pipelines = data.get("entries", [data])
    print(f"📦 Found {len(pipelines)} pipeline(s) to seed\n")

    with GraphDatabase.driver(uri, auth=(user, pwd)) as driver:
        verify(driver)
        print()

        summaries = []
        with driver.session() as session:

            # Seed all pipelines and snaps
            for pipeline in pipelines:
                print(f"🌱 Seeding: {pipeline.get('name', 'unknown')}")
                summary = session.execute_write(seed_pipeline, pipeline)
                summaries.append(summary)
                print()

            # Create parent → child CALLS relationships
            print("🔗 Creating parent/child pipeline relationships...")
            session.execute_write(seed_parent_child_relationships, summaries)
            print()

            total = session.execute_read(count_nodes)

    # Final summary
    print("=" * 50)
    print(f"🐻 Goldilocks seeding complete!")
    print(f"📊 Total nodes in Neo4j: {total}")
    print()
    for s in summaries:
        print(f"  Pipeline: {s['pipeline']}")
        print(f"  Snaps:    {', '.join(s['snaps'])}")
        if s["child_pipelines"]:
            print(f"  Calls:    {', '.join(s['child_pipelines'])}")
        print()


if __name__ == "__main__":
    main()
