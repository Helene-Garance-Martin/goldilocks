
from neo4j import GraphDatabase
from getpass import getpass
print("DEBUG: using getpass")


import os
from neo4j import GraphDatabase

uri = os.environ["NEO4J_URI"]
username = os.environ.get("NEO4J_USER", "neo4j")
password = os.environ["NEO4J_PASSWORD"]

print("🔗 Testing Neo4j connection...")

try:
    with GraphDatabase.driver(uri, auth=(username, password)) as driver:
        driver.verify_connectivity()
        print("✅ SUCCESS! Connected to Neo4j!")

        with driver.session(database="neo4j") as session:
            total = session.run("MATCH (n) RETURN count(n) AS total").single()["total"]
            print(f"📊 Found {total} nodes in your database")

except Exception as e:
    print(f"❌ Connection failed: {type(e).__name__}: {e}")




