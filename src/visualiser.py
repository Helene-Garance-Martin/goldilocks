from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class DiagramNode:
    """Represents a node in a workflow diagram"""
    node_id: str
    label: str
    shape: str = "rect"  # rect, round, circle, diamond, etc.
    
    def to_diagram(self) -> str:
        """Convert node to diagram syntax"""
        shapes = {
            "rect": f'{self.node_id}["{self.label}"]',
            "round": f'{self.node_id}("{self.label}")',
            "circle": f'{self.node_id}(("{self.label}"))',
            "diamond": f'{self.node_id}{{"{self.label}"}}',
            "hexagon": f'{self.node_id}{{{{{self.label}}}}}',
            "cylinder": f'{self.node_id}[("{self.label}")]'
        }
        return shapes.get(self.shape, shapes["rect"])


@dataclass
class DiagramEdge:
    """Represents a connection in a workflow diagram"""
    from_node: str
    to_node: str
    label: Optional[str] = None
    arrow_type: str = "-->"  # -->, -.-, ==>, etc.
    
    def to_diagram(self) -> str:
        """Convert edge to diagram syntax"""
        if self.label:
            return f"    {self.from_node} {self.arrow_type}|{self.label}| {self.to_node}"
        else:
            return f"    {self.from_node} {self.arrow_type} {self.to_node}"


@dataclass
class WorkflowDiagram:
    """Main workflow diagram builder - DataCamp practice"""
    graph_type: str = "TD"  # TD, LR, TB, RL
    title: Optional[str] = None
    nodes: List[DiagramNode] = field(default_factory=list)
    edges: List[DiagramEdge] = field(default_factory=list)
    
    def add_node(self, node_id: str, label: str, shape: str = "rect") -> DiagramNode:
        """Add a node to the diagram"""
        node = DiagramNode(node_id, label, shape)
        self.nodes.append(node)
        return node
    
    def add_edge(self, from_node: str, to_node: str, label: Optional[str] = None) -> DiagramEdge:
        """Add an edge to the diagram"""
        edge = DiagramEdge(from_node, to_node, label)
        self.edges.append(edge)
        return edge
    
    def to_diagram(self, include_wrapper: bool = True) -> str:
        """Generate complete workflow diagram"""
        lines = []
        
        if include_wrapper:
            lines.append("```mermaid")
        
        lines.append(f"graph {self.graph_type}")
        
        if self.title:
            lines.append(f"    %% {self.title}")
            lines.append("")
        
        # Add nodes
        if self.nodes:
            lines.append("    %% Node Definitions")
            for node in self.nodes:
                lines.append(f"    {node.to_diagram()}")
            lines.append("")
        
        # Add edges
        if self.edges:
            lines.append("    %% Connections")
            for edge in self.edges:
                lines.append(edge.to_diagram())
        
        if include_wrapper:
            lines.append("```")
        
        return "\n".join(lines)


class DiagramBuilder:
    """Fluent builder for workflow diagrams - DataCamp practice"""
    
    def __init__(self):
        self.diagram = WorkflowDiagram()
    
    def title(self, title: str):
        """Set diagram title"""
        self.diagram.title = title
        return self
    
    def direction(self, direction: str):
        """Set diagram direction (TD, LR, etc.)"""
        self.diagram.graph_type = direction
        return self
    
    def node(self, node_id: str, label: str, shape: str = "rect"):
        """Add a node"""
        self.diagram.add_node(node_id, label, shape)
        return self
    
    def edge(self, from_node: str, to_node: str, label: Optional[str] = None):
        """Add an edge"""
        self.diagram.add_edge(from_node, to_node, label)
        return self
    
    def build(self) -> str:
        """Build the final diagram"""
        return self.diagram.to_diagram()


# Utility functions for common patterns
def simple_workflow(nodes: List[Tuple[str, str]], 
                   connections: List[Tuple[str, str]], 
                   title: Optional[str] = None) -> str:
    """Quick function to create a simple workflow diagram"""
    builder = DiagramBuilder()
    
    if title:
        builder.title(title)
    
    # Add nodes
    for node_id, label in nodes:
        builder.node(node_id, label)
    
    # Add connections
    for from_node, to_node in connections:
        builder.edge(from_node, to_node)
    
    return builder.build()


def data_processing_workflow(workflow_name: str, 
                           components: Dict[str, str],
                           connections: List[Tuple[str, str, str]]) -> str:
    """Specialized function for data processing workflows"""
    builder = DiagramBuilder().title(f"Workflow: {workflow_name}")
    
    # Add components as nodes
    for comp_id, comp_label in components.items():
        # Use shorter node IDs for cleaner diagrams
        node_id = f"n{hash(comp_id) % 1000}"
        builder.node(node_id, comp_label)
    
    # Add connections
    for src, dst, link_id in connections:
        src_node = f"n{hash(src) % 1000}"
        dst_node = f"n{hash(dst) % 1000}"
        builder.edge(src_node, dst_node, link_id)
    
    return builder.build()


# Quick test if run directly
if __name__ == "__main__":
    # Test the diagram generator
    print("Testing Diagram Generator...")
    
    # Simple test
    test_diagram = simple_workflow(
        nodes=[("A", "Input"), ("B", "Process"), ("C", "Output")],
        connections=[("A", "B"), ("B", "C")],
        title="Test Data Workflow"
    )
    
    print(test_diagram)
    print()
    
    # Data processing example
    print("Data Processing Example:")
    
    workflow = (DiagramBuilder()
        .title("ETL Pipeline") 
        .node("extract", "Extract Data", "cylinder")
        .node("transform", "Transform", "rect")
        .node("load", "Load", "cylinder")
        .edge("extract", "transform", "raw")
        .edge("transform", "load", "clean")
        .build())
    
    print(workflow)
