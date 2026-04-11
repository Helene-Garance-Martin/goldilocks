# run_neo4j.ps1
# Sets Neo4j Aura connection environment variables for this session
# then runs the Python connection test.

$env:NEO4J_URI  = "neo4j+ssc://b264f1e6.databases.neo4j.io"
$env:NEO4J_USER = "neo4j"
$env:NEO4J_PASSWORD = "Wy1q070992u6eNAqPNhD7jIB15UHZNCtvY5IRaaRsTU"

python .\goldilocks_seed.py

