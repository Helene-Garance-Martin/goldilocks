#!/usr/bin/env python3
"""
database_connector.py - Database Integration Practice + goldilocks Integration
"""

import sys
import os
import json
from neo4j import GraphDatabase
from typing import Dict, Any
from getpass import getpass


class GraphDatabaseConnector:
    """Enhanced database connector with goldilocks pipeline loading"""
    
    def __init__(self, uri: str, username: str = "neo4j", password: str = ""):
        """Initialize database connection"""
        try:
            self.driver = GraphDatabase.driver(uri, auth=(username, password))
            print("✓ Connected to graph database successfully!")
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            self.driver = None
    
    def extract_string_value(self, data):
        """Extract string from SnapLogic format (handles {'value': 'string'} objects)"""
        if isinstance(data, dict) and 'value' in data:
            return str(data['value'])
        return str(data) if data else 'Unknown'
    
    def load_pipeline_from_slp(self, slp_file_path: str):
        """Load a .slp pipeline file into Neo4j"""
        if not self.driver:
            print("❌ No database connection")
            return
        
        # Parse the .slp file
        try:
            with open(slp_file_path, 'r', encoding='utf-8') as file:
                slp_data = json.load(file)
            print(f"✓ Parsed {slp_file_path}")
        except Exception as e:
            print(f"❌ Failed to parse .slp file: {e}")
            return
        
        # Extract pipeline info safely
        label_data = slp_data.get('property_map', {}).get('info', {}).get('label', 'Unknown Pipeline')
        pipeline_name = self.extract_string_value(label_data)
        snap_map = slp_data.get('snap_map', {})
        
        print(f"🔗 Loading pipeline: {pipeline_name}")
        print(f"📊 Found {len(snap_map)} snaps")
        
        # Load into Neo4j
        with self.driver.session() as session:
            # Clear existing data (optional - remove if you want to keep other data)
            session.run("MATCH (n) DETACH DELETE n")
            print("🧹 Cleared existing data")
            
            # Create pipeline node
            session.run(
                "CREATE (p:Pipeline {name: $name, source: $source})",
                name=pipeline_name,
                source=os.path.basename(slp_file_path)  # Just filename, not full path
            )
            
            # Create snap nodes
            for snap_id, snap_data in snap_map.items():
                # Extract snap name safely
                snap_label_data = snap_data.get('property_map', {}).get('info', {}).get('label', snap_id)
                snap_name = self.extract_string_value(snap_label_data)
                snap_class = snap_data.get('class_id', 'unknown')
                
                session.run("""
                    CREATE (s:Snap {
                        id: $id, 
                        name: $name, 
                        class_id: $class_id
                    })
                """, id=snap_id, name=snap_name, class_id=snap_class)
                
                # Connect snap to pipeline
                session.run("""
                    MATCH (p:Pipeline {name: $pipeline_name})
                    MATCH (s:Snap {id: $snap_id})
                    CREATE (p)-[:CONTAINS]->(s)
                """, pipeline_name=pipeline_name, snap_id=snap_id)
            
            print(f"✓ Created pipeline node: {pipeline_name}")
            print(f"✓ Created {len(snap_map)} snap nodes")
            print(f"✓ Created {len(snap_map)} CONTAINS relationships")
            print("🎉 Your real ROH pipeline is now in Neo4j!")
            print("🌐 Check Neo4j Browser to see the beautiful graph!")
    
    def close(self):
        """Close database connection"""
        if self.driver:
            self.driver.close()
            print("✓ Database connection closed")


def main():
    if len(sys.argv) < 2:
        print("Usage: python database_connector.py <slp_file_path>")
        print("Example: python database_connector.py test-data\\DIESE-SHAREPOINT.slp")
        return
    
    slp_file = sys.argv[1]
    
    # Your Neo4j credentials  
    uri = "neo4j+ssc://b264f1e6.databases.neo4j.io"
    username = "neo4j"
    password = getpass("Neo4j password: ")
    
    # Connect and load
    connector = GraphDatabaseConnector(uri, username, password)
    connector.load_pipeline_from_slp(slp_file)
    connector.close()


if __name__ == "__main__":
    main()