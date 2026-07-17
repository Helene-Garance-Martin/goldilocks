# src/snap_resolver.py
# ------------------------------------------------------------
# GOLDILOCKS — Snap Type Resolver
# Icons, shapes, colours and classification for SnapLogic snaps
# ------------------------------------------------------------

# ------------------------------------------------------------
# TEXT TAGS — per snap type (Mermaid-safe, no emojis)
# ------------------------------------------------------------

SNAP_ICONS = {
    "httpclient": "🌐",
    "script": "📜",
    "pipeexec": "🔀",
    "sftp_get": "📥",
    "sftp_put": "📤",
    "mapper": "🗺️",
    "filter": "⚗️",
    "trigger": "⚡",
    "dynamodb": "🗄️",
    "router": "🔀",
    "union": "🔗",
    "copy": "📋",
    "jsonsplitter": "✂️",
    "groupbyfields": "🧮",
    "recordreplay": "⏪",
    "sort": "↕️",
    "unique": "◇",
    "datatransform": "🔄",
    "default": "⚙️",
}

# ------------------------------------------------------------
# SHAPES — per snap type
# ------------------------------------------------------------

SNAP_SHAPES = {
    "httpclient":   ("[\"", "\"]"),
    "script":       ("[\"", "\"]"),
    "pipeexec":     ("[[\"", "\"]]"),
    "sftp_get":     (">\"", "\"]"),
    "sftp_put":     (">\"", "\"]"),
    "db_select":    ("[(\"", "\")]"),
    "db_insert":    ("[(\"", "\")]"),
    "mapper":       ("[\"", "\"]"),
    "filter":       ("{\"", "\"}"),
    "trigger":      ("(\"", "\")"),
    "default":      ("[\"", "\"]"),
}

# ------------------------------------------------------------
# CLASSDEFS — colour coding per snap type
# ------------------------------------------------------------

CLASSDEFS = """    classDef httpclient fill:#D4A017,stroke:#8B6914,color:#1A1A1A
    classDef script     fill:#4A90D9,stroke:#2C5F8A,color:#FFFFFF
    classDef pipeexec   fill:#7B68EE,stroke:#483D8B,color:#FFFFFF
    classDef sftp_get   fill:#F0A500,stroke:#A06800,color:#1A1A1A
    classDef sftp_put   fill:#E07B00,stroke:#904D00,color:#FFFFFF
    classDef db         fill:#20B2AA,stroke:#147870,color:#FFFFFF
    classDef mapper     fill:#5CB85C,stroke:#3D7A3D,color:#FFFFFF
    classDef filter     fill:#E74C3C,stroke:#922B21,color:#FFFFFF
    classDef trigger    fill:#95A5A6,stroke:#626D6E,color:#FFFFFF
    classDef default    fill:#F5F5F5,stroke:#CCCCCC,color:#1A1A1A
    classDef pipeline   fill:#00BFFF,stroke:#0080AA,color:#1A1A1A"""

# ------------------------------------------------------------
# CLASSIFICATION HELPERS
# ------------------------------------------------------------

CONTEXT_WIPING_TYPES = frozenset({
    "httpclient",
    "script",
    "sftp_get",
    "sftp_put",
})

CONTEXT_WIPING_CLASS_MARKERS = frozenset({
    "binarytodocument",
    "filereader",
})

EXTERNAL_IO_TYPES = frozenset({
    "httpclient",
    "sftp_get",
    "sftp_put",
    "db_select",
    "db_insert",
    "dynamodb",
})

CONTROL_FLOW_TYPES = frozenset({
    "pipeexec",
    "trigger",
    "filter",
    "router",
    "union",
    "copy",
    "jsonsplitter",
})

AUDIT_SIGNIFICANT_TYPES = frozenset({
    "httpclient",
    "script",
    "pipeexec",
    "router",
    "recordreplay",
})

VISUALISATION_PROTECTED_TYPES = frozenset(
    EXTERNAL_IO_TYPES | CONTROL_FLOW_TYPES | AUDIT_SIGNIFICANT_TYPES
)


def resolve_snap_type(class_id: str) -> str:
    """Resolve a SnapLogic class id to Goldilocks' existing snap taxonomy."""
    value = (class_id or "").lower()

    if "httpclient" in value:
        return "httpclient"
    if "script-script" in value:
        return "script"
    if "pipeexec" in value:
        return "pipeexec"
    if "directorybrowser" in value or "simpleread" in value:
        return "sftp_get"
    if "simplewrite" in value or "filewriter" in value:
        return "sftp_put"
    if "dbselect" in value or "select" in value and "database" in value:
        return "db_select"
    if "dbinsert" in value or "insert" in value and "database" in value:
        return "db_insert"
    if "binarytodocument" in value or "mapper" in value:
        return "mapper"
    if "filter" in value:
        return "filter"
    if "trigger" in value:
        return "trigger"
    if "dynamodb" in value:
        return "dynamodb"
    if "router" in value:
        return "router"
    if "union" in value:
        return "union"
    if "flow-copy" in value:
        return "copy"
    if "jsonsplitter" in value:
        return "jsonsplitter"
    if "groupbyfields" in value:
        return "groupbyfields"
    if "recordreplay" in value:
        return "recordreplay"
    if "sort" in value:
        return "sort"
    if "unique" in value:
        return "unique"
    if "datatransform" in value:
        return "datatransform"
    return "default"


def get_icon(snap_type: str) -> str:
    return SNAP_ICONS.get(snap_type, SNAP_ICONS["default"])


def snap_wipes_context(snap_type: str, class_id: str = "") -> bool:
    """Reuse Goldilocks' context-loss classification for graph and JSON DAGs."""
    value = (class_id or "").lower()
    return (
        snap_type in CONTEXT_WIPING_TYPES
        or any(marker in value for marker in CONTEXT_WIPING_CLASS_MARKERS)
    )


def is_visualisation_protected(
    snap_type: str,
    *,
    wipes_context: bool = False,
    child_pipeline: str | None = None,
) -> bool:
    """Whether a snap must remain visible in an abstracted DAG view."""
    return (
        snap_type in VISUALISATION_PROTECTED_TYPES
        or wipes_context
        or bool(child_pipeline)
    )
