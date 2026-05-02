# src/snap_resolver.py
# ------------------------------------------------------------
# GOLDILOCKS — Snap Type Resolver
# Icons, shapes, colours and classification for SnapLogic snaps
# ------------------------------------------------------------

# ------------------------------------------------------------
# TEXT TAGS — per snap type (Mermaid-safe, no emojis)
# ------------------------------------------------------------

SNAP_ICONS = {
    "httpclient":   "[HTTP]",
    "script":       "[SCRIPT]",
    "pipeexec":     "[PIPE]",
    "sftp_get":     "[SFTP-IN]",
    "sftp_put":     "[SFTP-OUT]",
    "db_select":    "[DB]",
    "db_insert":    "[DB]",
    "mapper":       "[MAP]",
    "filter":       "[FILTER]",
    "trigger":      "[TRIGGER]",
    "default":      "[SNAP]",
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
# LAMBDA FUNCTIONS
# ------------------------------------------------------------

resolve_snap_type = lambda class_id: (
    "httpclient" if "httpclient"        in class_id.lower() else
    "script"     if "script-script"     in class_id.lower() else
    "pipeexec"   if "pipeexec"          in class_id.lower() else
    "sftp_get"   if "directorybrowser"  in class_id.lower() else
    "sftp_get"   if "simpleread"        in class_id.lower() else
    "mapper"     if "binarytodocument"  in class_id.lower() else
    "mapper"     if "mapper"            in class_id.lower() else
    "filter"     if "filter"            in class_id.lower() else
    "trigger"    if "trigger"           in class_id.lower() else
    "default"
)

get_icon = lambda snap_type: SNAP_ICONS.get(snap_type, SNAP_ICONS["default"])