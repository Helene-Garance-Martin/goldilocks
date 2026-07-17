from pydantic import BaseModel, Field


class DAGNode(BaseModel):
    id: str
    label: str
    type: str
    wipes_context: bool = False
    next_ids: list[str] = Field(default_factory=list)
    child_pipeline: str | None = None
    error_behavior: str = "unknown"

    # Synthetic visualisation provenance. Real snaps retain empty/default values.
    synthetic_kind: str | None = None
    collapsed_snap_ids: list[str] = Field(default_factory=list)
    collapsed_snap_names: list[str] = Field(default_factory=list)
    first_snap_id: str | None = None
    first_snap_name: str | None = None
    last_snap_id: str | None = None
    last_snap_name: str | None = None
    snap_count: int = 1


class DAGEdge(BaseModel):
    source: str
    target: str
    relationship: str = "CONNECTS_TO"


class PipelineCall(BaseModel):
    source_pipeline_id: str
    source_pipeline_name: str
    target_pipeline_id: str
    target_pipeline_name: str
    source_snap_id: str | None = None


class DAGModel(BaseModel):
    pipeline_name: str
    pipeline_id: str | None = None
    nodes: list[DAGNode] = Field(default_factory=list)
    edges: list[DAGEdge] = Field(default_factory=list)
    entry_points: list[str] = Field(default_factory=list)
    exit_points: list[str] = Field(default_factory=list)
    branches: list[list[str]] = Field(default_factory=list)
    external_references: list[str] = Field(default_factory=list)
    complexity: str = "simple"
