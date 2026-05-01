# ============================================================
# 🐻 GOLDILOCKS — Pipeline Visualiser
# ============================================================
# Generates stunning Mermaid diagrams from anonymised
# pipeline export JSON.
#
# Features:
#   - Text tags per snap type ([HTTP], [SCRIPT] etc.)
#   - \n label splitting for clean node sizing
#   - Subgraphs per pipeline
#   - classDef colour coding
#   - Parent/child pipeline CALLS relationships
#
# Run:
#   python src/visualiser.py --input export_anonymised.json
# ============================================================

import json
import subprocess 
import shutil 
import re
from pathlib import Path


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
    "httpclient":   ("[\"", "\"]"),       # rectangle
    "script":       ("[\"", "\"]"),       # rectangle
    "pipeexec":     ("[[\"", "\"]]"),     # subroutine
    "sftp_get":     (">\"", "\"]"),       # asymmetric
    "sftp_put":     (">\"", "\"]"),       # asymmetric
    "db_select":    ("[(\"", "\")]"),     # cylinder
    "db_insert":    ("[(\"", "\")]"),     # cylinder
    "mapper":       ("[\"", "\"]"),       # rectangle
    "filter":       ("{\"", "\"}"),       # diamond
    "trigger":      ("(\"", "\")"),       # rounded
    "default":      ("[\"", "\"]"),       # rectangle
}


# ------------------------------------------------------------
# CLASSDEFS — colour coding per snap type
# ------------------------------------------------------------

# CLASSDEFS: add subgraph style to kill the black border
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

# Get text tag for snap type
get_icon = lambda snap_type: SNAP_ICONS.get(snap_type, SNAP_ICONS["default"])

# Safe node ID — Mermaid doesn't like hyphens or long IDs
safe_id = lambda snap_id: "n" + snap_id.replace("-", "_")[:8]
safe_file_name = lambda name: re.sub(r"[^a-zA-Z0-9_]+", "_", name).strip("_")


# ------------------------------------------------------------
# LABEL FORMATTER
# ------------------------------------------------------------

def format_label(label: str, snap_type: str) -> str:
    tag = get_icon(snap_type)
    words = label.split()
    lines = []
    current = ""
    for word in words:
        if len(current) + len(word) + 1 > 28:
            if current:
                lines.append(current.strip())
            current = word
        else:
            current += " " + word
    if current:
        lines.append(current.strip())
    formatted = "<br/>".join(lines)
    return f"{tag}<br/>{formatted}"
# ------------------------------------------------------------
# BUILD DIAGRAM
# ------------------------------------------------------------

def build_pipeline_diagram(
    pipelines: list,
    direction: str = "LR"
) -> str:
    """
    Build a complete Mermaid diagram from pipeline data.
    Each pipeline becomes a subgraph.
    Parent/child relationships shown between subgraphs.
    """
    lines = []
    lines.append("%%{init: {'theme': 'base', 'flowchart': {'nodeSpacing': 50, 'rankSpacing': 80, 'padding': 16}, 'themeVariables': {'clusterBkg': '#FAFAFA', 'clusterBorder': '#CCCCCC'}}}%%")
    lines.append(f"flowchart {direction}")
    lines.append("")

    all_snap_types    = {}   # node_id → snap_type
    pipeline_node_ids = {}   # pipeline_name → safe subgraph id

    for pipeline in pipelines:
        pipeline_name = pipeline.get("name", "Unknown")
        snap_map      = pipeline.get("snap_map", {})
        link_map      = pipeline.get("link_map", {})

        # Safe subgraph ID
        p_safe_id = "p_" + safe_file_name(pipeline_name)[:16]
        pipeline_node_ids[pipeline_name] = p_safe_id
        


        # ── Subgraph per pipeline ──────────────────────────
        lines.append(f"    subgraph {p_safe_id}[\"{pipeline_name}\"]")
        lines.append(f"        direction {direction}")
        lines.append("")

        # ── Snap nodes ────────────────────────────────────
        for snap_id, snap in snap_map.items():
            try:
                label = snap["property_map"]["info"]["label"]["value"]
            except (KeyError, TypeError):
                label = snap_id

            class_id  = snap.get("class_id", "unknown")
            snap_type = resolve_snap_type(class_id)
            node_id   = safe_id(snap_id)
            formatted = format_label(label, snap_type)

            shape_open, shape_close = SNAP_SHAPES.get(snap_type, SNAP_SHAPES["default"])
            lines.append(f"        {node_id}{shape_open}{formatted}{shape_close}")

            all_snap_types[node_id] = snap_type

        lines.append("")

        # ── Snap connections ──────────────────────────────
        for _, link in link_map.items():
            src = safe_id(link["src_id"])
            dst = safe_id(link["dst_id"])
            lines.append(f"        {src} --> {dst}")

        lines.append("    end")
        lines.append("")

    # ── Parent/child CALLS relationships ──────────────────
    for pipeline in pipelines:
        pipeline_name = pipeline.get("name", "")
        snap_map      = pipeline.get("snap_map", {})
        p_safe_id     = pipeline_node_ids.get(pipeline_name, "")

        for snap_id, snap in snap_map.items():
            snap_type = resolve_snap_type(snap.get("class_id", ""))
            if snap_type == "pipeexec":
                try:
                    child_name = snap["property_map"]["settings"]["pipeline"]["value"]
                    for other in pipelines:
                        other_name = other.get("name", "")
                        if child_name in other_name or other_name in child_name:
                            child_safe_id = pipeline_node_ids.get(other_name, "")
                            if child_safe_id and child_safe_id != p_safe_id:
                                lines.append(f"    {p_safe_id} -.->|CALLS| {child_safe_id}")
                except (KeyError, TypeError):
                    pass

    lines.append("")

    # ── ClassDefs ─────────────────────────────────────────
    lines.append(CLASSDEFS)
    lines.append("")

    # ── Assign classDefs to nodes ──────────────────────────
    for node_id, snap_type in all_snap_types.items():
        css_class = snap_type if snap_type in [
            "httpclient", "script", "pipeexec",
            "sftp_get", "sftp_put", "mapper",
            "filter", "trigger"
        ] else "default"
        lines.append(f"    class {node_id} {css_class}")

    return "\n".join(lines)


# ------------------------------------------------------------
# RENDER DIAGRAM
# ------------------------------------------------------------

def render_diagram(mmd_path: Path, fmt: str) -> None:
    """Render .mmd to png or svg via Mermaid CLI (mmdc)."""
    if fmt == "mmd":
        return
    if not shutil.which("mmdc"):
        print("⚠️  mmdc not found — install with: npm install -g @mermaid-js/mermaid-cli")
        return
    out_path = mmd_path.with_suffix(f".{fmt}")
    result = subprocess.run(
        ["mmdc", "-i", str(mmd_path), "-o", str(out_path), "--backgroundColor", "white"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        print(f"🖼️  Rendered: {out_path}")
    else:
        print(f"⚠️  PNG render unavailable in this environment (Codespaces/Linux missing Chrome libs)")
        print(f"   💡 Use .mmd preview in VS Code, or run locally for PNG output")
        
    result = subprocess.run(
    ["mmdc", "-i", str(mmd_path), "-o", str(out_path), 
     "--backgroundColor", "white",
     "--puppeteerConfigFile", "puppeteer-config.json"],  
    capture_output=True, text=True
)


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

def generate_diagrams(input_path: str, output_dir: str, direction: str = "LR", fmt: str = "mmd", single: str = None) -> None:
   
    input_file  = Path(input_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    if not input_file.exists():
        print(f"❌ File not found: {input_path}")
        raise FileNotFoundError(f"{input_path}")
        return
    print(f"📂 Loading: {input_path}")
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}")
        return
    pipelines = data.get("entries", [data])
    if single:
        pipelines = [p for p in pipelines if single.lower() in p.get("name", "").lower()]
        if not pipelines:
            print(f"❌ No pipeline found matching: {single}")
            return
        print(f"🔍 Filtering to: {single}")
        
    if not single:
        combined      = build_pipeline_diagram(pipelines, direction)
        combined_path = output_path / "goldilocks_combined.mmd"
        combined_path.write_text(combined, encoding='utf-8')
        print(f"✅ Combined diagram: {combined_path}")
        render_diagram(combined_path, fmt)

    count = len(pipelines)
    print(f"📦 Found {count} pipeline{'s' if count != 1 else ''}\n")
    if count > 5:
        print(f"⚠️  {count} pipelines — combined diagram may be large. Use --single to isolate.")
    # ── Combined diagram ───────────────────────────────────
    combined      = build_pipeline_diagram(pipelines, direction)
    combined_path = output_path / "goldilocks_combined.mmd"
    combined_path.write_text(combined, encoding='utf-8')
    print(f"✅ Combined diagram: {combined_path}")
    render_diagram(combined_path, fmt)
    # ── Individual diagrams ────────────────────────────────
    from typer import progressbar
    with progressbar(pipelines, label="  🎨 Generating") as progress:
        for pipeline in progress:
            name    = safe_file_name(pipeline.get("name", "pipeline"))
            diagram = build_pipeline_diagram([pipeline], direction)
            path    = output_path / f"{name}.mmd"
            path.write_text(diagram, encoding='utf-8')
            render_diagram(path, fmt)
    print(f"\n🐻 Done — {count + 1} diagrams written to {output_dir}")
    
# ------------------------------------------------------------
# CLI ENTRY POINT
# ------------------------------------------------------------

if __name__ == "__main__":
    parser.add_argument("--format", default="mmd", choices=["mmd", "png", "svg"], 
                    help="Output format (default: mmd)")
    parser = argparse.ArgumentParser(
        description="🐻 Goldilocks Visualiser — generate Mermaid diagrams"
    )
  
    parser.add_argument("--input",     default="export_anonymised.json")
    parser.add_argument("--output",    default="diagrams/")
    parser.add_argument("--direction", default="LR")
    args = parser.parse_args()

    generate_diagrams(args.input, args.output, args.direction, args.format)