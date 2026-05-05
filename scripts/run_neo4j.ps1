# run_neo4j.ps1
# Sets Neo4j Aura connection environment variables for this session
# then runs the Python connection test.


$env:NEO4J_URI      = "your-neo4j-uri-here"
$env:NEO4J_USER     = "neo4j"
$env:NEO4J_PASSWORD = "your-password-here"

python pie.py ping
