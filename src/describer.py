def describe_pipeline(pipeline: dict) -> str:
    """Return a simple human-readable description of one pipeline."""
    name = pipeline.get("name", "Unknown pipeline")
    snap_map = pipeline.get("snap_map", {})

    steps = []
    calls = []

    for snap in snap_map.values():
        class_id = snap.get("class_id", "").lower()

        try:
            label = snap["property_map"]["info"]["label"]["value"]
        except Exception:
            label = "Unnamed step"

        if "directorybrowser" in class_id or "simpleread" in class_id:
            steps.append("fetches files from SFTP")
        elif "httpclient" in class_id:
            steps.append("sends data via HTTP")
        elif "binarytodocument" in class_id or "mapper" in class_id:
            steps.append("transforms data")
        elif "script" in class_id:
            steps.append("runs custom logic")

        if "pipeexec" in class_id:
            try:
                child = snap["property_map"]["settings"]["pipeline"]["value"]
                if child:
                    calls.append(child)
            except Exception:
                pass

    steps = list(dict.fromkeys(steps))
    calls = list(dict.fromkeys(calls))

    lines = [f"🐻 Pipeline: {name}", ""]

    if steps:
        lines.append("What it does:")
        for step in steps:
            lines.append(f"  - {step}")

    if calls:
        lines.append("")
        lines.append("Relationships:")
        for child in calls:
            lines.append(f"  - Calls: {child}")

    return "\n".join(lines)