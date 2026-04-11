

import json
from typing import Dict, List, Tuple, Any
from pathlib import Path


class JsonParser:
    """Parser for structured JSON files - DataCamp practice exercise"""
    
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.data = None
        self.workflow_name = ""
        self.components = {}
        self.connections = []
    
    def parse(self) -> Dict[str, Any]:
        """Parse a JSON file and extract structured information"""
        # Load the JSON data
        self._load_file()
        
        # Extract components
        self._extract_workflow_name()
        self._extract_components()
        self._extract_connections()
        
        return {
            'name': self.workflow_name,
            'components': self.components,
            'connections': self.connections,
            'stats': self._get_stats()
        }
    
    def _load_file(self):
        """Load and parse the JSON file"""
        if not self.filepath.exists():
            raise FileNotFoundError(f"File not found: {self.filepath}")
        
        # Accept .slp and .json files for practice
        valid_extensions = ['.json', '.slp']
        if self.filepath.suffix.lower() not in valid_extensions:
            raise ValueError(f"Expected .json or .slp file, got: {self.filepath.suffix}")
        
        try:
            with open(self.filepath, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in {self.filepath}: {e}")
    
    def _extract_workflow_name(self):
        """Extract workflow name from JSON structure"""
        try:
            # Try SnapLogic format first
            self.workflow_name = self.data['property_map']['info']['label']['value']
        except KeyError:
            # Fallback to simple format or filename
            self.workflow_name = self.data.get('name', self.filepath.stem)
    
    def _extract_components(self):
        """Extract component information (id -> label mapping)"""
        self.components = {}
        
        # Try SnapLogic format
        if 'snap_map' in self.data:
            snap_map = self.data['snap_map']
        elif 'components' in self.data:
            snap_map = self.data['components']
        else:
            return
        
        for comp_id, comp_data in snap_map.items():
            try:
                # Try SnapLogic nested structure
                label = comp_data['property_map']['info']['label']['value']
                self.components[comp_id] = label
            except (KeyError, TypeError):
                # Try simple structure
                if isinstance(comp_data, dict) and 'label' in comp_data:
                    self.components[comp_id] = comp_data['label']
                elif isinstance(comp_data, str):
                    self.components[comp_id] = comp_data
                else:
                    # Use comp_id as fallback
                    self.components[comp_id] = comp_id
    
    def _extract_connections(self):
        """Extract connections between components"""
        self.connections = []
        
        # Try SnapLogic format
        if 'link_map' in self.data:
            link_map = self.data['link_map']
        elif 'connections' in self.data:
            link_map = self.data['connections']
        else:
            return
        
        for link_id, link_data in link_map.items():
            try:
                src_id = link_data['src_id']
                dst_id = link_data['dst_id']
                
                # Only include if both components exist
                if src_id in self.components and dst_id in self.components:
                    self.connections.append((src_id, dst_id, link_id))
            except (KeyError, TypeError):
                # Try simple structure
                if isinstance(link_data, dict):
                    src = link_data.get('from', link_data.get('source'))
                    dst = link_data.get('to', link_data.get('target'))
                    if src and dst and src in self.components and dst in self.components:
                        self.connections.append((src, dst, link_id))
    
    def _get_stats(self) -> Dict[str, Any]:
        """Get basic statistics about the workflow"""
        return {
            'component_count': len(self.components),
            'connection_count': len(self.connections),
            'complexity': self._calculate_complexity()
        }
    
    def _calculate_complexity(self) -> str:
        """Calculate workflow complexity based on size"""
        component_count = len(self.components)
        if component_count > 15:
            return "High"
        elif component_count > 8:
            return "Medium"
        else:
            return "Low"
    
    def get_component_names(self) -> List[str]:
        """Get list of all component names"""
        return list(self.components.values())
    
    def get_connection_summary(self) -> List[Dict[str, str]]:
        """Get human-readable connection summary"""
        summary = []
        for src_id, dst_id, link_id in self.connections:
            summary.append({
                'from': self.components[src_id],
                'to': self.components[dst_id],
                'link_id': link_id
            })
        return summary
    
    def validate(self) -> bool:
        """Validate that the workflow structure makes sense"""
        # Check we have basic data
        if not self.workflow_name:
            raise ValueError("Workflow has no name")
        
        if not self.components:
            raise ValueError("Workflow has no components")
        
        # Check connections reference valid components
        for src_id, dst_id, link_id in self.connections:
            if src_id not in self.components:
                raise ValueError(f"Connection references unknown source: {src_id}")
            if dst_id not in self.components:
                raise ValueError(f"Connection references unknown destination: {dst_id}")
        
        return True


# Utility function for quick parsing
def parse_json_file(filepath: str) -> Dict[str, Any]:
    """Quick function to parse a JSON workflow file"""
    parser = JsonParser(filepath)
    return parser.parse()


# Test if run directly
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2:
        print("Usage: python json_parser.py <data_file.json>")
        sys.exit(1)
    
    try:
        result = parse_json_file(sys.argv[1])
        
        print(f"Workflow: {result['name']}")
        print(f"Components: {result['stats']['component_count']}")
        print(f"Connections: {result['stats']['connection_count']}")
        print(f"Complexity: {result['stats']['complexity']}")
        
        print("\nComponents:")
        for i, name in enumerate(result['components'].values(), 1):
            print(f"  {i}. {name}")
        
        if result['connections']:
            print("\nConnections:")
            parser = JsonParser(sys.argv[1])
            parser.parse()
            for conn in parser.get_connection_summary():
                print(f"  {conn['from']} → {conn['to']} ({conn['link_id']})")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
