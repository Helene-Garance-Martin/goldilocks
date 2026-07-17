"""Shared scale thresholds and decisions for Goldilocks visualisation."""

from dataclasses import dataclass
from typing import Optional


SOFT_NODE_THRESHOLD = 50
HARD_NODE_THRESHOLD = 300
PROJECT_PIPELINE_THRESHOLD = 15
COLLAPSE_MIN_CHAIN = 4

# Raised only when the detected Mermaid version supports these keys.
MERMAID_MAX_TEXT_SIZE = 200_000
MERMAID_MAX_EDGES = 2_000


@dataclass(frozen=True)
class ScaleDecision:
    """The rendering policy for one measured DAG or project view."""

    node_count: int
    edge_count: int
    collapse: bool

    @property
    def is_large(self) -> bool:
        return self.node_count >= SOFT_NODE_THRESHOLD

    @property
    def reaches_hard_limit(self) -> bool:
        return self.node_count >= HARD_NODE_THRESHOLD


def choose_collapse(node_count: int, explicit: Optional[bool] = None) -> bool:
    """Resolve automatic collapse behaviour, allowing an explicit override."""
    if explicit is not None:
        return explicit
    return node_count >= SOFT_NODE_THRESHOLD


def measure_scale(
    node_count: int,
    edge_count: int,
    explicit_collapse: Optional[bool] = None,
) -> ScaleDecision:
    """Return one central scale decision for a measured view."""
    return ScaleDecision(
        node_count=node_count,
        edge_count=edge_count,
        collapse=choose_collapse(node_count, explicit_collapse),
    )


def combined_view_is_safe(visual_node_count: int) -> bool:
    """Whether a combined view remains within Goldilocks' honest limit."""
    return visual_node_count < HARD_NODE_THRESHOLD
