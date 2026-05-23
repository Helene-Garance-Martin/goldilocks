from pydantic import BaseModel, Field



class DAGNode(BaseModel):
    id: str
    label: str
    type: str
    wipes_context: bool = False
    next_ids: list[str] = Field(default_factory=list)


class DAGEdge(BaseModel):
    source: str
    target: str
    relationship: str = "CONNECTS_TO"


class DAGModel(BaseModel):
    pipeline_name: str
    nodes: list[DAGNode] = Field(default_factory=list)
    edges: list[DAGEdge] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    exit_points: list[str] = Field(default_factory=list)
    branches: list[list[str]] = Field(default_factory=list)
    external_references: list[str] = []
    complexity: str = "simple"