# src/models.py
from pydantic import BaseModel, Field
from typing import Optional

# ------------------------------------------------------------
# SNAP
# ------------------------------------------------------------

class Snap(BaseModel):
    id: str
    label: str
    snap_type: str
    class_id: str
    wipes_context: bool = False

# ------------------------------------------------------------
# LINK
# ------------------------------------------------------------

class Link(BaseModel):
    src_id: str
    dst_id: str

# ------------------------------------------------------------
# PIPELINE
# ------------------------------------------------------------

class Pipeline(BaseModel):
    name: str
    snaps: list[Snap] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)

# ------------------------------------------------------------
# FOLDER
# ------------------------------------------------------------

class Folder(BaseModel):
    name: str
    pipelines: list[Pipeline] = Field(default_factory=list)